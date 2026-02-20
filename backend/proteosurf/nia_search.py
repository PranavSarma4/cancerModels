"""
Nia by Nozomio integration for research paper and documentation search.

Uses Nia's universal search API to find relevant protein research papers,
bioinformatics documentation, and package references to enrich AI responses
with up-to-date scientific context.

Track: Best use of Nia by Nozomio
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

NIA_API_KEY = os.environ.get("NIA_API_KEY", "")
NIA_BASE_URL = "https://apigcp.trynia.ai/v2"

# Fallback: try the Python SDK if available
_HAS_NIA_SDK = False
try:
    from nia_py.sdk import NiaSDK
    _HAS_NIA_SDK = True
except ImportError:
    pass


def _nia_client():
    if not NIA_API_KEY:
        raise ValueError(
            "NIA_API_KEY not set. Get one at app.trynia.ai"
        )
    if _HAS_NIA_SDK:
        return NiaSDK(api_key=NIA_API_KEY)
    return None


def _nia_rest_search(query: str, top_k: int = 5) -> dict:
    """Fallback REST API call when the SDK is not installed."""
    if not NIA_API_KEY:
        raise ValueError("NIA_API_KEY not set")

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{NIA_BASE_URL}/search/universal",
            headers={
                "Authorization": f"Bearer {NIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"query": query, "top_k": top_k},
        )
        resp.raise_for_status()
        return resp.json()


def search_protein_research(
    query: str,
    pdb_id: str = "",
    top_k: int = 8,
) -> str:
    """Search scientific literature and documentation for protein-related information.

    Uses Nia's universal search to find relevant research papers, package
    documentation, and code examples related to the protein or analysis
    being performed.

    Args:
        query: Natural language search query about the protein or technique.
        pdb_id: Optional PDB ID to include in the search for specificity.
        top_k: Number of results to return (max 15).

    Returns:
        JSON with search results including titles, snippets, and source URLs.
    """
    top_k = min(top_k, 15)
    search_query = f"{query} {pdb_id}".strip() if pdb_id else query

    try:
        sdk = _nia_client()
        if sdk:
            results = sdk.search.universal(query=search_query, top_k=top_k)
            return json.dumps({
                "status": "ok",
                "query": search_query,
                "source": "nia_sdk",
                "results": _format_results(results),
            }, indent=2)
        else:
            results = _nia_rest_search(search_query, top_k)
            return json.dumps({
                "status": "ok",
                "query": search_query,
                "source": "nia_rest_api",
                "results": results,
            }, indent=2)

    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"Nia API error: {exc.response.status_code}"})
    except Exception as exc:
        return json.dumps({"error": f"Search failed: {exc}"})


def search_bioinformatics_docs(
    package_name: str,
    query: str = "",
) -> str:
    """Search bioinformatics package documentation using Nia.

    Nia has 3,000+ pre-indexed packages. This searches documentation
    for tools like BioPython, RDKit, PyMOL, MDAnalysis, etc.

    Args:
        package_name: Name of the package to search docs for.
        query: Specific question about the package (optional).

    Returns:
        JSON with documentation search results.
    """
    search_query = f"{package_name} {query}".strip()

    try:
        sdk = _nia_client()
        if sdk:
            results = sdk.search.universal(query=search_query, top_k=5)
            return json.dumps({
                "status": "ok",
                "package": package_name,
                "query": search_query,
                "source": "nia_sdk",
                "results": _format_results(results),
            }, indent=2)
        else:
            results = _nia_rest_search(search_query, 5)
            return json.dumps({
                "status": "ok",
                "package": package_name,
                "query": search_query,
                "source": "nia_rest_api",
                "results": results,
            }, indent=2)

    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        return json.dumps({"error": f"Documentation search failed: {exc}"})


def deep_research(query: str) -> str:
    """Run a deep multi-step research query using Nia for comprehensive analysis.

    This uses Nia's deep research mode which performs multi-step searches
    with citations, ideal for complex scientific questions about protein
    structure-function relationships.

    Args:
        query: A complex research question about structural biology or drug discovery.

    Returns:
        JSON with deep research results including citations.
    """
    try:
        sdk = _nia_client()
        if sdk:
            results = sdk.search.deep(query=query)
            return json.dumps({
                "status": "ok",
                "query": query,
                "source": "nia_deep_research",
                "results": _format_results(results),
            }, indent=2)
        else:
            return json.dumps({"error": "Deep research requires the nia-ai-py SDK. pip install nia-ai-py"})

    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        return json.dumps({"error": f"Deep research failed: {exc}"})


def _format_results(results: Any) -> Any:
    """Normalize Nia SDK results into a consistent format."""
    if isinstance(results, list):
        return [
            {
                "title": getattr(r, "title", str(r)[:100]),
                "snippet": getattr(r, "snippet", getattr(r, "content", str(r)[:500])),
                "url": getattr(r, "url", getattr(r, "source", "")),
                "score": getattr(r, "score", None),
            }
            for r in results
        ]
    if isinstance(results, dict):
        return results
    return {"raw": str(results)[:2000]}
