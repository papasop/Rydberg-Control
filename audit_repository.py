#!/usr/bin/env python3
"""Repository-level audit for frozen artifacts and public rerun outputs.

This checker deliberately uses real file bytes for SHA-256 values. It does not
replace the frozen evaluator scripts; it audits the repository state around
them.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parent
VERSIONS = {
    "v2.0.1": {
        "protocol_sha256": (
            "2c05a45f5d534f581c0491a5215534ae"
            "657f3eae26e7362ea436850d51d909c4"
        ),
        "summary_all_gates_pass": False,
        "expected_selected": "v00_m_0.030",
        "expected_candidates": 60,
        "expected_heldout": 4,
    },
    "v3.0.2": {
        "protocol_sha256": (
            "c9917d5119b520fa17e1e56f1d903403"
            "b3e2d963d5a24e32e3945fbd253ba39e"
        ),
        "summary_all_gates_pass": True,
        "expected_selected": "v01_m_0.150",
        "expected_candidates": 80,
        "expected_heldout": 4,
    },
}

BYTE_HASH_FILES = [
    "README.md",
    "CORRIGENDA.md",
    "REFERENCE_RUNS.md",
    "SCIENTIFIC_HARDENING.md",
    "STRICT_AUDIT_201_302.md",
    "KNOWN_LIMITATIONS.md",
    "V201_SCIENTIFIC_SCOPE.md",
    "audit_repository.py",
    "CITATION.cff",
    "FIXES.md",
    "LICENSE",
    "requirements.txt",
    "requirements-lock-python312.txt",
    "environment-reference.json",
    "historical_source_identities.json",
    ".python-version",
    ".gitignore",
    "pasqal_kz_quasistatic_ranking_v3_0_2.py",
    "pasqal_kqs_v302_one_click.py",
    "pasqal_kz_task_ranking_prospective_v2_0_1.py",
    "pasqal_kz_v201_one_click.py",
    "reproduce.py",
    "reproduce.sh",
    "reproduce.ps1",
    "verify_v201_strict_v1.py",
    "verify_v302_strict_v1.py",
    ".github/workflows/external-reproduction.yml",
    "Dockerfile",
    ".dockerignore",
    "tests/test_reproduce.py",
]

REQUIRED_RESULT_FILES = [
    "summary.json",
    "predicted_ranking_frozen_before_heldout.json",
    "candidate_ranking_results.csv",
    "heldout_results.csv",
    "candidate_predictor_audit.json",
    "reference_control.csv",
    "selected_control.csv",
]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def numpy_build_config() -> str:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        np.show_config()
    return stream.getvalue()


def environment_record() -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "blas_lapack": numpy_build_config(),
    }


def finite_numbers(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(finite_numbers(item) for item in value)
    if isinstance(value, dict):
        return all(finite_numbers(item) for item in value.values())
    return True


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def selected_from_ranking(ranking: dict[str, Any]) -> str | None:
    if isinstance(ranking.get("selected_candidate_id"), str):
        return ranking["selected_candidate_id"]
    rows = ranking.get("ranking")
    if isinstance(rows, list) and rows:
        ranked = sorted(rows, key=lambda row: row.get("predicted_rank", 10**9))
        return ranked[0].get("candidate_id")
    return None


def protocol_record(version: str) -> dict[str, Any]:
    manifest_path = ROOT / "manifests" / version / "prospective_protocol.json"
    result_dir = ROOT / "results" / version
    summary_path = result_dir / "summary.json"
    ranking_path = result_dir / "predicted_ranking_frozen_before_heldout.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    protocol_hash = hashlib.sha256(
        canonical_bytes(manifest["protocol"])
    ).hexdigest()
    expected = VERSIONS[version]
    required_files = {
        name: {
            "exists": (result_dir / name).is_file(),
            "size_bytes": (result_dir / name).stat().st_size
            if (result_dir / name).is_file() else 0,
        }
        for name in REQUIRED_RESULT_FILES
    }
    missing_or_empty = [
        name for name, item in required_files.items()
        if not item["exists"] or item["size_bytes"] <= 0
    ]
    ranking_sha = file_sha256(ranking_path)
    selected_summary = summary.get("candidate_audit", {}).get("selected_candidate_id")
    selected_ranking = selected_from_ranking(ranking)
    candidate_rows = read_csv_rows(result_dir / "candidate_ranking_results.csv")
    heldout_csv_rows = read_csv_rows(result_dir / "heldout_results.csv")
    heldout_rows = summary.get("heldout_rows", [])
    comparable = []
    for row in heldout_rows:
        n = int(row["number_ranked_candidates"])
        total_pairs = n * (n - 1) // 2
        comparable_pairs = int(row["comparable_pairs"])
        comparable.append({
            "noise": row.get("gamma_per_us", row.get("sigma_detuning_rad_per_us")),
            "comparable_pairs": comparable_pairs,
            "total_pairs": total_pairs,
            "comparable_pair_fraction": (
                comparable_pairs / total_pairs if total_pairs else None
            ),
        })
    expected_candidate_grid_rows = (
        expected["expected_candidates"] * expected["expected_heldout"]
    )
    csv_counts_ok = (
        len(candidate_rows) == expected_candidate_grid_rows
        and len(heldout_csv_rows) == len(heldout_rows) == expected["expected_heldout"]
    )
    selected_ok = (
        selected_summary == selected_ranking == expected["expected_selected"]
    )
    ranking_hash_ok = (
        ranking_sha == summary.get("ranking_certificate_sha256")
    )
    finite_ok = finite_numbers(summary) and finite_numbers(ranking)
    required_files_ok = not missing_or_empty
    return {
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "summary_path": str(summary_path.relative_to(ROOT)),
        "result_required_files": required_files,
        "missing_or_empty_result_files": missing_or_empty,
        "required_files_ok": required_files_ok,
        "protocol_sha256_field": manifest.get("protocol_sha256"),
        "protocol_sha256_recomputed": protocol_hash,
        "protocol_hash_expected": expected["protocol_sha256"],
        "protocol_hash_ok": (
            manifest.get("protocol_sha256")
            == protocol_hash
            == expected["protocol_sha256"]
        ),
        "manifest_source_sha256": manifest.get("source_sha256"),
        "outcomes_computed_at_commitment": manifest.get("outcomes_computed"),
        "summary_all_gates_pass": summary.get("all_gates_pass"),
        "summary_verdict_expected": expected["summary_all_gates_pass"],
        "summary_verdict_ok": (
            summary.get("all_gates_pass")
            is expected["summary_all_gates_pass"]
        ),
        "ranking_certificate_sha256": summary.get("ranking_certificate_sha256"),
        "ranking_certificate_sha256_recomputed": ranking_sha,
        "ranking_certificate_hash_ok": ranking_hash_ok,
        "selected_candidate_summary": selected_summary,
        "selected_candidate_ranking": selected_ranking,
        "selected_candidate_expected": expected["expected_selected"],
        "selected_candidate_ok": selected_ok,
        "candidate_csv_rows": len(candidate_rows),
        "candidate_csv_rows_expected": expected_candidate_grid_rows,
        "heldout_csv_rows": len(heldout_csv_rows),
        "heldout_csv_rows_expected": expected["expected_heldout"],
        "csv_counts_ok": csv_counts_ok,
        "finite_numeric_values_ok": finite_ok,
        "pairwise_comparable_fractions": comparable,
    }


def artifact_inventory() -> dict[str, str]:
    paths = [ROOT / name for name in BYTE_HASH_FILES]
    paths.extend(sorted((ROOT / "manifests").glob("*/*.json")))
    paths.extend(sorted((ROOT / "results").glob("*/*")))
    return {
        str(path.relative_to(ROOT)): file_sha256(path)
        for path in paths
        if path.is_file()
    }


def artifact_inventory_check(inventory: dict[str, str]) -> dict[str, Any]:
    path = ROOT / "ARTIFACTS.sha256"
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        rows[rel.strip()] = digest
    mismatches = {
        rel: {"recorded": rows.get(rel), "computed": digest}
        for rel, digest in inventory.items()
        if rows.get(rel) != digest
    }
    missing_from_file = sorted(set(inventory) - set(rows))
    stale_entries = sorted(rel for rel in set(rows) - set(inventory) if (ROOT / rel).exists())
    return {
        "path": "ARTIFACTS.sha256",
        "checked_files": len(inventory),
        "mismatches": mismatches,
        "missing_from_artifacts_file": missing_from_file,
        "stale_existing_entries": stale_entries,
        "ok": not mismatches and not missing_from_file and not stale_entries,
    }


def audit() -> dict[str, Any]:
    protocols = {
        version: protocol_record(version)
        for version in sorted(VERSIONS)
    }
    inventory = artifact_inventory()
    artifacts_check = artifact_inventory_check(inventory)
    checks_ok = all(
        item["protocol_hash_ok"]
        and item["summary_verdict_ok"]
        and item["required_files_ok"]
        and item["ranking_certificate_hash_ok"]
        and item["selected_candidate_ok"]
        and item["csv_counts_ok"]
        and item["finite_numeric_values_ok"]
        for item in protocols.values()
    ) and artifacts_check["ok"]
    return {
        "git_commit": git_commit(),
        "environment": environment_record(),
        "file_byte_sha256": inventory,
        "artifact_inventory_check": artifacts_check,
        "protocols": protocols,
        "checks_ok": checks_ok,
        "notes": [
            "File hashes are computed from real repository bytes.",
            "The frozen evaluator scripts are archival; next-version hardening "
            "requirements are tracked in SCIENTIFIC_HARDENING.md.",
            "The public results are CPython 3.9.6 reruns and are not claimed "
            "to be byte-identical to the original CPython 3.12 reference run.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()
    record = audit()
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0 if record["checks_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
