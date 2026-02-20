"""
Molecular docking tools.

dock_ligand       — prepare receptor, convert SMILES to 3D, run AutoDock Vina
generate_candidates — fragment-based ligand suggestion for a pocket
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .tools import CACHE_DIR, download_pdb

VINA_BIN = os.environ.get("VINA_BIN", shutil.which("vina") or "vina")
OBABEL_BIN = os.environ.get("OBABEL_BIN", shutil.which("obabel") or "obabel")

_HAS_RDKIT = False
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, Fragments, rdMolDescriptors
    _HAS_RDKIT = True
except ImportError:
    pass


def _check_binary(name: str, path: str) -> str | None:
    """Return an error string if the binary is not found, else None."""
    if not shutil.which(path):
        return f"{name} not found at '{path}'. Install it or set {name.upper()}_BIN."
    return None


def dock_ligand(pdb_id: str, smiles: str, center_x: float = 0.0,
                center_y: float = 0.0, center_z: float = 0.0,
                box_size: float = 25.0, exhaustiveness: int = 8) -> str:
    """Dock a small-molecule ligand into a protein structure using AutoDock Vina.

    Args:
        pdb_id: 4-character PDB identifier for the receptor.
        smiles: SMILES string of the ligand to dock.
        center_x: X-coordinate of the docking box center (Angstroms).
        center_y: Y-coordinate of the docking box center.
        center_z: Z-coordinate of the docking box center.
        box_size: Side length of the cubic search box (Angstroms).
        exhaustiveness: Search thoroughness (higher = slower but better).
    """
    if not _HAS_RDKIT:
        return "Error: RDKit is required for docking. pip install rdkit"

    for name, path in [("vina", VINA_BIN), ("obabel", OBABEL_BIN)]:
        err = _check_binary(name, path)
        if err:
            return f"Error: {err}"

    try:
        pdb_path = download_pdb(pdb_id)
    except Exception as exc:
        return f"Error downloading receptor: {exc}"

    workdir = Path(tempfile.mkdtemp(prefix="dock_", dir=CACHE_DIR))

    # --- Prepare receptor PDBQT via Open Babel ---
    receptor_pdbqt = workdir / "receptor.pdbqt"
    proc = subprocess.run(
        [OBABEL_BIN, str(pdb_path), "-O", str(receptor_pdbqt), "-xr"],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        return f"Error preparing receptor: {proc.stderr}"

    # --- Convert SMILES to 3D ligand PDBQT ---
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return f"Error: Invalid SMILES '{smiles}'"
    mol = Chem.AddHs(mol)
    status = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if status != 0:
        return "Error: Could not generate 3D coordinates for ligand"
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)

    ligand_sdf = workdir / "ligand.sdf"
    writer = Chem.SDWriter(str(ligand_sdf))
    writer.write(mol)
    writer.close()

    ligand_pdbqt = workdir / "ligand.pdbqt"
    proc = subprocess.run(
        [OBABEL_BIN, str(ligand_sdf), "-O", str(ligand_pdbqt)],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        return f"Error converting ligand: {proc.stderr}"

    # --- Run Vina ---
    output_pdbqt = workdir / "output.pdbqt"
    vina_cmd = [
        VINA_BIN,
        "--receptor", str(receptor_pdbqt),
        "--ligand", str(ligand_pdbqt),
        "--out", str(output_pdbqt),
        "--center_x", str(center_x),
        "--center_y", str(center_y),
        "--center_z", str(center_z),
        "--size_x", str(box_size),
        "--size_y", str(box_size),
        "--size_z", str(box_size),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", "5",
    ]

    try:
        proc = subprocess.run(
            vina_cmd, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return "Error: Vina docking timed out (>5 min)"

    if proc.returncode != 0:
        return f"Error running Vina:\n{proc.stderr}"

    # --- Parse results ---
    poses: list[dict[str, Any]] = []
    current_energy: float | None = None
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            try:
                poses.append({
                    "mode": int(parts[0]),
                    "affinity_kcal_mol": float(parts[1]),
                    "rmsd_lb": float(parts[2]),
                    "rmsd_ub": float(parts[3]),
                })
            except (ValueError, IndexError):
                continue

    return json.dumps({
        "pdb_id": pdb_id.upper(),
        "ligand_smiles": smiles,
        "box_center": [center_x, center_y, center_z],
        "box_size": box_size,
        "num_poses": len(poses),
        "poses": poses,
        "output_file": str(output_pdbqt),
        "work_dir": str(workdir),
    }, indent=2)


def generate_candidates(pocket_residues: list[str], num: int = 10) -> str:
    """Suggest small-molecule candidates for a binding pocket using fragment-based generation.

    Args:
        pocket_residues: List of residue identifiers from pocket detection (e.g. ['A:ASP25', 'A:THR26']).
        num: Number of candidate molecules to generate (max 50).
    """
    if not _HAS_RDKIT:
        return "Error: RDKit is required. pip install rdkit"

    num = min(num, 50)

    charged_residues = {"ASP", "GLU", "LYS", "ARG", "HIS"}
    aromatic_residues = {"PHE", "TYR", "TRP", "HIS"}
    polar_residues = {"SER", "THR", "ASN", "GLN", "CYS"}
    hydrophobic_residues = {"ALA", "VAL", "LEU", "ILE", "MET", "PRO"}

    pocket_chars: dict[str, int] = {
        "charged": 0, "aromatic": 0, "polar": 0, "hydrophobic": 0,
    }
    for r in pocket_residues:
        resname = r.split(":")[-1][:3] if ":" in r else r[:3]
        if resname in charged_residues:
            pocket_chars["charged"] += 1
        if resname in aromatic_residues:
            pocket_chars["aromatic"] += 1
        if resname in polar_residues:
            pocket_chars["polar"] += 1
        if resname in hydrophobic_residues:
            pocket_chars["hydrophobic"] += 1

    # Fragment library biased by pocket character
    fragments_charged = [
        "C(=O)[O-]", "C(=O)O", "[NH3+]", "C(=N)N", "c1cc[nH]c1",
    ]
    fragments_aromatic = [
        "c1ccccc1", "c1ccncc1", "c1ccc2[nH]ccc2c1", "c1ccoc1", "c1ccsc1",
    ]
    fragments_polar = [
        "O", "N", "C(=O)N", "CO", "CS", "C(=O)", "NC(=O)",
    ]
    fragments_hydrophobic = [
        "C", "CC", "C(C)C", "C1CCCCC1", "C1CCC1",
    ]

    import random
    random.seed(42)

    dominant = max(pocket_chars, key=pocket_chars.get)  # type: ignore[arg-type]
    frag_pools = {
        "charged": fragments_charged + fragments_polar,
        "aromatic": fragments_aromatic + fragments_polar,
        "polar": fragments_polar + fragments_charged + fragments_aromatic,
        "hydrophobic": fragments_hydrophobic + fragments_aromatic,
    }
    pool = frag_pools[dominant]

    candidates: list[dict[str, Any]] = []
    attempts = 0
    while len(candidates) < num and attempts < num * 20:
        attempts += 1
        n_frags = random.randint(2, 5)
        smiles = "".join(random.choices(pool, k=n_frags))
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue
        smiles_canonical = Chem.MolToSmiles(mol)
        if any(c["smiles"] == smiles_canonical for c in candidates):
            continue

        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)

        # Lipinski filter
        if mw > 500 or logp > 5 or hbd > 5 or hba > 10:
            continue

        candidates.append({
            "smiles": smiles_canonical,
            "mol_weight": round(mw, 2),
            "logP": round(logp, 2),
            "hbd": hbd,
            "hba": hba,
            "num_atoms": mol.GetNumAtoms(),
        })

    return json.dumps({
        "pocket_character": pocket_chars,
        "dominant_character": dominant,
        "num_candidates": len(candidates),
        "candidates": candidates,
    }, indent=2)
