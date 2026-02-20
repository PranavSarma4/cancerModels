"""
NVIDIA Nemotron integration for protein literature summarization.

Uses Nemotron models via NVIDIA's OpenAI-compatible API at
build.nvidia.com to summarize protein research, explain structures,
and provide scientific context.

Track: Best Use of Nemotron
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NEMOTRON_MODEL = os.environ.get(
    "NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct"
)


def _nvidia_chat(messages: list[dict], temperature: float = 0.4,
                 max_tokens: int = 1024) -> dict:
    """Call the NVIDIA Nemotron API (OpenAI-compatible)."""
    if not NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY not set. Get one at build.nvidia.com")

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": NEMOTRON_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()


def summarize_protein(
    pdb_id: str,
    context: str = "",
    focus: str = "general",
) -> str:
    """Use NVIDIA Nemotron to generate a scientific summary of a protein structure.

    Leverages Nemotron's strong reasoning capabilities to synthesize information
    about protein function, clinical relevance, and structural features.

    Args:
        pdb_id: PDB identifier of the protein to summarize.
        context: Additional context (e.g. residue list, pocket data) to include.
        focus: What to focus on — 'general', 'drug_target', 'mechanism', 'mutations'.

    Returns:
        JSON with the Nemotron-generated summary and model metadata.
    """
    focus_prompts = {
        "general": "Provide a comprehensive overview of this protein's function, structure, and biological significance.",
        "drug_target": "Analyze this protein as a potential drug target. Discuss druggability, known inhibitors, binding sites, and therapeutic relevance.",
        "mechanism": "Explain the molecular mechanism of action of this protein. Describe catalytic residues, conformational changes, and substrate interactions.",
        "mutations": "Discuss known clinically relevant mutations in this protein, their effects on structure/function, and associated diseases.",
    }

    prompt = focus_prompts.get(focus, focus_prompts["general"])

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert structural biologist and biochemist. "
                "Provide clear, accurate, scientifically rigorous summaries "
                "of protein structures. Cite specific residue numbers and "
                "structural features. Be accessible to graduate students."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Summarize protein structure PDB: {pdb_id}\n"
                f"Focus: {prompt}\n"
                f"\nAdditional context:\n{context[:3000]}" if context else
                f"Summarize protein structure PDB: {pdb_id}\n"
                f"Focus: {prompt}"
            ),
        },
    ]

    try:
        response = _nvidia_chat(messages, temperature=0.3, max_tokens=1500)
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})

        return json.dumps({
            "status": "ok",
            "pdb_id": pdb_id,
            "focus": focus,
            "summary": content,
            "model": NEMOTRON_MODEL,
            "tokens_used": {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
            },
        }, indent=2)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"Nemotron API error: {exc.response.status_code}"})


def compare_structures(
    pdb_id_1: str,
    pdb_id_2: str,
    context_1: str = "",
    context_2: str = "",
) -> str:
    """Use Nemotron to compare two protein structures and highlight differences.

    Args:
        pdb_id_1: First PDB identifier.
        pdb_id_2: Second PDB identifier.
        context_1: Structural data for the first protein.
        context_2: Structural data for the second protein.

    Returns:
        JSON with a comparative analysis from Nemotron.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert structural biologist. Compare protein "
                "structures with scientific rigor, noting differences in "
                "fold, active sites, and functional implications."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Compare these two protein structures:\n\n"
                f"Protein 1 — PDB: {pdb_id_1}\n{context_1[:2000]}\n\n"
                f"Protein 2 — PDB: {pdb_id_2}\n{context_2[:2000]}\n\n"
                "Discuss structural similarities and differences, functional "
                "implications, and evolutionary relationship."
            ),
        },
    ]

    try:
        response = _nvidia_chat(messages, temperature=0.3, max_tokens=1500)
        content = response["choices"][0]["message"]["content"]

        return json.dumps({
            "status": "ok",
            "pdb_id_1": pdb_id_1,
            "pdb_id_2": pdb_id_2,
            "comparison": content,
            "model": NEMOTRON_MODEL,
        }, indent=2)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"Nemotron API error: {exc.response.status_code}"})
