#!/usr/bin/env python3
"""Repository-level audit for frozen artifacts and public rerun outputs.

This checker deliberately uses real file bytes for SHA-256 values. It does not
replace the frozen evaluator scripts; it audits the repository state around
them.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
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
    },
    "v3.0.2": {
        "protocol_sha256": (
            "c9917d5119b520fa17e1e56f1d903403"
            "b3e2d963d5a24e32e3945fbd253ba39e"
        ),
        "summary_all_gates_pass": True,
    },
}

BYTE_HASH_FILES = [
    "README.md",
    "CORRIGENDA.md",
    "REFERENCE_RUNS.md",
    "SCIENTIFIC_HARDENING.md",
    "audit_repository.py",
    "CITATION.cff",
    "LICENSE",
    "requirements.txt",
    ".python-version",
    "pasqal_kz_quasistatic_ranking_v3_0_2.py",
    "pasqal_kqs_v302_one_click.py",
    "pasqal_kz_task_ranking_prospective_v2_0_1.py",
    "pasqal_kz_v201_one_click.py",
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


def protocol_record(version: str) -> dict[str, Any]:
    manifest_path = ROOT / "manifests" / version / "prospective_protocol.json"
    summary_path = ROOT / "results" / version / "summary.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    protocol_hash = hashlib.sha256(
        canonical_bytes(manifest["protocol"])
    ).hexdigest()
    expected = VERSIONS[version]
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
    return {
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "summary_path": str(summary_path.relative_to(ROOT)),
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


def audit() -> dict[str, Any]:
    protocols = {
        version: protocol_record(version)
        for version in sorted(VERSIONS)
    }
    checks_ok = all(
        item["protocol_hash_ok"] and item["summary_verdict_ok"]
        for item in protocols.values()
    )
    return {
        "git_commit": git_commit(),
        "environment": environment_record(),
        "file_byte_sha256": artifact_inventory(),
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
