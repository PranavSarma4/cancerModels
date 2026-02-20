"""
ChimeraX-backed MCP tools.

Each function builds a ChimeraX command, sends it via the REST API,
and optionally returns a base64-encoded screenshot.
"""

from __future__ import annotations

import asyncio
import json

from .chimerax_session import ChimeraXError, get_session
from .tools import RCSB_DOWNLOAD_URL


def _run(coro):
    """Run an async coroutine from sync context (MCP tools are sync)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()


def open_structure(pdb_id: str) -> str:
    """Open a PDB structure in ChimeraX.

    Args:
        pdb_id: 4-character PDB identifier.
    """
    pdb_id = pdb_id.strip().upper()
    session = get_session()
    try:
        _run(session.run_command(f"close all"))
        _run(session.run_command(f"open {RCSB_DOWNLOAD_URL}/{pdb_id}.pdb"))
        _run(session.run_command("lighting soft"))
        _run(session.run_command("set bgColor white"))
        b64 = _run(session.snapshot())
        return json.dumps({
            "status": "ok",
            "pdb_id": pdb_id,
            "message": f"Opened {pdb_id} in ChimeraX",
            "image_base64": b64,
        })
    except ChimeraXError as exc:
        return f"Error: {exc}"


def rotate_view(axis: str = "y", angle: float = 90.0) -> str:
    """Rotate the current ChimeraX view.

    Args:
        axis: Rotation axis ('x', 'y', or 'z').
        angle: Rotation angle in degrees.
    """
    if axis.lower() not in ("x", "y", "z"):
        return "Error: axis must be 'x', 'y', or 'z'"
    session = get_session()
    try:
        _run(session.run_command(f"turn {axis} {angle}"))
        b64 = _run(session.snapshot())
        return json.dumps({
            "status": "ok",
            "rotation": {"axis": axis, "angle": angle},
            "image_base64": b64,
        })
    except ChimeraXError as exc:
        return f"Error: {exc}"


def surface_view(representation: str = "surface", transparency: float = 0.5) -> str:
    """Switch to a surface or cartoon representation in ChimeraX.

    Args:
        representation: One of 'surface', 'cartoon', 'stick', 'sphere'.
        transparency: Surface transparency 0.0 (opaque) to 1.0 (invisible).
    """
    allowed = ("surface", "cartoon", "stick", "sphere")
    if representation not in allowed:
        return f"Error: representation must be one of {allowed}"
    transparency = max(0.0, min(1.0, transparency))

    session = get_session()
    try:
        if representation == "surface":
            _run(session.run_command("hide atoms"))
            _run(session.run_command("surface"))
            pct = int(transparency * 100)
            _run(session.run_command(f"transparency {pct}"))
        elif representation == "cartoon":
            _run(session.run_command("hide atoms"))
            _run(session.run_command("cartoon"))
        else:
            _run(session.run_command(f"style {representation}"))
            _run(session.run_command("show atoms"))

        b64 = _run(session.snapshot())
        return json.dumps({
            "status": "ok",
            "representation": representation,
            "transparency": transparency,
            "image_base64": b64,
        })
    except ChimeraXError as exc:
        return f"Error: {exc}"


def mutate_residue(chain: str, resseq: int, new_residue: str) -> str:
    """Mutate a single residue in the loaded structure using ChimeraX's swapaa.

    Args:
        chain: Chain identifier (e.g. 'A').
        resseq: Residue sequence number.
        new_residue: Three-letter code of the target amino acid (e.g. 'ALA').
    """
    new_residue = new_residue.strip().upper()
    spec = f"/{chain}:{resseq}"
    session = get_session()
    try:
        _run(session.run_command(f"swapaa {spec} {new_residue}"))
        _run(session.run_command(f"color {spec} magenta"))
        _run(session.run_command(f"label {spec}"))
        b64 = _run(session.snapshot())
        return json.dumps({
            "status": "ok",
            "mutation": f"{chain}:{resseq} -> {new_residue}",
            "image_base64": b64,
        })
    except ChimeraXError as exc:
        return f"Error: {exc}"


def take_snapshot(width: int = 1024, height: int = 768, transparent: bool = False) -> str:
    """Take a screenshot of the current ChimeraX view.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        transparent: If true, use a transparent background.
    """
    session = get_session()
    try:
        b64 = _run(session.snapshot(width=width, height=height, transparent=transparent))
        return json.dumps({
            "status": "ok",
            "width": width,
            "height": height,
            "image_base64": b64,
        })
    except ChimeraXError as exc:
        return f"Error: {exc}"
