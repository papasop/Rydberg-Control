#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict external verifier and packager for the v2.0.1 expected negative."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT_NAME = "pasqal_kz_task_ranking_prospective_v2_0_1.py"
VERIFIER_NAME = "verify_v201_strict_v1.py"
EXPECTED_PROTOCOL_HASH = "2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4"
EXPECTED_STATUS = "PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_NOT_SUPPORTED"
EXPECTED_SELECTED = "v00_m_0.030"
EXPECTED_CANDIDATES = 60
EXPECTED_HELDOUT = 4
REQUIRED_OUTPUTS = (
    "summary.json",
    "predicted_ranking_frozen_before_heldout.json",
    "candidate_ranking_results.csv",
    "heldout_results.csv",
    "candidate_predictor_audit.json",
    "reference_control.csv",
    "selected_control.csv",
)
BUNDLE_FILES = (
    "certificate.json",
    "prospective_protocol.json",
    "summary.json",
    "predicted_ranking_frozen_before_heldout.json",
    "candidate_ranking_results.csv",
    "heldout_results.csv",
    "candidate_predictor_audit.json",
    "reference_control.csv",
    "selected_control.csv",
    MAIN_SCRIPT_NAME,
    VERIFIER_NAME,
    "requirements.txt",
    "requirements-lock-python312.txt",
    "environment.json",
    "README_REPRODUCTION.md",
    "provenance.json",
)


class VerificationError(RuntimeError):
    pass


class UnexpectedScientificResult(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "algorithm": "sha256-file-bytes-v1",
        "sha256": sha256_bytes(resolved),
        "path_basename": resolved.name,
        "size_bytes": resolved.stat().st_size,
    }


def canonical_json_hash(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def import_version(name: str) -> str | None:
    try:
        module = __import__(name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "unknown"))


def blas_lapack_info() -> dict[str, Any]:
    try:
        import contextlib
        import io
        import numpy as np

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            np.__config__.show()
        return {"numpy_config_show": buf.getvalue()}
    except Exception as exc:
        return {"error": repr(exc)}


def environment(strict: bool, main_script: Path, verifier: Path) -> dict[str, Any]:
    scipy_version = import_version("scipy")
    env = {
        "utc": utc_now(),
        "platform": platform.platform(),
        "os": platform.system(),
        "machine": platform.machine(),
        "python": {
            "implementation": platform.python_implementation(),
            "version": sys.version,
            "version_info": list(sys.version_info[:5]),
            "executable": sys.executable,
        },
        "packages": {
            "numpy": import_version("numpy"),
            "scipy": scipy_version,
        },
        "blas_lapack": blas_lapack_info(),
        "protocol_sha256": EXPECTED_PROTOCOL_HASH,
        "source_identity": file_identity(main_script),
        "verifier_identity": {
            "verifier_name": VERIFIER_NAME,
            "verifier_hash_algorithm": "sha256-file-bytes-v1",
            "verifier_sha256": sha256_bytes(verifier),
        },
        "warnings": [],
        "strict_environment": strict,
    }
    if scipy_version is None:
        raise VerificationError("SciPy version is missing; environment recording is incomplete.")
    py = env["python"]
    if py["implementation"] != "CPython" or py["version_info"][:2] != [3, 12]:
        env["warnings"].append("STRICT_BYTE_IDENTITY_NOT_EXPECTED")
        if strict:
            raise SystemExit(3)
    if env["packages"]["numpy"] != "2.0.2" or env["packages"]["scipy"] != "1.13.1":
        env["warnings"].append("STRICT_REFERENCE_DEPENDENCY_VERSIONS_NOT_MATCHED")
        if strict:
            raise SystemExit(3)
    return env


def ensure_inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise VerificationError(f"Path escapes expected root: {resolved}")
    return resolved


def reject_symlink_escape(root: Path) -> None:
    root_resolved = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            target = path.resolve()
            if not target.is_relative_to(root_resolved):
                raise VerificationError(f"Symlink escapes result directory: {path} -> {target}")


