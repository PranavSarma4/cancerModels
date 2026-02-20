"""
MCP server entry point — registers all tools with FastMCP.

Sponsors integrated:
  - Claude Agent SDK (via claude_agent.py)
  - ElevenLabs (voice.py)
  - Databricks MLflow (databricks_analytics.py)
  - NVIDIA Nemotron (nemotron.py)
  - TrueMarket API (market_intel.py)
  - Nia by Nozomio (nia_search.py)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import tools, chimerax_tools, docking, voice, databricks_analytics
from . import nemotron, market_intel, nia_search

mcp = FastMCP(
    "proteosurf",
    instructions=(
        "Proteosurf: AI-powered structural biology assistant. "
        "Fetch PDB/AlphaFold structures, inspect residues, detect pockets, "
        "control ChimeraX, dock ligands, narrate analysis with voice, "
        "track experiments in Databricks, summarize with Nemotron, "
        "search literature with Nia, and get pharma market intelligence."
    ),
)

# --- Core structural biology tools ---
mcp.tool()(tools.fetch_structure)
mcp.tool()(tools.fetch_alphafold)
mcp.tool()(tools.list_residues)
mcp.tool()(tools.highlight_residues)
mcp.tool()(tools.find_pockets)

# --- ChimeraX tools ---
mcp.tool()(chimerax_tools.open_structure)
mcp.tool()(chimerax_tools.rotate_view)
mcp.tool()(chimerax_tools.surface_view)
mcp.tool()(chimerax_tools.mutate_residue)
mcp.tool(name="snapshot")(chimerax_tools.take_snapshot)

# --- Docking tools ---
mcp.tool()(docking.dock_ligand)
mcp.tool()(docking.generate_candidates)

# --- ElevenLabs voice narration ---
mcp.tool()(voice.narrate_analysis)
mcp.tool()(voice.list_voices)

# --- Databricks MLflow experiment tracking ---
mcp.tool()(databricks_analytics.log_docking_experiment)
mcp.tool()(databricks_analytics.log_protein_analysis)
mcp.tool()(databricks_analytics.query_docking_history)

# --- NVIDIA Nemotron summarization ---
mcp.tool()(nemotron.summarize_protein)
mcp.tool()(nemotron.compare_structures)

# --- TrueMarket pharma intelligence ---
mcp.tool()(market_intel.pharma_market_intel)
mcp.tool()(market_intel.target_pipeline_report)

# --- Nia research search ---
mcp.tool()(nia_search.search_protein_research)
mcp.tool()(nia_search.search_bioinformatics_docs)
mcp.tool()(nia_search.deep_research)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
