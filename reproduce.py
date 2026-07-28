#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""External one-command reproduction wrapper for the frozen Rydberg-control runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = "external_runs"
RECOMMENDED_PYTHON = (3, 12)


@dataclass(frozen=True)
class ProtocolConfig:
    key: str
    version: str
    script: str
    expected_protocol_hash: str
    expected_status: str
    expected_candidates: int
    expected_heldout_points: int
    expected_selected: str
    expected_execution_status: str
    expected_all_gates_pass: bool
    expected_predicted_effect_range: tuple[float, float]
    expected_heldout_effect_range: tuple[float, float]


PROTOCOLS: dict[str, ProtocolConfig] = {
    "v2": ProtocolConfig(
        key="v2",
        version="v2.0.1",
        script="pasqal_kz_task_ranking_prospective_v2_0_1.py",
        expected_protocol_hash="2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4",
        expected_status="PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_NOT_SUPPORTED",
        expected_candidates=60,
        expected_heldout_points=4,
        expected_selected="v00_m_0.030",
        expected_execution_status="REPRODUCED_EXPECTED_NEGATIVE",
        expected_all_gates_pass=False,
        expected_predicted_effect_range=(0.0045, 0.0051),
        expected_heldout_effect_range=(0.0045, 0.0051),
    ),
    "v3": ProtocolConfig(
        key="v3",
        version="v3.0.2",
        script="pasqal_kz_quasistatic_ranking_v3_0_2.py",
        expected_protocol_hash="c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e",
        expected_status="PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_SUPPORTED",
        expected_candidates=80,
        expected_heldout_points=4,
        expected_selected="v01_m_0.150",
        expected_execution_status="REPRODUCED_EXPECTED_PASS",
        expected_all_gates_pass=True,
        expected_predicted_effect_range=(0.20, 0.21),
        expected_heldout_effect_range=(0.20, 0.21),
    ),
}


CORE_OUTPUTS = (
    "summary.json",
    "candidate_predictor_audit.json",
    "candidate_ranking_results.csv",
    "heldout_results.csv",
    "predicted_ranking_frozen_before_heldout.json",
    "reference_control.csv",
    "selected_control.csv",
)

STRICT_VERIFIERS = {
    "v2": "verify_v201_strict_v1.py",
    "v3": "verify_v302_strict_v1.py",
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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def import_version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "unknown"))


def blas_lapack_info() -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        import numpy as np

        config = getattr(np, "__config__", None)
        if config and hasattr(config, "show"):
            import io
            import contextlib

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                config.show()
            info["numpy_config_show"] = buf.getvalue()
        if config and hasattr(config, "CONFIG"):
            info["numpy_config"] = getattr(config, "CONFIG")
    except Exception as exc:
        info["error"] = repr(exc)
    return info


def collect_environment() -> dict[str, Any]:
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "platform": platform.platform(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "version_info": list(sys.version_info[:5]),
            "implementation": platform.python_implementation(),
        },
        "packages": {
            "numpy": import_version("numpy"),
            "scipy": import_version("scipy"),
        },
        "blas_lapack": blas_lapack_info(),
}


def git_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def environment_warnings(env: dict[str, Any], strict: bool) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    py = env["python"]
    version = py["version_info"]
    if py["implementation"] != "CPython":
        errors.append("CPython is required for strict reproduction.")
    if version[:2] != list(RECOMMENDED_PYTHON):
        msg = (
            "CPython 3.12 is recommended; non-3.12 runs can reproduce numerical verdicts "
            "but strict source/ranking byte identity is not guaranteed."
        )
        if strict:
            errors.append(msg)
        else:
            warnings.append(msg)
    for package in ("numpy", "scipy"):
        if not env["packages"].get(package):
            errors.append(f"{package} is not importable.")
    return warnings, errors