def unique_run_dir(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(100):
        candidate = output_root / "v201" / f"{stamp}_{secrets.token_hex(4)}"
        try:
            candidate.mkdir(parents=True)
            return candidate.resolve()
        except FileExistsError:
            continue
    raise VerificationError("Could not create a unique v201 run directory.")


def log(log_fh: Any, message: str) -> None:
    log_fh.write(f"[{utc_now()}] {message}\n")
    log_fh.flush()


def run_stage(args: list[str], log_fh: Any) -> dict[str, Any]:
    log(log_fh, "RUN " + " ".join(args))
    started = time.monotonic()
    proc = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        shell=False,
        check=False,
        text=True,
        capture_output=True,
    )
    elapsed = time.monotonic() - started
    log(log_fh, f"RETURN_CODE {proc.returncode} WALL_SECONDS {elapsed:.3f}")
    if proc.stdout:
        log_fh.write("--- stdout ---\n" + proc.stdout + ("" if proc.stdout.endswith("\n") else "\n"))
    if proc.stderr:
        log_fh.write("--- stderr ---\n" + proc.stderr + ("" if proc.stderr.endswith("\n") else "\n"))
    log_fh.flush()
    return {
        "args": args,
        "returncode": proc.returncode,
        "wall_seconds": elapsed,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def finite_numbers(obj: Any) -> bool:
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return True
    if isinstance(obj, int):
        return True
    if isinstance(obj, float):
        return math.isfinite(obj)
    if isinstance(obj, list):
        return all(finite_numbers(item) for item in obj)
    if isinstance(obj, dict):
        return all(finite_numbers(value) for value in obj.values())
    return True


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def selected_from_ranking(ranking: dict[str, Any]) -> str | None:
    if isinstance(ranking.get("selected_candidate_id"), str):
        return ranking["selected_candidate_id"]
    rows = ranking.get("ranking")
    if isinstance(rows, list) and rows:
        ranked = sorted(rows, key=lambda row: row.get("predicted_rank", 10**9))
        return ranked[0].get("candidate_id")
    return None


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise VerificationError(f"Missing manifest: {manifest_path}")
    manifest = read_json(manifest_path)
    recomputed = canonical_json_hash(manifest.get("protocol"))
    if manifest.get("protocol_sha256") != EXPECTED_PROTOCOL_HASH:
        raise VerificationError("Manifest protocol hash mismatch.")
    if recomputed != EXPECTED_PROTOCOL_HASH:
        raise VerificationError("Canonical protocol hash mismatch.")
    if manifest.get("outcomes_computed") is not False:
        raise VerificationError("Manifest outcomes_computed is not false.")
    return {
        "manifest_protocol_hash": manifest.get("protocol_sha256"),
        "canonical_protocol_sha256_recomputed": recomputed,
        "historical_manifest_source_hash": manifest.get("source_sha256"),
        "historical_source_identity_status": "HISTORICAL_SOURCE_IDENTITY_REPORTED_NOT_REESTABLISHED",
    }


def validate_results(eval_dir: Path, manifest_path: Path) -> dict[str, Any]:
    eval_dir = eval_dir.resolve()
    reject_symlink_escape(eval_dir)
    for name in REQUIRED_OUTPUTS:
        path = ensure_inside(eval_dir / name, eval_dir)
        if not path.is_file() or path.stat().st_size <= 0:
            raise VerificationError(f"Required artifact missing or empty: {name}")

    summary_path = eval_dir / "summary.json"
    ranking_path = eval_dir / "predicted_ranking_frozen_before_heldout.json"
    summary = read_json(summary_path)
    ranking = read_json(ranking_path)
    if not finite_numbers(summary) or not finite_numbers(ranking):
        raise VerificationError("NaN/Inf found in summary or ranking certificate.")

    manifest_check = validate_manifest(manifest_path)
    if summary.get("protocol_sha256") != EXPECTED_PROTOCOL_HASH:
        raise VerificationError("Summary protocol hash mismatch.")

    ranking_sha = sha256_bytes(ranking_path)
    recorded_ranking_sha = summary.get("ranking_certificate_sha256")
    if ranking_sha != recorded_ranking_sha:
        raise VerificationError("RANKING_CERTIFICATE_HASH_MISMATCH")

    summary_selected = summary.get("candidate_audit", {}).get("selected_candidate_id")
    ranking_selected = selected_from_ranking(ranking)
    if summary_selected != ranking_selected:
        raise VerificationError("Selected candidate differs between summary and ranking certificate.")
    if summary_selected != EXPECTED_SELECTED:
        raise UnexpectedScientificResult("Selected candidate differs from expected v2.0.1 negative.")

    heldout = summary.get("heldout_rows", [])
    audit = summary.get("candidate_audit", {})
    gates = summary.get("gates", {})
    if audit.get("valid") != EXPECTED_CANDIDATES:
        raise VerificationError("Unexpected valid candidate count.")
    if len(heldout) != EXPECTED_HELDOUT:
        raise VerificationError("Unexpected held-out grid count.")
    if len(csv_rows(eval_dir / "heldout_results.csv")) != len(heldout):
        raise VerificationError("Held-out CSV row count does not match summary.")
    if len(csv_rows(eval_dir / "candidate_ranking_results.csv")) != EXPECTED_CANDIDATES * EXPECTED_HELDOUT:
        raise VerificationError("Candidate CSV row count does not match summary grid.")

    ranking_gates = [
        "spearman_ranking_each_gamma",
        "kendall_ranking_each_gamma",
        "pairwise_ordering_each_gamma",
        "top_k_recovery_each_gamma",
    ]
    if any(gates.get(name) is not True for name in ranking_gates):
        raise VerificationError("Unexpected ranking gate failure.")
    expected_false = ["predicted_improvement_predeclared_minimum", "minimum_relative_improvement_each_gamma"]
    if any(gates.get(name) is not False for name in expected_false):
        raise UnexpectedScientificResult("Expected effect-size gates did not fail.")
    if summary.get("all_gates_pass") is not False or summary.get("scientific_status") != EXPECTED_STATUS:
        raise UnexpectedScientificResult("Scientific status does not match expected negative.")

    predicted = audit.get("predicted_relative_improvement")
    heldout_effects = [row.get("relative_improvement") for row in heldout]
    if not isinstance(predicted, (float, int)) or not 0.0045 <= float(predicted) <= 0.0051:
        raise UnexpectedScientificResult("Predicted improvement is outside expected 0.484% range.")
    if not all(isinstance(x, (float, int)) and 0.0045 <= float(x) <= 0.0051 for x in heldout_effects):
        raise UnexpectedScientificResult("Held-out improvements are outside expected 0.482% range.")

    return {
        **manifest_check,
        "ranking_sha256_recorded_in_summary": recorded_ranking_sha,
        "ranking_sha256_recomputed": ranking_sha,
        "ranking_hash_match": True,
        "summary_selected_candidate_id": summary_selected,
        "ranking_selected_candidate_id": ranking_selected,
        "selected_candidate_match": True,
        "execution_success": True,
        "expected_scientific_outcome_reproduced": True,
        "scientific_result": "NEGATIVE",
        "wrapper_status": "REPRODUCED_EXPECTED_NEGATIVE",
        "scientific_status": summary.get("scientific_status"),
        "all_gates_pass": summary.get("all_gates_pass"),
        "predicted_relative_improvement": predicted,
        "heldout_relative_improvements": heldout_effects,
        "candidate_csv_rows": EXPECTED_CANDIDATES * EXPECTED_HELDOUT,
        "heldout_csv_rows": EXPECTED_HELDOUT,
    }


def write_checksums(directory: Path) -> None:
    checksum_path = directory / "artifact_checksums.sha256"
    lines: list[str] = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        if path == checksum_path:
            continue
        lines.append(f"{sha256_bytes(path)}  {path.relative_to(directory).as_posix()}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_required(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise VerificationError(f"Cannot bundle missing file: {src}")
    if src.is_symlink():
        raise VerificationError(f"Refusing to bundle symlink: {src}")
    shutil.copy2(src, dst)


def make_readme(path: Path) -> None:
    path.write_text(
        "# v2.0.1 Strict External Reproduction Bundle\n\n"
        "This bundle is self-contained for auditing the v2.0.1 expected negative. "
        "The verifier is self-identifying via file-byte SHA-256, but this is not "
        "third-party timestamping or certification.\n\n"
        "Expected result: `REPRODUCED_EXPECTED_NEGATIVE`. The v2.0.1 ranking gates "
        "pass, while the predeclared practical-effect gates fail.\n",
        encoding="utf-8",
    )


def package_bundle(
    run_dir: Path,
    manifest_path: Path,
    eval_dir: Path,
    certificate: dict[str, Any],
    env: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    staging = run_dir / "bundle_v201"
    if staging.exists():
        raise VerificationError(f"Bundle staging already exists: {staging}")
    staging.mkdir()
    write_json(staging / "certificate.json", certificate)
    write_json(staging / "environment.json", env)
    write_json(staging / "provenance.json", provenance)
    copy_required(manifest_path, staging / "prospective_protocol.json")
    for name in REQUIRED_OUTPUTS:
        copy_required(eval_dir / name, staging / name)
    for name in (MAIN_SCRIPT_NAME, VERIFIER_NAME, "requirements.txt", "requirements-lock-python312.txt"):
        copy_required(REPO_ROOT / name, staging / name)
    make_readme(staging / "README_REPRODUCTION.md")
    write_checksums(staging)

    missing = [name for name in BUNDLE_FILES + ("artifact_checksums.sha256",) if not (staging / name).is_file()]
    if missing:
        raise VerificationError("Bundle staging is incomplete: " + ", ".join(missing))

    zip_base = run_dir / f"v201_external_reproduction_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(4)}"
    zip_path = zip_base.with_suffix(".zip")
    if zip_path.exists():
        raise VerificationError(f"ZIP already exists: {zip_path}")
    created = Path(shutil.make_archive(str(zip_base), "zip", root_dir=staging))
    bundle_info = {
        "bundle_dir": str(staging),
        "zip_path": str(created),
        "bundle_sha256": sha256_bytes(created),
    }
    certificate["bundle"] = bundle_info
    write_json(staging / "certificate.json", certificate)
    write_checksums(staging)
    return bundle_info


def fresh_reproduction(args: argparse.Namespace, run_dir: Path, env: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    main_script = (REPO_ROOT / MAIN_SCRIPT_NAME).resolve()
    verifier = (REPO_ROOT / VERIFIER_NAME).resolve()
    expected_source_hash = sha256_bytes(main_script)
    log_path = run_dir / "verify_v201_strict_v1.log"
    commit_dir = run_dir / "commitment"
    eval_dir = run_dir / "evaluation"
    with log_path.open("w", encoding="utf-8") as log_fh:
        commit = run_stage([sys.executable, str(main_script), "--outdir", str(commit_dir)], log_fh)
        if commit["returncode"] not in (0,):
            raise VerificationError("Commit stage failed.")
        if sha256_bytes(main_script) != expected_source_hash:
            raise VerificationError("Fresh reproduction source changed between initial read and commitment.")
        manifest_path = commit_dir / "prospective_protocol.json"
        manifest_check = validate_manifest(manifest_path)
        evaluate = run_stage(
            [
                sys.executable,
                str(main_script),
                "--evaluate",
                "--expected-hash",
                EXPECTED_PROTOCOL_HASH,
                "--manifest",
                str(manifest_path),
                "--outdir",
                str(eval_dir),
            ],
            log_fh,
        )
        if evaluate["returncode"] == 2:
            raise VerificationError("Evaluate stage returned endpoint/execution failure code 2.")
        if sha256_bytes(main_script) != expected_source_hash:
            raise VerificationError("Fresh reproduction source changed between commitment and evaluation.")
        validation = validate_results(eval_dir, manifest_path)
        validation["source_identity"] = {
            "algorithm": "sha256-file-bytes-v1",
            "manifest_source_hash_equals_current_source_hash": True,
            "current_source_hash_equals_expected_source_hash": True,
            "expected_source_hash": expected_source_hash,
            "current_source_hash": sha256_bytes(main_script),
            "historical_manifest_source_hash": manifest_check["historical_manifest_source_hash"],
            "historical_source_identity_status": "HISTORICAL_SOURCE_IDENTITY_REPORTED_NOT_REESTABLISHED",
        }
        validation["subprocess"] = {"commit": commit, "evaluate": evaluate}
        provenance = {
            "mode": "fresh_reproduction",
            "run_dir": str(run_dir),
            "commit_dir": str(commit_dir),
            "evaluation_dir": str(eval_dir),
            "manifest_path": str(manifest_path),
            "log_path": str(log_path),
            "main_script": str(main_script),
            "source_identity": env["source_identity"],
            "verifier_identity": env["verifier_identity"],
        }
    return validation, provenance


def reuse_existing(args: argparse.Namespace, run_dir: Path, env: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    eval_dir = Path(args.reuse_existing).expanduser().resolve()
    if not eval_dir.is_dir():
        raise VerificationError(f"--reuse-existing is not a directory: {eval_dir}")
    if args.manifest:
        manifest_path = Path(args.manifest).expanduser().resolve()
    else:
        manifest_path = (eval_dir.parent / "commitment" / "prospective_protocol.json").resolve()
    validation = validate_results(eval_dir, manifest_path)
    provenance = {
        "mode": "reuse_existing",
        "run_dir": str(run_dir),
        "evaluation_dir": str(eval_dir),
        "manifest_path": str(manifest_path),
        "source_identity": env["source_identity"],
        "verifier_identity": env["verifier_identity"],
    }
    return validation, provenance


def historical_audit(args: argparse.Namespace, env: dict[str, Any]) -> int:
    path = Path(args.historical_manifest or "manifests/v2.0.1/prospective_protocol.json")
    manifest = read_json((REPO_ROOT / path).resolve() if not path.is_absolute() else path)
    report = {
        "mode": "historical_audit",
        "protocol_sha256": manifest.get("protocol_sha256"),
        "historical_manifest_source_hash": manifest.get("source_sha256"),
        "current_file_source_identity": env["source_identity"],
        "status": "HISTORICAL_SOURCE_IDENTITY_REPORTED_NOT_REESTABLISHED",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="external_runs", help="Root for fresh v201 reproduction runs.")
    parser.add_argument("--strict-environment", action="store_true", help="Require CPython 3.12 and locked dependencies.")
    parser.add_argument("--reuse-existing", default=None, help="Verified package of an existing evaluation directory.")
    parser.add_argument("--manifest", default=None, help="Manifest path for --reuse-existing.")
    parser.add_argument("--historical-audit", action="store_true", help="Report historical manifest source identity only.")
    parser.add_argument("--historical-manifest", default=None, help="Manifest for --historical-audit.")
    args = parser.parse_args()

    main_script = (REPO_ROOT / MAIN_SCRIPT_NAME).resolve()
    verifier = (REPO_ROOT / VERIFIER_NAME).resolve()
    try:
        env = environment(args.strict_environment, main_script, verifier)
        if args.historical_audit:
            return historical_audit(args, env)
        output_root = Path(args.output_root)
        if not output_root.is_absolute():
            output_root = REPO_ROOT / output_root
        run_dir = unique_run_dir(output_root.resolve())
        write_json(run_dir / "environment.json", env)
        if args.reuse_existing:
            validation, provenance = reuse_existing(args, run_dir, env)
        else:
            validation, provenance = fresh_reproduction(args, run_dir, env)
        certificate = {
            **validation,
            "execution_success": True,
            "expected_scientific_outcome_reproduced": True,
            "scientific_result": "NEGATIVE",
            "wrapper_status": "REPRODUCED_EXPECTED_NEGATIVE",
            "verifier_name": VERIFIER_NAME,
            "verifier_hash_algorithm": "sha256-file-bytes-v1",
            "verifier_sha256": env["verifier_identity"]["verifier_sha256"],
            "created_utc": utc_now(),
        }
        write_json(run_dir / "provenance.json", provenance)
        write_json(run_dir / "certificate.json", certificate)
        bundle = package_bundle(
            run_dir,
            Path(provenance["manifest_path"]),
            Path(provenance["evaluation_dir"]),
            certificate,
            env,
            provenance,
        )
        write_json(run_dir / "certificate.json", {**certificate, "bundle": bundle})
        try:
            from google.colab import files

            files.download(str(bundle["zip_path"]))
        except Exception as exc:
            print(f"Bundle created at {bundle['zip_path']}; automatic download unavailable: {exc}")
        print(json.dumps({**certificate, "bundle": bundle}, indent=2, sort_keys=True))
        return 0
    except SystemExit as exc:
        return int(exc.code)
    except UnexpectedScientificResult as exc:
        print(f"UNEXPECTED_SCIENTIFIC_RESULT: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"EXECUTION_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
