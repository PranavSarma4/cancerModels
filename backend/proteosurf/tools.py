"""
Core MCP tools for structural biology.

Provides: fetch_structure, fetch_alphafold, list_residues,
highlight_residues, find_pockets.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from Bio.PDB import PDBParser, NeighborSearch

RCSB_DOWNLOAD_URL = "https://files.rcsb.org/download"
ALPHAFOLD_API_URL = "https://alphafold.ebi.ac.uk/api/prediction"
CACHE_DIR = Path(os.environ.get("STRUCTBIO_CACHE", tempfile.gettempdir())) / "proteosurf"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HTTP_TIMEOUT = 30.0


def _http_client() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True)


def _cached_pdb_path(pdb_id: str) -> Path:
    return CACHE_DIR / f"{pdb_id.lower()}.pdb"


def download_pdb(pdb_id: str) -> Path:
    """Download a PDB file from RCSB and cache it locally."""
    pdb_id = pdb_id.strip().upper()
    if len(pdb_id) != 4:
        raise ValueError(f"PDB ID must be exactly 4 characters, got '{pdb_id}'")
    dest = _cached_pdb_path(pdb_id)
    if dest.exists():
        return dest
    url = f"{RCSB_DOWNLOAD_URL}/{pdb_id}.pdb"
    with _http_client() as client:
        resp = client.get(url)
        if resp.status_code == 404:
            raise FileNotFoundError(f"PDB entry '{pdb_id}' not found on RCSB")
        resp.raise_for_status()
    dest.write_text(resp.text)
    return dest


def parse_structure(pdb_path: Path, structure_id: str = "s"):
    parser = PDBParser(QUIET=True)
    return parser.get_structure(structure_id, str(pdb_path))


# ---------------------------------------------------------------------------
# Pocket detection
# ---------------------------------------------------------------------------

@dataclass
class Pocket:
    rank: int
    score: float
    center: tuple[float, float, float]
    residues: list[str]


def detect_pockets(
    structure,
    *,
    probe_radius: float = 1.4,
    min_cluster_size: int = 3,
    grid_spacing: float = 1.0,
    burial_threshold: int = 16,
) -> list[Pocket]:
    """Grid-based burial analysis to find surface cavities."""
    atoms = list(structure.get_atoms())
    if not atoms:
        return []

    coords = np.array([a.get_vector().get_array() for a in atoms])
    ns = NeighborSearch(atoms)

    lo = coords.min(axis=0) - 4.0
    hi = coords.max(axis=0) + 4.0

    pocket_points: list[tuple[np.ndarray, int]] = []
    for x in np.arange(lo[0], hi[0], grid_spacing):
        for y in np.arange(lo[1], hi[1], grid_spacing):
            for z in np.arange(lo[2], hi[2], grid_spacing):
                pt = np.array([x, y, z])
                close = ns.search(pt, probe_radius + 3.0, level="A")
                if len(close) < burial_threshold:
                    continue
                dists = np.linalg.norm(coords - pt, axis=1)
                if dists.min() < probe_radius:
                    continue
                pocket_points.append((pt, len(close)))

    if not pocket_points:
        return []

    used = [False] * len(pocket_points)
    clusters: list[list[int]] = []
    merge_dist = grid_spacing * 2.5

    for i in range(len(pocket_points)):
        if used[i]:
            continue
        cluster = [i]
        used[i] = True
        queue = [i]
        while queue:
            ci = queue.pop()
            pi = pocket_points[ci][0]
            for j in range(len(pocket_points)):
                if used[j]:
                    continue
                if np.linalg.norm(pi - pocket_points[j][0]) < merge_dist:
                    used[j] = True
                    cluster.append(j)
                    queue.append(j)
        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)

    pockets: list[Pocket] = []
    for rank, cluster in enumerate(
        sorted(clusters, key=lambda c: sum(pocket_points[i][1] for i in c), reverse=True),
        start=1,
    ):
        pts_arr = np.array([pocket_points[i][0] for i in cluster])
        center = tuple(float(v) for v in pts_arr.mean(axis=0))
        score = sum(pocket_points[i][1] for i in cluster) / len(cluster)

        nearby_residues: set[str] = set()
        for pt in pts_arr:
            for res in ns.search(pt, probe_radius + 3.0, level="R"):
                chain_id = res.get_parent().id
                resname = res.get_resname().strip()
                resseq = res.get_id()[1]
                nearby_residues.add(f"{chain_id}:{resname}{resseq}")

        pockets.append(Pocket(
            rank=rank,
            score=round(score, 2),
            center=(round(center[0], 2), round(center[1], 2), round(center[2], 2)),
            residues=sorted(nearby_residues),
        ))
    return pockets[:10]


# ---------------------------------------------------------------------------
# Tool implementations (plain functions, decorated by mcp_server.py)
# ---------------------------------------------------------------------------

def fetch_structure(pdb_id: str) -> str:
    """Download a PDB file from RCSB and return its contents.

    Args:
        pdb_id: 4-character PDB identifier (e.g. '1CRN', '4HHB').
    """
    try:
        path = download_pdb(pdb_id)
        text = path.read_text()
        lines = text.splitlines()
        if len(lines) > 500:
            header = "\n".join(lines[:50])
            atom_lines = [l for l in lines if l.startswith(("ATOM", "HETATM"))]
            return (
                f"[PDB {pdb_id.upper()} — {len(lines)} lines, "
                f"{len(atom_lines)} ATOM/HETATM records. Cached at {path}]\n\n"
                + header + f"\n... ({len(lines) - 50} more lines)"
            )
        return text
    except (ValueError, FileNotFoundError) as exc:
        return f"Error: {exc}"
    except httpx.HTTPStatusError as exc:
        return f"HTTP error fetching PDB {pdb_id}: {exc.response.status_code}"


def fetch_alphafold(uniprot_id: str) -> str:
    """Fetch a predicted structure from AlphaFold DB for a given UniProt accession.

    Args:
        uniprot_id: UniProt accession (e.g. 'P00520', 'Q9Y6K9').
    """
    uniprot_id = uniprot_id.strip().upper()
    try:
        with _http_client() as client:
            resp = client.get(f"{ALPHAFOLD_API_URL}/{uniprot_id}")
            if resp.status_code == 404:
                return f"Error: No AlphaFold prediction for '{uniprot_id}'"
            resp.raise_for_status()
            entries = resp.json()

        entry = entries[0] if isinstance(entries, list) and entries else entries
        if not isinstance(entry, dict):
            return f"Error: Unexpected API response for '{uniprot_id}'"

        pdb_url = entry.get("pdbUrl") or entry.get("pdb_url")
        result: dict[str, Any] = {
            "uniprot_id": uniprot_id,
            "model_id": entry.get("entryId", "unknown"),
            "organism": entry.get("organismScientificName", "unknown"),
            "gene": entry.get("gene", "unknown"),
            "pdb_url": pdb_url,
            "cif_url": entry.get("cifUrl") or entry.get("cif_url"),
            "model_quality": entry.get("globalMetricValue"),
        }
        if pdb_url:
            with _http_client() as client:
                pdb_resp = client.get(pdb_url)
                pdb_resp.raise_for_status()
                dest = CACHE_DIR / f"AF-{uniprot_id}.pdb"
                dest.write_text(pdb_resp.text)
                lines = pdb_resp.text.splitlines()
                result["cached_path"] = str(dest)
                result["atom_count"] = sum(1 for l in lines if l.startswith(("ATOM", "HETATM")))
        return json.dumps(result, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"HTTP error: {exc.response.status_code}"


def list_residues(pdb_id: str, chain: str) -> str:
    """List all residues for a given chain in a PDB structure.

    Args:
        pdb_id: 4-character PDB identifier.
        chain: Single-letter chain identifier (e.g. 'A').
    """
    try:
        path = download_pdb(pdb_id)
    except (ValueError, FileNotFoundError, httpx.HTTPStatusError) as exc:
        return f"Error: {exc}"

    structure = parse_structure(path, pdb_id)
    chain = chain.strip().upper()

    for model in structure:
        if chain in model:
            chain_obj = model[chain]
            break
    else:
        available = sorted({c.id for m in structure for c in m})
        return f"Error: Chain '{chain}' not found. Available: {available}"

    residues: list[dict[str, Any]] = []
    for res in chain_obj.get_residues():
        het, resseq, icode = res.get_id()
        if het.strip() and het.strip() != "W":
            res_type = "hetero"
        elif het.strip() == "W":
            res_type = "water"
        else:
            res_type = "standard"
        residues.append({
            "resseq": resseq,
            "resname": res.get_resname().strip(),
            "num_atoms": len(list(res.get_atoms())),
            "insertion_code": icode.strip() or None,
            "type": res_type,
        })

    return json.dumps({
        "pdb_id": pdb_id.upper(), "chain": chain,
        "total_residues": len(residues),
        "standard_residues": sum(1 for r in residues if r["type"] == "standard"),
        "hetero_residues": sum(1 for r in residues if r["type"] == "hetero"),
        "water_molecules": sum(1 for r in residues if r["type"] == "water"),
        "residues": residues,
    }, indent=2)


def highlight_residues(
    pdb_id: str, residues: list[int], color: str = "red", chain: str = "A"
) -> str:
    """Generate a UCSF ChimeraX command script to color specific residues.

    Args:
        pdb_id: 4-character PDB identifier.
        residues: List of residue sequence numbers to highlight.
        color: Color name (e.g. 'red', 'blue', '#FF6600').
        chain: Chain identifier (default 'A').
    """
    pdb_id = pdb_id.strip().upper()
    if not residues:
        return "Error: No residues specified."

    res_spec = ",".join(str(r) for r in sorted(residues))
    sel = f"/{chain}:{res_spec}"
    script = "\n".join([
        f"# ChimeraX — highlight {pdb_id} chain {chain}",
        f"open {RCSB_DOWNLOAD_URL}/{pdb_id}.pdb",
        f"color #1 lightgray", f"style #1 stick",
        f"color #1{sel} {color}", f"style #1{sel} ball",
        f"select #1{sel}",
        f"surface #1", f"transparency #1 70",
        f"color #1{sel} {color} target s",
        f"label #1{sel} text {{0.name}}{{0.number}}",
        f"view #1{sel}", f"lighting soft",
    ])
    dest = CACHE_DIR / f"{pdb_id}_highlight.cxc"
    dest.write_text(script)
    return f"Script saved to {dest}\n\n{script}"


def find_pockets(pdb_id: str, sensitivity: str = "normal") -> str:
    """Detect binding pockets using geometry-based burial analysis.

    Args:
        pdb_id: 4-character PDB identifier.
        sensitivity: 'low', 'normal', or 'high'.
    """
    params: dict[str, dict] = {
        "low": {"grid_spacing": 1.5, "burial_threshold": 20, "min_cluster_size": 5},
        "normal": {"grid_spacing": 1.0, "burial_threshold": 16, "min_cluster_size": 3},
        "high": {"grid_spacing": 0.8, "burial_threshold": 12, "min_cluster_size": 2},
    }
    if sensitivity not in params:
        return f"Error: sensitivity must be one of {list(params.keys())}"
    try:
        path = download_pdb(pdb_id)
    except (ValueError, FileNotFoundError, httpx.HTTPStatusError) as exc:
        return f"Error: {exc}"

    structure = parse_structure(path, pdb_id)
    pockets = detect_pockets(structure, **params[sensitivity])

    return json.dumps({
        "pdb_id": pdb_id.upper(),
        "sensitivity": sensitivity,
        "pockets_found": len(pockets),
        "pockets": [
            {"rank": p.rank, "burial_score": p.score,
             "center_xyz": list(p.center),
             "num_residues": len(p.residues), "residues": p.residues}
            for p in pockets
        ],
    }, indent=2)