def preflight_checks(output_root: Path, strict: bool) -> dict[str, Any]:
    env = collect_environment()
    warnings, errors = environment_warnings(env, strict)
    scripts = {
        cfg.key: {
            "path": str((REPO_ROOT / cfg.script).relative_to(REPO_ROOT)),
            "exists": (REPO_ROOT / cfg.script).is_file(),
            "sha256": file_sha256(REPO_ROOT / cfg.script) if (REPO_ROOT / cfg.script).is_file() else None,
        }
        for cfg in PROTOCOLS.values()
    }
    for key, item in scripts.items():
        if not item["exists"]:
            errors.append(f"Missing frozen script for {key}: {item['path']}")
    req = REPO_ROOT / "requirements.txt"
    if not req.is_file():
        errors.append("requirements.txt is missing.")
    output_root.mkdir(parents=True, exist_ok=True)
    probe = output_root / f".write_probe_{secrets.token_hex(4)}"
    try:
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        writable = True
    except Exception as exc:
        writable = False
        errors.append(f"Output root is not writable: {exc}")
    return {
        "environment": env,
        "strict_environment": strict,
        "recommended_python": "CPython 3.12.x",
        "requirements_txt": {"path": str(req.relative_to(REPO_ROOT)), "exists": req.is_file()},
        "scripts": scripts,
        "output_root": str(output_root),
        "output_root_writable": writable,
        "warnings": warnings,
        "errors": errors,
        "ok": not errors,
    }


