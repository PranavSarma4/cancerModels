"""
Databricks integration for protein analytics and experiment tracking.

Uses MLflow (hosted on Databricks) to track docking experiments, log
protein analysis results, and query historical experiment data.

Track: Best use of Databricks
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI",
    f"databricks" if DATABRICKS_HOST else "",
)

_HAS_MLFLOW = False
try:
    import mlflow
    from mlflow.tracking import MlflowClient
    _HAS_MLFLOW = True
except ImportError:
    pass


def _configure_mlflow():
    """Configure MLflow to point at Databricks."""
    if not _HAS_MLFLOW:
        raise ImportError("mlflow not installed. pip install mlflow databricks-sdk")
    if DATABRICKS_HOST:
        os.environ.setdefault("DATABRICKS_HOST", DATABRICKS_HOST)
        os.environ.setdefault("DATABRICKS_TOKEN", DATABRICKS_TOKEN)
        mlflow.set_tracking_uri("databricks")
    elif MLFLOW_TRACKING_URI:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    else:
        mlflow.set_tracking_uri("mlruns")


def log_docking_experiment(
    pdb_id: str,
    ligand_smiles: str,
    binding_affinity: float,
    pocket_rank: int = 1,
    box_center: list[float] | None = None,
    box_size: float = 25.0,
    extra_metrics: dict[str, float] | None = None,
    extra_params: dict[str, str] | None = None,
) -> str:
    """Log a molecular docking run to Databricks MLflow for experiment tracking.

    Args:
        pdb_id: PDB identifier of the receptor.
        ligand_smiles: SMILES string of the docked ligand.
        binding_affinity: Best binding affinity in kcal/mol.
        pocket_rank: Which pocket was targeted (from find_pockets).
        box_center: [x, y, z] center of the docking box.
        box_size: Side length of docking box in Angstroms.
        extra_metrics: Additional numeric metrics to log.
        extra_params: Additional string parameters to log.

    Returns:
        JSON with the MLflow run ID and experiment details.
    """
    try:
        _configure_mlflow()
    except ImportError as exc:
        return json.dumps({"error": str(exc)})

    experiment_name = f"/proteosurf/docking/{pdb_id}"
    try:
        mlflow.set_experiment(experiment_name)
    except Exception:
        mlflow.set_experiment(f"proteosurf-docking-{pdb_id}")

    with mlflow.start_run(run_name=f"{pdb_id}_{ligand_smiles[:20]}") as run:
        mlflow.log_params({
            "pdb_id": pdb_id,
            "ligand_smiles": ligand_smiles[:250],
            "pocket_rank": str(pocket_rank),
            "box_size": str(box_size),
            "box_center": json.dumps(box_center or [0, 0, 0]),
            **(extra_params or {}),
        })

        mlflow.log_metrics({
            "binding_affinity_kcal": binding_affinity,
            "pocket_rank": pocket_rank,
            "box_size": box_size,
            **(extra_metrics or {}),
        })

        mlflow.set_tags({
            "project": "proteosurf",
            "task": "docking",
            "receptor": pdb_id,
        })

        return json.dumps({
            "status": "ok",
            "run_id": run.info.run_id,
            "experiment_name": experiment_name,
            "experiment_id": run.info.experiment_id,
            "tracking_uri": mlflow.get_tracking_uri(),
            "message": f"Docking experiment logged for {pdb_id} + {ligand_smiles[:30]}",
        }, indent=2)


def log_protein_analysis(
    pdb_id: str,
    analysis_type: str,
    results_summary: str,
    metrics: dict[str, float] | None = None,
) -> str:
    """Log a protein analysis run (pocket detection, residue listing, etc.) to MLflow.

    Args:
        pdb_id: PDB identifier analyzed.
        analysis_type: Type of analysis ('pocket_detection', 'residue_analysis', etc.).
        results_summary: Brief text summary of results.
        metrics: Numeric metrics from the analysis.

    Returns:
        JSON with the MLflow run ID.
    """
    try:
        _configure_mlflow()
    except ImportError as exc:
        return json.dumps({"error": str(exc)})

    experiment_name = f"/proteosurf/analysis/{analysis_type}"
    try:
        mlflow.set_experiment(experiment_name)
    except Exception:
        mlflow.set_experiment(f"proteosurf-{analysis_type}")

    with mlflow.start_run(run_name=f"{pdb_id}_{analysis_type}") as run:
        mlflow.log_params({
            "pdb_id": pdb_id,
            "analysis_type": analysis_type,
        })
        if metrics:
            mlflow.log_metrics(metrics)
        mlflow.set_tags({
            "project": "proteosurf",
            "task": analysis_type,
        })
        mlflow.log_text(results_summary, "results_summary.txt")

        return json.dumps({
            "status": "ok",
            "run_id": run.info.run_id,
            "experiment_name": experiment_name,
            "message": f"Analysis logged: {analysis_type} on {pdb_id}",
        }, indent=2)


def query_docking_history(
    pdb_id: str | None = None,
    max_results: int = 20,
    sort_by: str = "binding_affinity_kcal",
) -> str:
    """Query historical docking experiments from Databricks MLflow.

    Args:
        pdb_id: Filter by receptor PDB ID (optional, None = all).
        max_results: Maximum number of results to return.
        sort_by: Metric to sort by (default: binding_affinity_kcal, ascending).

    Returns:
        JSON with experiment history including best poses and binding affinities.
    """
    try:
        _configure_mlflow()
    except ImportError as exc:
        return json.dumps({"error": str(exc)})

    client = MlflowClient()

    filter_string = "tags.project = 'proteosurf' AND tags.task = 'docking'"
    if pdb_id:
        filter_string += f" AND params.pdb_id = '{pdb_id.upper()}'"

    try:
        runs = client.search_runs(
            experiment_ids=[],
            filter_string=filter_string,
            max_results=max_results,
            order_by=[f"metrics.{sort_by} ASC"],
        )
    except Exception:
        runs = []

    results = []
    for run in runs:
        results.append({
            "run_id": run.info.run_id,
            "pdb_id": run.data.params.get("pdb_id", ""),
            "ligand_smiles": run.data.params.get("ligand_smiles", ""),
            "binding_affinity": run.data.metrics.get("binding_affinity_kcal"),
            "pocket_rank": run.data.metrics.get("pocket_rank"),
            "start_time": run.info.start_time,
        })

    return json.dumps({
        "query": {"pdb_id": pdb_id, "max_results": max_results},
        "total_results": len(results),
        "experiments": results,
    }, indent=2)
