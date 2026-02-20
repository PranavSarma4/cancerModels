"""
ProteoAgent — Claude-powered orchestrator for structural biology queries.

Takes natural-language messages, routes them through Claude with MCP tools
available as function calls, executes tool calls, and streams results.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from functools import partial
from typing import Any, AsyncIterator

import httpx

from . import tools, chimerax_tools, docking, voice
from . import databricks_analytics, nemotron, market_intel, nia_search

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """\
You are Proteosurf — Windsurf for biology. You turn a Chromebook into a cinematic \
structural-biology workstation. You are a chemical-biology assistant built for \
students, researchers, and drug-hunters who want to interrogate proteins the way a \
mechanic dissects an engine.

Your north-star story: 1,600 people die of cancer every day. KRAS was "undruggable" \
for 40 years until Kevan Shokat at UCSF found a hidden allosteric pocket in the \
GDP-bound (inactive) Switch-II region of KRAS G12C. That discovery led to sotorasib \
(Lumakras, Amgen — FDA approved 2021) and adagrasib (Krazati, Mirati — 2022). You \
exist so any student can replicate that kind of insight.

STRUCTURAL-BIOLOGY KNOWLEDGE (use this to give accurate answers):
- KRAS: PDB 4LDJ (G12C·GDP, 1.15 A, Switch-II pocket visible), \
  4OBE (wild-type KRAS·GDP, 1.24 A), 6OIM (G12C covalently bound to sotorasib/AMG 510, 1.65 A), \
  5P21 (wild-type HRAS·GppNHp, classic Ras structure). UniProt P01116 (KRAS4B).
- KRAS Switch-II pocket: allosteric pocket beneath the switch-II loop (res ~58-72) first \
  identified by Ostrem, Peters, Sos, Shokat et al. (Nature 2013). Cys12 in G12C mutant is \
  covalently targeted. The pocket forms between switch-I (res 30-40) and switch-II (res 58-72). \
  Key contact residues include H95, Y96, Q99 in the S-IIP.
- p53: PDB 2XWR (wild-type DBD with extended N-terminus, Joerger et al.), \
  1TSR (classic wild-type core domain, Cho et al. 1994). UniProt P04637. \
  Mutated in >50% of cancers. Common hotspot mutations: R175H, G245S, R248W, R249S, R273H, R282W. \
  Use fetch_structure to find specific mutant PDB entries.
- EGFR: PDB 1M17 (kinase domain + erlotinib, Stamos et al. 2002). Lung cancer driver. \
  T790M gatekeeper mutation confers resistance to first-gen TKIs.
- BCR-ABL: PDB 1IEP (ABL kinase + imatinib), 2HYY (ABL + dasatinib). CML target.
- BCL-2: PDB 6O0K (BCL-2 + venetoclax). UniProt Q07817. Apoptosis regulator. \
  Venetoclax (ABT-199) is FDA-approved for CLL.
- Siglecs: immunomodulatory receptors binding sialic acid on glycoproteins. \
  PDB 2HRL (Siglec-2/CD22). Cancer immunotherapy relevance — tumors exploit \
  sialic acid to evade immune detection.
- AlphaFold: access via UniProt accession. Predictions cover >200M proteins. \
  pLDDT confidence: >90 = high accuracy, 70-90 = good backbone, 50-70 = low confidence, \
  <50 = likely disordered.

Capabilities & tools:
- fetch_structure / fetch_alphafold — retrieve experimental or predicted coordinates
- list_residues — enumerate residues, heteroatoms, water for a chain
- find_pockets — geometry-based burial analysis to locate surface cavities
- find_contacts — identify binding contacts (protein-ligand, protein-protein, glycan-receptor)
- highlight_residues — generate ChimeraX coloring scripts for key residues
- open_structure / rotate_view / surface_view / mutate_residue / snapshot — ChimeraX control
- dock_ligand — full AutoDock Vina pipeline (receptor prep, SMILES→3D, docking)
- generate_candidates — fragment-based molecule suggestion biased by pocket chemistry
- narrate_analysis — ElevenLabs voice narration of findings
- log_docking_experiment / log_protein_analysis / query_docking_history — MLflow tracking
- summarize_protein / compare_structures — NVIDIA Nemotron scientific summarization
- search_protein_research / deep_research — Nia literature search with citations
- pharma_market_intel / target_pipeline_report — TrueMarket drug-market intelligence