def print_preflight(report: dict[str, Any]) -> None:
    env = report["environment"]
    print("External reproduction preflight")
    print(f"OS: {env['platform']}")
    print(f"Python: {env['python']['version']}")
    print(f"Implementation: {env['python']['implementation']}")
    print(f"Executable: {env['python']['executable']}")
    print(f"NumPy: {env['packages']['numpy']}")
    print(f"SciPy: {env['packages']['scipy']}")
    print(f"Git commit: {env['git_commit']}")
    for key, cfg in PROTOCOLS.items():
        script_sha = report["scripts"].get(key, {}).get("sha256")
        print(f"{key} protocol SHA: {cfg.expected_protocol_hash}")
        print(f"{key} source SHA(file bytes): {script_sha}")
    print("BLAS/LAPACK: recorded in preflight JSON/environment.json")
    print(f"requirements.txt: {'present' if report['requirements_txt']['exists'] else 'missing'}")
    print(f"Output root writable: {report['output_root_writable']} ({report['output_root']})")
    for key, script in report["scripts"].items():
        print(f"{key} script: {'present' if script['exists'] else 'missing'} ({script['path']})")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in report["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)


def unique_run_dir(
    output_root: Path,
    now: Callable[[], datetime] | None = None,
    short_id_fn: Callable[[], str] | None = None,
) -> Path:
    now = now or (lambda: datetime.now(timezone.utc))
    short_id_fn = short_id_fn or (lambda: secrets.token_hex(4))
    output_root.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        stamp = now().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        candidate = output_root / f"{stamp}_{short_id_fn()}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError("Could not create a unique external run directory.")


def build_commit_command(cfg: ProtocolConfig, outdir: Path) -> list[str]:
    return [sys.executable, cfg.script, "--outdir", str(outdir)]


def build_evaluate_command(cfg: ProtocolConfig, protocol_hash: str, manifest: Path, outdir: Path) -> list[str]:
    return [
        sys.executable,
        cfg.script,
        "--evaluate",
        "--expected-hash",
        protocol_hash,
        "--manifest",
        str(manifest),
        "--outdir",
        str(outdir),
    ]


def log_line(log_fh: Any, message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    log_fh.write(f"[{stamp}] {message}\n")
    log_fh.flush()


def run_subprocess(args: list[str], log_fh: Any, timeout_seconds: int | None = None) -> dict[str, Any]:
    started = time.monotonic()
    log_line(log_fh, "RUN " + " ".join(args))
    try:
        proc = subprocess.run(
            args,
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        log_line(log_fh, f"TIMEOUT WALL_SECONDS {elapsed:.3f}")
        return {
            "args": args,
            "returncode": 124,
            "wall_seconds": elapsed,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timeout_seconds": timeout_seconds,
        }
    elapsed = time.monotonic() - started
    log_line(log_fh, f"RETURN_CODE {proc.returncode} WALL_SECONDS {elapsed:.3f}")
    if proc.stdout:
        log_fh.write("--- stdout ---\n")
        log_fh.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            log_fh.write("\n")
    if proc.stderr:
        log_fh.write("--- stderr ---\n")
        log_fh.write(proc.stderr)
        if not proc.stderr.endswith("\n"):
            log_fh.write("\n")
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


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
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


def validate_protocol_manifest(manifest_path: Path, expected_hash: str) -> tuple[bool, list[str], dict[str, Any]]:
    warnings: list[str] = []
    details: dict[str, Any] = {"manifest": str(manifest_path)}
    if not manifest_path.is_file():
        return False, [f"Manifest missing: {manifest_path}"], details
    try:
        manifest = read_json(manifest_path)
    except Exception as exc:
        return False, [f"Manifest is not parseable JSON: {exc}"], details
    details["outcomes_computed"] = manifest.get("outcomes_computed")
    details["protocol_sha256"] = manifest.get("protocol_sha256")
    recomputed = canonical_json_hash(manifest.get("protocol"))
    details["recomputed_protocol_sha256"] = recomputed
    ok = True
    if manifest.get("outcomes_computed") is not False:
        ok = False
        warnings.append("Manifest outcomes_computed is not false.")
    if manifest.get("protocol_sha256") != expected_hash or recomputed != expected_hash:
        ok = False
        warnings.append("Protocol hash mismatch against canonical protocol content.")
    return ok, warnings, details


def classify_summary(cfg: ProtocolConfig, summary: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    warnings: list[str] = []
    gates = summary.get("gates", {})
    audit = summary.get("candidate_audit", {})
    rows = summary.get("heldout_rows", [])
    selected = audit.get("selected_candidate_id")
    predicted_effect = audit.get("predicted_relative_improvement")
    heldout_effects = [row.get("relative_improvement") for row in rows if isinstance(row, dict)]
    protocol_match = summary.get("protocol_sha256") == cfg.expected_protocol_hash
    numerical = True

    checks = {
        "protocol_hash_match": protocol_match,
        "all_gates_pass_expected": summary.get("all_gates_pass") == cfg.expected_all_gates_pass,
        "scientific_status_expected": summary.get("scientific_status") == cfg.expected_status,
        "candidate_count_expected": audit.get("valid") == cfg.expected_candidates,
        "heldout_count_expected": len(rows) == cfg.expected_heldout_points,
        "selected_expected": selected == cfg.expected_selected,
        "finite_numerics": finite_numbers(summary),
    }
    for name, ok in checks.items():
        if not ok:
            numerical = False
            warnings.append(f"Summary check failed: {name}")

    if selected != cfg.expected_selected:
        warnings.append(f"Selected candidate differs from expected: {selected} != {cfg.expected_selected}")

    lo, hi = cfg.expected_predicted_effect_range
    if not isinstance(predicted_effect, (int, float)) or not lo <= float(predicted_effect) <= hi:
        numerical = False
        warnings.append("Predicted effect size is outside the expected README range.")
    hlo, hhi = cfg.expected_heldout_effect_range
    if len(heldout_effects) != cfg.expected_heldout_points or not all(
        isinstance(x, (int, float)) and hlo <= float(x) <= hhi for x in heldout_effects
    ):
        numerical = False
        warnings.append("Held-out effect sizes are outside the expected README range.")

    if cfg.key == "v2":
        rank_gates = [
            "spearman_ranking_each_gamma",
            "kendall_ranking_each_gamma",
            "pairwise_ordering_each_gamma",
            "top_k_recovery_each_gamma",
        ]
        if any(gates.get(name) is not True for name in rank_gates):
            numerical = False
            warnings.append("v2 ranking gates did not all pass.")
        expected_false = ["predicted_improvement_predeclared_minimum", "minimum_relative_improvement_each_gamma"]
        if any(gates.get(name) is not False for name in expected_false):
            numerical = False
            warnings.append("v2 expected effect-size gates did not fail as predeclared.")

    status = cfg.expected_execution_status if numerical else "REPRODUCTION_ERROR"
    return status, warnings, {
        "protocol_hash_match": protocol_match,
        "numerical_reproduction": numerical,
        "summary_checks": checks,
        "selected_candidate_id": selected,
        "predicted_relative_improvement": predicted_effect,
        "heldout_relative_improvements": heldout_effects,
    }


def validate_evaluation(cfg: ProtocolConfig, commitment_dir: Path, evaluation_dir: Path) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    manifest_path = commitment_dir / "prospective_protocol.json"
    manifest_ok, manifest_warnings, manifest_details = validate_protocol_manifest(
        manifest_path, cfg.expected_protocol_hash
    )
    if not manifest_ok:
        errors.extend(manifest_warnings)
    else:
        warnings.extend(manifest_warnings)

    file_checks: dict[str, Any] = {}
    for rel in CORE_OUTPUTS:
        path = evaluation_dir / rel
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        file_checks[rel] = {"exists": exists, "size_bytes": size}
        if not exists:
            errors.append(f"Missing output: {cfg.key}/{rel}")
        elif size <= 0:
            errors.append(f"Empty output: {cfg.key}/{rel}")

    summary_path = evaluation_dir / "summary.json"
    ranking_path = evaluation_dir / "predicted_ranking_frozen_before_heldout.json"
    if not summary_path.is_file():
        return {
            "execution_status": "REPRODUCTION_ERROR",
            "scientific_status": "ERROR",
            "protocol_hash_match": False,
            "strict_source_identity_match": False,
            "numerical_reproduction": False,
            "warnings": warnings + errors,
            "manifest": manifest_details,
            "file_checks": file_checks,
        }
    try:
        summary = read_json(summary_path)
    except Exception as exc:
        errors.append(f"summary.json is not parseable: {exc}")
        summary = {}

    ranking: dict[str, Any] = {}
    if ranking_path.is_file():
        try:
            ranking = read_json(ranking_path)
        except Exception as exc:
            errors.append(f"ranking certificate is not parseable: {exc}")

    if (evaluation_dir / "candidate_ranking_results.csv").is_file():
        expected_rows = cfg.expected_candidates * cfg.expected_heldout_points
        actual_rows = count_csv_rows(evaluation_dir / "candidate_ranking_results.csv")
        file_checks["candidate_csv_rows"] = {"actual": actual_rows, "expected": expected_rows}
        if actual_rows != expected_rows:
            errors.append("Candidate CSV row count does not match expected candidate-by-heldout grid count.")
    if (evaluation_dir / "heldout_results.csv").is_file():
        actual_heldout = count_csv_rows(evaluation_dir / "heldout_results.csv")
        file_checks["heldout_csv_rows"] = {"actual": actual_heldout, "expected": cfg.expected_heldout_points}
        if actual_heldout != cfg.expected_heldout_points:
            errors.append("Held-out CSV row count does not match expected grid count.")

    cert_path = evaluation_dir / "predicted_ranking_frozen_before_heldout.json"
    heldout_path = evaluation_dir / "heldout_results.csv"
    if cert_path.is_file() and heldout_path.is_file():
        file_checks["ranking_before_heldout_by_mtime"] = cert_path.stat().st_mtime <= heldout_path.stat().st_mtime
        if not file_checks["ranking_before_heldout_by_mtime"]:
            errors.append("Ranking certificate mtime is after held-out results.")

    if ranking_path.is_file() and summary:
        ranking_sha = file_sha256(ranking_path)
        recorded_sha = summary.get("ranking_certificate_sha256")
        file_checks["ranking_sha256_recorded_in_summary"] = recorded_sha
        file_checks["ranking_sha256_recomputed"] = ranking_sha
        file_checks["ranking_hash_match"] = ranking_sha == recorded_sha
        if ranking_sha != recorded_sha:
            errors.append("RANKING_CERTIFICATE_HASH_MISMATCH")
        summary_selected = summary.get("candidate_audit", {}).get("selected_candidate_id")
        ranking_selected = selected_from_ranking(ranking)
        file_checks["selected_candidate_summary"] = summary_selected
        file_checks["selected_candidate_ranking"] = ranking_selected
        file_checks["selected_candidate_match"] = summary_selected == ranking_selected == cfg.expected_selected
        if summary_selected != ranking_selected or summary_selected != cfg.expected_selected:
            errors.append("Selected candidate mismatch across summary, ranking certificate, or expectation.")
    if summary and ranking and (not finite_numbers(summary) or not finite_numbers(ranking)):
        errors.append("NaN/Inf found in summary or ranking certificate.")

    summary_status, summary_warnings, details = classify_summary(cfg, summary)
    warnings.extend(summary_warnings)
    if errors:
        execution_status = "REPRODUCTION_ERROR"
    else:
        execution_status = summary_status

    return {
        "execution_status": execution_status,
        "scientific_status": summary.get("scientific_status", "ERROR"),
        "protocol_hash_match": bool(details.get("protocol_hash_match")) and manifest_ok,
        "strict_source_identity_match": False,
        "numerical_reproduction": execution_status != "REPRODUCTION_ERROR" and bool(details.get("numerical_reproduction")),
        "warnings": warnings + errors,
        "manifest": manifest_details,
        "file_checks": file_checks,
        "details": details,
    }


def run_protocol(cfg: ProtocolConfig, run_dir: Path, log_fh: Any, timeout_seconds: int) -> dict[str, Any]:
    protocol_dir = run_dir / cfg.key
    commitment_dir = protocol_dir / "commitment"
    evaluation_dir = protocol_dir / "evaluation"
    protocol_dir.mkdir(parents=True)
    log_line(log_fh, f"START protocol {cfg.key} ({cfg.version})")
    source_path = REPO_ROOT / cfg.script
    source_before = file_sha256(source_path)
    commit_result = run_subprocess(build_commit_command(cfg, commitment_dir), log_fh, timeout_seconds)
    source_after_commit = file_sha256(source_path)
    manifest_path = commitment_dir / "prospective_protocol.json"
    protocol_hash = None
    if manifest_path.is_file():
        try:
            protocol_hash = read_json(manifest_path).get("protocol_sha256")
        except Exception:
            protocol_hash = None
    if not protocol_hash:
        protocol_hash = cfg.expected_protocol_hash
    evaluate_result = run_subprocess(
        build_evaluate_command(cfg, protocol_hash, manifest_path, evaluation_dir),
        log_fh,
        timeout_seconds,
    )
    source_after_evaluate = file_sha256(source_path)
    validation = validate_evaluation(cfg, commitment_dir, evaluation_dir)
    validation["subprocess"] = {"commit": commit_result, "evaluate": evaluate_result}
    validation["source_identity"] = {
        "algorithm": "sha256-file-bytes-v1",
        "source_before_commit": source_before,
        "source_after_commit": source_after_commit,
        "source_after_evaluate": source_after_evaluate,
        "fresh_freeze_evaluate_source_bytes_match": (
            source_before == source_after_commit == source_after_evaluate
        ),
    }
    if not validation["source_identity"]["fresh_freeze_evaluate_source_bytes_match"]:
        validation["execution_status"] = "REPRODUCTION_ERROR"
        validation["numerical_reproduction"] = False
        validation.setdefault("warnings", []).append("Fresh freeze/evaluate source bytes differ.")
    if commit_result["returncode"] != 0 or evaluate_result["returncode"] != 0:
        validation.setdefault("warnings", []).append(
            f"Subprocess nonzero return code: commit={commit_result['returncode']} evaluate={evaluate_result['returncode']}"
        )
        if evaluate_result["returncode"] not in (0,):
            validation["execution_status"] = "REPRODUCTION_ERROR"
            validation["numerical_reproduction"] = False
    validation["protocol"] = cfg.version
    validation["script"] = cfg.script
    write_json(protocol_dir / "wrapper_verdict.json", validation)
    log_line(log_fh, f"END protocol {cfg.key}: {validation['execution_status']}")
    return validation


def run_strict_verifier(
    cfg: ProtocolConfig,
    run_dir: Path,
    log_fh: Any,
    strict: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    protocol_dir = run_dir / cfg.key
    evaluation_dir = protocol_dir / "evaluation"
    manifest_path = protocol_dir / "commitment" / "prospective_protocol.json"
    verifier = STRICT_VERIFIERS[cfg.key]
    args = [
        sys.executable,
        verifier,
        "--reuse-existing",
        str(evaluation_dir),
        "--manifest",
        str(manifest_path),
        "--output-root",
        str(run_dir / "strict_verifier_runs"),
    ]
    if strict:
        args.append("--strict-environment")
    result = run_subprocess(args, log_fh, timeout_seconds)
    ok = result["returncode"] == 0
    parsed: Any = None
    if ok and result["stdout_tail"]:
        start = result["stdout_tail"].find("{")
        if start >= 0:
            try:
                parsed = json.loads(result["stdout_tail"][start:])
            except Exception:
                parsed = None
    return {
        "name": verifier,
        "execution_status": "STRICT_AUDIT_PASS" if ok else "STRICT_AUDIT_ERROR",
        "returncode": result["returncode"],
        "subprocess": result,
        "parsed_tail_json": parsed,
    }


def run_repository_audit(run_dir: Path, log_fh: Any, timeout_seconds: int) -> dict[str, Any]:
    result = run_subprocess([sys.executable, "audit_repository.py", "--json"], log_fh, timeout_seconds)
    ok = result["returncode"] == 0
    parsed: Any = None
    if result["stdout_tail"]:
        start = result["stdout_tail"].find("{")
        if start >= 0:
            try:
                parsed = json.loads(result["stdout_tail"][start:])
            except Exception:
                parsed = None
    write_json(run_dir / "repository_audit.json", parsed if parsed is not None else result)
    return {
        "name": "audit_repository.py",
        "execution_status": "STRICT_AUDIT_PASS" if ok else "STRICT_AUDIT_ERROR",
        "returncode": result["returncode"],
        "checks_ok": bool(parsed.get("checks_ok")) if isinstance(parsed, dict) else False,
        "subprocess": result,
    }


def run_tamper_tests(run_dir: Path, log_fh: Any, timeout_seconds: int) -> dict[str, Any]:
    result = run_subprocess([sys.executable, "-m", "unittest", "discover", "-s", "tests"], log_fh, timeout_seconds)
    ok = result["returncode"] == 0
    write_json(run_dir / "tamper_tests.json", result)
    return {
        "name": "python -m unittest discover -s tests",
        "execution_status": "TAMPER_TESTS_PASS" if ok else "TAMPER_TESTS_ERROR",
        "returncode": result["returncode"],
        "subprocess": result,
    }


def write_run_checksums(run_dir: Path) -> Path:
    checksum_path = run_dir / "artifact_checksums.sha256"
    rows: list[str] = []
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        if path == checksum_path:
            continue
        rows.append(f"{file_sha256(path)}  {path.relative_to(run_dir).as_posix()}")
    checksum_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return checksum_path


def summarize_run(
    run_dir: Path,
    env: dict[str, Any],
    protocol_results: dict[str, Any],
    strict_audits: dict[str, Any],
) -> dict[str, Any]:
    protocol_error = any(result["execution_status"] == "REPRODUCTION_ERROR" for result in protocol_results.values())
    strict_error = any(
        result.get("execution_status") in {"STRICT_AUDIT_ERROR", "TAMPER_TESTS_ERROR"}
        for result in strict_audits.values()
    )
    if protocol_error or strict_error:
        overall = "REPRODUCTION_ERROR"
    else:
        overall = "REPRODUCED_EXPECTED_RESULTS"
    return {
        "run_dir": str(run_dir),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": env,
        "protocols": protocol_results,
        "strict_audits": strict_audits,
        "overall_reproduction_status": overall,
    }


def exit_code_for_summary(summary: dict[str, Any]) -> int:
    return 0 if summary.get("overall_reproduction_status") == "REPRODUCED_EXPECTED_RESULTS" else 1


def selected_protocols(selection: str) -> list[ProtocolConfig]:
    if selection == "all":
        return [PROTOCOLS["v2"], PROTOCOLS["v3"]]
    return [PROTOCOLS[selection]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run external reproduction of the frozen protocols.")
    parser.add_argument("--preflight", action="store_true", help="Check environment and inputs without running physics.")
    parser.add_argument("--protocol", choices=("v2", "v3", "all"), default="all", help="Protocol to reproduce.")
    parser.add_argument("--strict-environment", action="store_true", help="Fail unless running under CPython 3.12.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT, help="Root directory for unique external runs.")
    parser.add_argument("--timeout-seconds", type=int, default=3600, help="Timeout for each subprocess stage.")
    args = parser.parse_args(argv)

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = REPO_ROOT / output_root

    preflight = preflight_checks(output_root, args.strict_environment)
    if args.preflight:
        print_preflight(preflight)
        return 0 if preflight["ok"] else 1
    if not preflight["ok"]:
        print_preflight(preflight)
        return 1
    for warning in preflight["warnings"]:
        print(f"WARNING: {warning}", file=sys.stderr)

    run_dir = unique_run_dir(output_root)
    log_path = run_dir / "reproduction.log"
    env = preflight["environment"]
    write_json(run_dir / "environment.json", env)
    protocol_results: dict[str, Any] = {}
    strict_audits: dict[str, Any] = {}
    with log_path.open("w", encoding="utf-8") as log_fh:
        log_line(log_fh, f"External reproduction run directory: {run_dir}")
        for cfg in selected_protocols(args.protocol):
            protocol_results[cfg.key] = run_protocol(cfg, run_dir, log_fh, args.timeout_seconds)
        for cfg in selected_protocols(args.protocol):
            strict_audits[f"{cfg.key}_strict_verifier"] = run_strict_verifier(
                cfg, run_dir, log_fh, args.strict_environment, args.timeout_seconds
            )
        if args.protocol == "all":
            strict_audits["repository_audit"] = run_repository_audit(run_dir, log_fh, args.timeout_seconds)
            strict_audits["tamper_tests"] = run_tamper_tests(run_dir, log_fh, args.timeout_seconds)
        summary = summarize_run(run_dir, env, protocol_results, strict_audits)
        write_json(run_dir / "reproduction_summary.json", summary)
        write_run_checksums(run_dir)
        log_line(log_fh, f"OVERALL {summary['overall_reproduction_status']}")

    print(f"Reproduction run written to {run_dir}")
    print(f"Overall status: {summary['overall_reproduction_status']}")
    for key, result in protocol_results.items():
        print(f"{key}: {result['execution_status']} ({result['scientific_status']})")
    for key, result in strict_audits.items():
        print(f"{key}: {result['execution_status']}")
    return exit_code_for_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())
