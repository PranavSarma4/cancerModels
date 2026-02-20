"""
TrueMarket API integration for pharma market intelligence.

Links protein drug targets to financial market data — when analyzing a
drug target, show which companies are working on it and relevant market
signals using the TrueMarket API.

Track: Best use of TrueMarket API
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

import httpx

TRUEMARKET_API_URL = os.environ.get(
    "TRUEMARKET_API_URL", "https://api.truemarkets.co"
)
TRUEMARKET_API_KEY = os.environ.get("TRUEMARKET_API_KEY", "")
TRUEMARKET_API_SECRET = os.environ.get("TRUEMARKET_API_SECRET", "")

# Well-known pharma/biotech companies and their protein targets
PHARMA_TARGET_MAP: dict[str, list[dict[str, str]]] = {
    "kinase": [
        {"company": "Novartis", "ticker": "NVS", "drug": "Imatinib (Gleevec)"},
        {"company": "Pfizer", "ticker": "PFE", "drug": "Crizotinib (Xalkori)"},
        {"company": "AstraZeneca", "ticker": "AZN", "drug": "Osimertinib (Tagrisso)"},
    ],
    "protease": [
        {"company": "Pfizer", "ticker": "PFE", "drug": "Nirmatrelvir (Paxlovid)"},
        {"company": "Merck", "ticker": "MRK", "drug": "Boceprevir (Victrelis)"},
        {"company": "AbbVie", "ticker": "ABBV", "drug": "Glecaprevir (Mavyret)"},
    ],
    "gpcr": [
        {"company": "Eli Lilly", "ticker": "LLY", "drug": "Tirzepatide (Mounjaro)"},
        {"company": "Novo Nordisk", "ticker": "NVO", "drug": "Semaglutide (Ozempic)"},
    ],
    "ion_channel": [
        {"company": "Biogen", "ticker": "BIIB", "drug": "Various CNS targets"},
        {"company": "Neurocrine Bio", "ticker": "NBIX", "drug": "Valbenazine (Ingrezza)"},
    ],
    "immune_checkpoint": [
        {"company": "Merck", "ticker": "MRK", "drug": "Pembrolizumab (Keytruda)"},
        {"company": "Bristol-Myers Squibb", "ticker": "BMY", "drug": "Nivolumab (Opdivo)"},
        {"company": "Roche", "ticker": "RHHBY", "drug": "Atezolizumab (Tecentriq)"},
    ],
    "hemoglobin": [
        {"company": "Vertex Pharma", "ticker": "VRTX", "drug": "Casgevy (gene therapy)"},
        {"company": "bluebird bio", "ticker": "BLUE", "drug": "Lyfgenia (gene therapy)"},
    ],
}


def _classify_target(pdb_id: str, pocket_residues: list[str] | None = None) -> str:
    """Simple heuristic to classify a protein target type."""
    pdb_upper = pdb_id.upper()
    # Well-known PDB structures
    known = {
        "1HBS": "hemoglobin", "4HHB": "hemoglobin", "2HHB": "hemoglobin",
        "1ATP": "kinase", "2SRC": "kinase", "3ERT": "nuclear_receptor",
        "6LU7": "protease", "7L10": "protease",
        "5C1M": "gpcr", "4DKL": "gpcr",
        "5J8O": "immune_checkpoint", "5GGV": "immune_checkpoint",
    }
    if pdb_upper in known:
        return known[pdb_upper]

    if pocket_residues:
        residue_names = {r.split(":")[-1][:3] for r in pocket_residues}
        catalytic = {"HIS", "ASP", "SER", "CYS"}
        if len(residue_names & catalytic) >= 2:
            return "protease"

    return "kinase"  # default fallback


def _hmac_sign(message: str) -> str:
    """Generate HMAC-SHA256 signature for TrueMarket API auth."""
    return hmac.new(
        TRUEMARKET_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def _query_truemarket(endpoint: str, params: dict | None = None) -> dict | None:
    """Query TrueMarket API with authentication."""
    if not TRUEMARKET_API_KEY:
        return None

    timestamp = str(int(time.time() * 1000))
    sign_payload = f"{timestamp}{TRUEMARKET_API_KEY}"
    signature = _hmac_sign(sign_payload) if TRUEMARKET_API_SECRET else ""

    headers = {
        "X-API-Key": TRUEMARKET_API_KEY,
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{TRUEMARKET_API_URL}{endpoint}",
                headers=headers,
                params=params,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def pharma_market_intel(
    pdb_id: str,
    pocket_residues: list[str] | None = None,
) -> str:
    """Get pharma market intelligence related to a protein drug target.

    Connects structural biology analysis to financial markets by identifying
    which pharmaceutical companies are developing drugs for the analyzed target
    and pulling relevant market data from TrueMarket API.

    Args:
        pdb_id: PDB identifier of the drug target being analyzed.
        pocket_residues: Residues from pocket detection (helps classify the target).

    Returns:
        JSON with target classification, relevant companies, and market data.
    """
    target_class = _classify_target(pdb_id, pocket_residues)
    companies = PHARMA_TARGET_MAP.get(target_class, PHARMA_TARGET_MAP["kinase"])

    market_data = None
    tickers = [c["ticker"] for c in companies]

    truemarket_result = _query_truemarket(
        "/v1/market/instruments",
        params={"symbols": ",".join(tickers)},
    )

    if truemarket_result:
        market_data = truemarket_result
    else:
        market_data = {
            "source": "pharma_target_database",
            "note": "Live market data requires TRUEMARKET_API_KEY. Showing curated pharma intelligence.",
        }

    result: dict[str, Any] = {
        "pdb_id": pdb_id.upper(),
        "target_classification": target_class,
        "drug_development_landscape": {
            "target_type": target_class,
            "companies": companies,
            "pipeline_status": "Active clinical programs exist for this target class",
        },
        "market_data": market_data,
        "investment_thesis": (
            f"Proteins in the {target_class} class represent validated drug targets "
            f"with {len(companies)} major pharma companies actively developing therapies. "
            f"Pocket detection and docking results can inform structure-based drug design "
            f"efforts for next-generation compounds."
        ),
    }

    return json.dumps(result, indent=2)


def target_pipeline_report(pdb_id: str) -> str:
    """Generate a drug development pipeline report for a protein target.

    Args:
        pdb_id: PDB identifier of the target.

    Returns:
        JSON report with pipeline stage analysis and market context.
    """
    target_class = _classify_target(pdb_id)
    companies = PHARMA_TARGET_MAP.get(target_class, [])

    stages = {
        "preclinical": "Structure-based drug design, lead optimization",
        "phase_1": "Safety and dosing studies",
        "phase_2": "Efficacy in target population",
        "phase_3": "Large-scale efficacy and safety",
        "approved": "FDA-approved therapies on market",
    }

    report = {
        "pdb_id": pdb_id.upper(),
        "target_class": target_class,
        "pipeline_stages": stages,
        "active_programs": [
            {**c, "stage": "approved" if c.get("drug") else "preclinical"}
            for c in companies
        ],
        "market_opportunity": (
            f"The {target_class} therapeutic area represents a multi-billion dollar "
            f"market with significant unmet medical need. Structural insights from "
            f"Proteosurf analysis can accelerate early-stage drug discovery."
        ),
    }

    return json.dumps(report, indent=2)