Guidelines:
- Be scientifically rigorous. Cite specific residue numbers (e.g. "Cys12 on KRAS \
  switch-II loop"), real PDB codes, and known biological mechanisms.
- When a user asks about a protein, fetch the structure FIRST, then analyze. \
  Don't guess what residues are in a pocket — run find_pockets to determine them.
- Explain everything like you're talking to a smart high-schooler who can learn fast.
- After analysis, offer voice narration so the student can listen while looking at \
  the 3D viewer.
- Report binding energies in kcal/mol. Explain: < -7 is promising, < -9 is strong.
- When comparing mutant vs wild-type, highlight which residues differ and what that \
  does to the binding surface.
- For cancer targets, connect to clinical relevance: what drugs target this? What \
  mutations cause resistance?

Common workflows:
- "Show me KRAS G12C" → fetch_structure(4LDJ) → find_pockets → highlight Switch-II pocket residues → summarize_protein(focus=drug_target)
- "How does sotorasib bind KRAS?" → fetch_structure(6OIM) → find_contacts(target=ligand) → highlight contact residues
- "Find druggable pockets in EGFR" → fetch_structure(1M17) → find_pockets → pharma_market_intel
- "Compare p53 wild-type vs mutant" → fetch_structure(2XWR) → compare_structures
- "Show me Siglec binding contacts" → fetch_structure(2HRL) → find_contacts → highlight binding interface
- "Dock a molecule into BCR-ABL" → fetch_structure(1IEP) → find_pockets → dock_ligand → log_docking_experiment
"""

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    # Core tools
    "fetch_structure": {
        "fn": tools.fetch_structure,
        "description": "Download a PDB file from RCSB and return its contents.",
        "input_schema": {
            "type": "object",
            "properties": {"pdb_id": {"type": "string", "description": "4-character PDB identifier"}},
            "required": ["pdb_id"],
        },
    },
    "fetch_alphafold": {
        "fn": tools.fetch_alphafold,
        "description": "Fetch a predicted structure from AlphaFold DB.",
        "input_schema": {
            "type": "object",
            "properties": {"uniprot_id": {"type": "string", "description": "UniProt accession"}},
            "required": ["uniprot_id"],
        },
    },
    "list_residues": {
        "fn": tools.list_residues,
        "description": "List all residues for a chain in a PDB structure.",
        "input_schema": {
            "type": "object",
            "properties": {"pdb_id": {"type": "string"}, "chain": {"type": "string"}},
            "required": ["pdb_id", "chain"],
        },
    },
    "highlight_residues": {
        "fn": tools.highlight_residues,
        "description": "Generate a ChimeraX script to color specific residues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"}, "residues": {"type": "array", "items": {"type": "integer"}},
                "color": {"type": "string", "default": "red"}, "chain": {"type": "string", "default": "A"},
            },
            "required": ["pdb_id", "residues"],
        },
    },
    "find_pockets": {
        "fn": tools.find_pockets,
        "description": "Detect binding pockets using geometry-based burial analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"},
                "sensitivity": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["pdb_id"],
        },
    },
    "find_contacts": {
        "fn": tools.find_contacts,
        "description": "Find binding contacts between a protein chain and ligands or another chain. Returns residues within a distance cutoff — use for mapping drug-protein contacts, protein-protein interfaces, or glycan-receptor contacts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string", "description": "4-character PDB identifier"},
                "chain": {"type": "string", "description": "Protein chain to analyze (default 'A')"},
                "distance": {"type": "number", "description": "Contact distance cutoff in Angstroms (default 4.0)"},
                "target": {"type": "string", "description": "'ligand' for HETATM groups, or a chain ID like 'B' for inter-chain contacts"},
            },
            "required": ["pdb_id"],
        },
    },
    # ChimeraX tools
    "open_structure": {
        "fn": chimerax_tools.open_structure,
        "description": "Open a PDB structure in ChimeraX and return a screenshot.",
        "input_schema": {"type": "object", "properties": {"pdb_id": {"type": "string"}}, "required": ["pdb_id"]},
    },
    "rotate_view": {
        "fn": chimerax_tools.rotate_view,
        "description": "Rotate the current ChimeraX view.",
        "input_schema": {"type": "object", "properties": {"axis": {"type": "string"}, "angle": {"type": "number"}}},
    },
    "surface_view": {
        "fn": chimerax_tools.surface_view,
        "description": "Switch ChimeraX representation.",
        "input_schema": {"type": "object", "properties": {"representation": {"type": "string"}, "transparency": {"type": "number"}}},
    },
    "mutate_residue": {
        "fn": chimerax_tools.mutate_residue,
        "description": "Mutate a residue in ChimeraX.",
        "input_schema": {"type": "object", "properties": {"chain": {"type": "string"}, "resseq": {"type": "integer"}, "new_residue": {"type": "string"}}, "required": ["chain", "resseq", "new_residue"]},
    },
    "snapshot": {
        "fn": chimerax_tools.take_snapshot,
        "description": "Capture a screenshot of the current ChimeraX view.",
        "input_schema": {"type": "object", "properties": {"width": {"type": "integer"}, "height": {"type": "integer"}, "transparent": {"type": "boolean"}}},
    },
    # Docking tools
    "dock_ligand": {
        "fn": docking.dock_ligand,
        "description": "Dock a ligand (SMILES) into a protein using AutoDock Vina.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"}, "smiles": {"type": "string"},
                "center_x": {"type": "number"}, "center_y": {"type": "number"},
                "center_z": {"type": "number"}, "box_size": {"type": "number"},
                "exhaustiveness": {"type": "integer"},
            },
            "required": ["pdb_id", "smiles"],
        },
    },
    "generate_candidates": {
        "fn": docking.generate_candidates,
        "description": "Suggest small molecules for a binding pocket.",
        "input_schema": {
            "type": "object",
            "properties": {"pocket_residues": {"type": "array", "items": {"type": "string"}}, "num": {"type": "integer"}},
            "required": ["pocket_residues"],
        },
    },
    # ElevenLabs voice
    "narrate_analysis": {
        "fn": voice.narrate_analysis,
        "description": "Convert protein analysis text to spoken audio using ElevenLabs TTS. Returns base64 MP3 audio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to narrate (max ~5000 chars)"},
                "voice_id": {"type": "string"},
                "stability": {"type": "number"},
            },
            "required": ["text"],
        },
    },
    "list_voices": {
        "fn": voice.list_voices,
        "description": "List available ElevenLabs voices for narration.",
        "input_schema": {"type": "object", "properties": {}},
    },
    # Databricks MLflow
    "log_docking_experiment": {
        "fn": databricks_analytics.log_docking_experiment,
        "description": "Log a molecular docking run to Databricks MLflow for experiment tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"}, "ligand_smiles": {"type": "string"},
                "binding_affinity": {"type": "number"}, "pocket_rank": {"type": "integer"},
                "box_center": {"type": "array", "items": {"type": "number"}}, "box_size": {"type": "number"},
            },
            "required": ["pdb_id", "ligand_smiles", "binding_affinity"],
        },
    },
    "log_protein_analysis": {
        "fn": databricks_analytics.log_protein_analysis,
        "description": "Log a protein analysis run to Databricks MLflow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"}, "analysis_type": {"type": "string"},
                "results_summary": {"type": "string"}, "metrics": {"type": "object"},
            },
            "required": ["pdb_id", "analysis_type", "results_summary"],
        },
    },
    "query_docking_history": {
        "fn": databricks_analytics.query_docking_history,
        "description": "Query historical docking experiments from Databricks MLflow.",
        "input_schema": {
            "type": "object",
            "properties": {"pdb_id": {"type": "string"}, "max_results": {"type": "integer"}},
        },
    },
    # Nemotron
    "summarize_protein": {
        "fn": nemotron.summarize_protein,
        "description": "Use NVIDIA Nemotron to generate a scientific summary of a protein structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"}, "context": {"type": "string"},
                "focus": {"type": "string", "enum": ["general", "drug_target", "mechanism", "mutations"]},
            },
            "required": ["pdb_id"],
        },
    },
    "compare_structures": {
        "fn": nemotron.compare_structures,
        "description": "Use NVIDIA Nemotron to compare two protein structures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id_1": {"type": "string"}, "pdb_id_2": {"type": "string"},
                "context_1": {"type": "string"}, "context_2": {"type": "string"},
            },
            "required": ["pdb_id_1", "pdb_id_2"],
        },
    },
    # TrueMarket
    "pharma_market_intel": {
        "fn": market_intel.pharma_market_intel,
        "description": "Get pharma market intelligence for a protein drug target using TrueMarket API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pdb_id": {"type": "string"},
                "pocket_residues": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["pdb_id"],
        },
    },
    "target_pipeline_report": {
        "fn": market_intel.target_pipeline_report,
        "description": "Generate a drug development pipeline report for a protein target.",
        "input_schema": {
            "type": "object",
            "properties": {"pdb_id": {"type": "string"}},
            "required": ["pdb_id"],
        },
    },
    # Nia research search
    "search_protein_research": {
        "fn": nia_search.search_protein_research,
        "description": "Search scientific literature and documentation for protein-related information using Nia by Nozomio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "pdb_id": {"type": "string"}, "top_k": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    "search_bioinformatics_docs": {
        "fn": nia_search.search_bioinformatics_docs,
        "description": "Search bioinformatics package documentation using Nia.",
        "input_schema": {
            "type": "object",
            "properties": {"package_name": {"type": "string"}, "query": {"type": "string"}},
            "required": ["package_name"],
        },
    },
    "deep_research": {
        "fn": nia_search.deep_research,
        "description": "Run a deep multi-step research query using Nia for comprehensive analysis with citations.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": spec["description"], "input_schema": spec["input_schema"]}
        for name, spec in TOOL_REGISTRY.items()
    ]


def _execute_tool(name: str, arguments: dict[str, Any]) -> str:
    spec = TOOL_REGISTRY.get(name)
    if not spec:
        return f"Error: Unknown tool '{name}'"
    try:
        logger.info("Executing tool %s with %s", name, list(arguments.keys()))
        result = spec["fn"](**arguments)
        logger.info("Tool %s completed (%d chars)", name, len(result))
        return result
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return f"Error executing {name}: {exc}"


# ---------------------------------------------------------------------------
# Stream event types
# ---------------------------------------------------------------------------

@dataclass
class TextDelta:
    text: str

@dataclass
class ToolUse:
    tool_name: str
    tool_input: dict[str, Any]
    result: str

@dataclass
class ImageResult:
    base64_png: str
    caption: str

@dataclass
class AudioResult:
    base64_mp3: str
    caption: str

@dataclass
class StreamEnd:
    pass

StreamEvent = TextDelta | ToolUse | ImageResult | AudioResult | StreamEnd


# ---------------------------------------------------------------------------
# ProteoAgent
# ---------------------------------------------------------------------------

class ProteoAgent:
    """Orchestrates Claude + MCP tools for structural biology queries."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or CLAUDE_MODEL
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.conversation: list[dict[str, Any]] = []

    async def chat(self, user_message: str) -> AsyncIterator[StreamEvent]:
        self.conversation.append({"role": "user", "content": user_message})
        messages = list(self.conversation)
        max_rounds = 10

        for _ in range(max_rounds):
            response = await self._call_claude(messages)

            has_tool_use = False
            text_parts: list[str] = []
            tool_results: list[dict[str, Any]] = []

            for block in response.get("content", []):
                if block["type"] == "text":
                    text_parts.append(block["text"])
                    yield TextDelta(text=block["text"])

                elif block["type"] == "tool_use":
                    has_tool_use = True
                    tool_name = block["name"]
                    tool_input = block["input"]

                    yield ToolUse(tool_name=tool_name, tool_input=tool_input, result="")

                    loop = asyncio.get_running_loop()
                    result_str = await loop.run_in_executor(
                        None, partial(_execute_tool, tool_name, tool_input)
                    )

                    try:
                        result_data = json.loads(result_str)
                        if isinstance(result_data, dict):
                            if "image_base64" in result_data:
                                yield ImageResult(
                                    base64_png=result_data["image_base64"],
                                    caption=f"{tool_name} result",
                                )
                            if "audio_base64" in result_data:
                                yield AudioResult(
                                    base64_mp3=result_data["audio_base64"],
                                    caption=f"Voice narration",
                                )
                    except (json.JSONDecodeError, TypeError):
                        pass

                    yield ToolUse(tool_name=tool_name, tool_input=tool_input, result=result_str[:2000])

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result_str[:4000],
                    })

            messages.append({"role": "assistant", "content": response["content"]})

            if not has_tool_use or response.get("stop_reason") == "end_turn":
                self.conversation.append({"role": "assistant", "content": "\n".join(text_parts)})
                break

            messages.append({"role": "user", "content": tool_results})

        yield StreamEnd()

    async def _call_claude(self, messages: list[dict]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "tools": _tool_definitions(),
            "messages": messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                import logging
                logging.error("Anthropic API error %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return resp.json()

    def reset(self) -> None:
        self.conversation.clear()
