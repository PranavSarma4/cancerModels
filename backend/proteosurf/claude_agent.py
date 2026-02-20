"""
Claude Agent SDK integration.

Uses the official claude-agent-sdk package with @tool decorator and
ClaudeSDKClient to provide a native MCP-based agent experience.

Track: Best use of Claude Agent SDK
"""

from __future__ import annotations

import json
import os
from typing import Any

from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeSDKClient,
    ClaudeAgentOptions,
)

from . import tools as core_tools
from . import chimerax_tools
from . import docking


SYSTEM_PROMPT = """\
You are Proteosurf — Windsurf for biology. An expert structural biology and \
drug-discovery assistant that can fetch protein structures (PDB, AlphaFold), \
inspect residues, find binding contacts, detect pockets, control ChimeraX for \
visualization, dock small molecules, search research literature, provide \
voice narrations, and look up pharma market data. \
Be scientifically rigorous — cite real PDB codes and residue numbers. \
Explain concepts clearly, especially for students.
"""


# ---------------------------------------------------------------------------
# Register every Proteosurf tool using the @tool decorator
# ---------------------------------------------------------------------------

@tool(
    "fetch_structure",
    "Download a PDB file from RCSB and return its contents.",
    {"pdb_id": str},
)
async def sdk_fetch_structure(args: dict) -> dict:
    result = core_tools.fetch_structure(args["pdb_id"])
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "fetch_alphafold",
    "Fetch a predicted structure from AlphaFold DB for a UniProt accession.",
    {"uniprot_id": str},
)
async def sdk_fetch_alphafold(args: dict) -> dict:
    result = core_tools.fetch_alphafold(args["uniprot_id"])
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "list_residues",
    "List all residues for a given chain in a PDB structure.",
    {"pdb_id": str, "chain": str},
)
async def sdk_list_residues(args: dict) -> dict:
    result = core_tools.list_residues(args["pdb_id"], args["chain"])
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "highlight_residues",
    "Generate a ChimeraX script to color specific residues.",
    {"pdb_id": str, "residues": list, "color": str, "chain": str},
)
async def sdk_highlight_residues(args: dict) -> dict:
    result = core_tools.highlight_residues(
        args["pdb_id"],
        args.get("residues", []),
        args.get("color", "red"),
        args.get("chain", "A"),
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "find_pockets",
    "Detect binding pockets using geometry-based burial analysis.",
    {"pdb_id": str, "sensitivity": str},
)
async def sdk_find_pockets(args: dict) -> dict:
    result = core_tools.find_pockets(
        args["pdb_id"], args.get("sensitivity", "normal")
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "find_contacts",
    "Find binding contacts between a protein chain and ligands or another chain.",
    {"pdb_id": str, "chain": str, "distance": float, "target": str},
)
async def sdk_find_contacts(args: dict) -> dict:
    result = core_tools.find_contacts(
        args["pdb_id"],
        args.get("chain", "A"),
        args.get("distance", 4.0),
        args.get("target", "ligand"),
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "open_structure",
    "Open a PDB structure in ChimeraX and return a screenshot.",
    {"pdb_id": str},
)
async def sdk_open_structure(args: dict) -> dict:
    result = chimerax_tools.open_structure(args["pdb_id"])
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "rotate_view",
    "Rotate the current ChimeraX view and return a screenshot.",
    {"axis": str, "angle": float},
)
async def sdk_rotate_view(args: dict) -> dict:
    result = chimerax_tools.rotate_view(
        args.get("axis", "y"), args.get("angle", 90.0)
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "surface_view",
    "Switch ChimeraX to surface, cartoon, stick, or sphere representation.",
    {"representation": str, "transparency": float},
)
async def sdk_surface_view(args: dict) -> dict:
    result = chimerax_tools.surface_view(
        args.get("representation", "surface"),
        args.get("transparency", 0.5),
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "mutate_residue",
    "Mutate a residue in ChimeraX using swapaa.",
    {"chain": str, "resseq": int, "new_residue": str},
)
async def sdk_mutate_residue(args: dict) -> dict:
    result = chimerax_tools.mutate_residue(
        args["chain"], args["resseq"], args["new_residue"]
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "snapshot",
    "Capture a screenshot of the current ChimeraX view.",
    {"width": int, "height": int, "transparent": bool},
)
async def sdk_snapshot(args: dict) -> dict:
    result = chimerax_tools.take_snapshot(
        args.get("width", 1024),
        args.get("height", 768),
        args.get("transparent", False),
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "dock_ligand",
    "Dock a small-molecule ligand (SMILES) into a protein using AutoDock Vina.",
    {"pdb_id": str, "smiles": str, "center_x": float, "center_y": float,
     "center_z": float, "box_size": float, "exhaustiveness": int},
)
async def sdk_dock_ligand(args: dict) -> dict:
    result = docking.dock_ligand(
        args["pdb_id"], args["smiles"],
        args.get("center_x", 0.0), args.get("center_y", 0.0),
        args.get("center_z", 0.0), args.get("box_size", 25.0),
        args.get("exhaustiveness", 8),
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "generate_candidates",
    "Suggest small molecules for a binding pocket using fragment-based generation.",
    {"pocket_residues": list, "num": int},
)
async def sdk_generate_candidates(args: dict) -> dict:
    result = docking.generate_candidates(
        args["pocket_residues"], args.get("num", 10)
    )
    return {"content": [{"type": "text", "text": result}]}


# ---------------------------------------------------------------------------
# Build the SDK MCP server and client factory
# ---------------------------------------------------------------------------

ALL_SDK_TOOLS = [
    sdk_fetch_structure, sdk_fetch_alphafold, sdk_list_residues,
    sdk_highlight_residues, sdk_find_pockets, sdk_find_contacts,
    sdk_open_structure, sdk_rotate_view, sdk_surface_view,
    sdk_mutate_residue, sdk_snapshot,
    sdk_dock_ligand, sdk_generate_candidates,
]


def create_proteosurf_mcp_server():
    """Create an in-process MCP server with all Proteosurf tools."""
    return create_sdk_mcp_server(
        name="proteosurf",
        version="0.1.0",
        tools=ALL_SDK_TOOLS,
    )


def build_agent_options(**overrides) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions with the Proteosurf MCP server attached."""
    server = create_proteosurf_mcp_server()
    tool_names = [f"mcp__proteosurf__{t._tool_name}" for t in ALL_SDK_TOOLS]

    defaults = {
        "system_prompt": SYSTEM_PROMPT,
        "mcp_servers": {"proteosurf": server},
        "allowed_tools": tool_names,
    }
    defaults.update(overrides)
    return ClaudeAgentOptions(**defaults)


async def run_agent_query(user_message: str, **overrides) -> str:
    """One-shot query using the Claude Agent SDK.

    Returns the agent's final text response.
    """
    options = build_agent_options(**overrides)
    async with ClaudeSDKClient(options=options) as client:
        result = await client.query(user_message)
        return result if isinstance(result, str) else str(result)
