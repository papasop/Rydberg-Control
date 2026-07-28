# ================================================================
# v3.0.2 — ONE-CLICK FROZEN EVALUATION
# ================================================================
# Standalone verifier/packager for the frozen v3.0.2 commitment.
# It imports the frozen protocol machinery from the main script;
# run from the directory containing both files.
#
#   python pasqal_kqs_v302_one_click.py

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from pasqal_kz_quasistatic_ranking_v3_0_2 import (
    evaluate,
    protocol_hash,
    source_hash,
)

EXPECTED_PROTOCOL_HASH = (
    "c9917d5119b520fa17e1e56f1d903403"
    "b3e2d963d5a24e32e3945fbd253ba39e"
)

# NOTE: the evaluated v3.0.2 source hashed to ae7dcfd7...; this repository
# ships a docstring-only cleanup (stale stage-2 filename and noise-model
# description corrected), which changes the bytecode-inventory hash to the
# value below. The frozen protocol and all scientific logic are untouched,
# and EXPECTED_PROTOCOL_HASH is unchanged.
EXPECTED_SOURCE_HASH = (
    "7ed2c8fe92355629bedd7b8ce057712c"
    "94845fe27821e8aa0871a774ca667874"
)

MANIFEST = Path(
    "pasqal_kz_commit_c9917d5119b5/"
    "prospective_protocol.json"
)

OUTPUT_DIR = Path(
    "pasqal_kqs_v302_eval_c9917d5119b5"
)

ZIP_BASENAME = (
    "pasqal_kqs_v302_c9917d5119b5_result"
)


# 1. Verify runtime and commitment
if not MANIFEST.exists():
    raise FileNotFoundError(
        f"Manifest not found: {MANIFEST}"
    )

manifest = json.loads(
    MANIFEST.read_text(encoding="utf-8")
)

# Known source hashes. The frozen manifest records the source as evaluated
# on 2026-07-27 (COMMITTED_SOURCE_HASH). The repository ships a
# docstring-only cleanup of that file (EXPECTED_SOURCE_HASH); both are
# accepted runtime sources because the frozen PROTOCOL is untouched.
COMMITTED_SOURCE_HASH = (
    "ae7dcfd733568901aa526ad2c2ad4e89"
    "a4da1f3378edcfe5b03035de8d026843"
)
KNOWN_SOURCE_HASHES = {
    EXPECTED_SOURCE_HASH,
    COMMITTED_SOURCE_HASH,
}

# Test repeated stability after code has executed
runtime_source_hash_1 = source_hash()

for _ in range(10):
    protocol_hash()
    source_hash()

runtime_source_hash_2 = source_hash()

checks = {
    "manifest_protocol_matches": (
        manifest.get("protocol_sha256")
        == EXPECTED_PROTOCOL_HASH
    ),
    "runtime_protocol_matches": (
        protocol_hash()
        == EXPECTED_PROTOCOL_HASH
    ),
    "manifest_source_is_known": (
        manifest.get("source_sha256")
        in KNOWN_SOURCE_HASHES
    ),
    "runtime_source_is_known": (
        runtime_source_hash_1
        in KNOWN_SOURCE_HASHES
    ),
    "repeated_source_hash_stable": (
        runtime_source_hash_1
        == runtime_source_hash_2
    ),
    "outcomes_not_computed_at_commitment": (
        manifest.get("outcomes_computed") is False
    ),
}

print("=" * 96)
print("v3.0.2 COMMITMENT VERIFICATION")
print("=" * 96)
print(json.dumps(checks, indent=2))
print(f"runtime_source_sha256={runtime_source_hash_1}")

if not all(checks.values()):
    raise RuntimeError(
        "Commitment verification failed. "
        "Do not bypass the failed gate."
    )


# 2. Evaluate
summary_path = OUTPUT_DIR / "summary.json"

if OUTPUT_DIR.exists():
    if not summary_path.exists():
        raise RuntimeError(
            f"Partial output directory exists: {OUTPUT_DIR}. "
            "Change OUTPUT_DIR to a new unused name."
        )

    print(
        "\nCompleted result already exists; "
        "packaging without rerunning."
    )
else:
    evaluate_args = argparse.Namespace(
        evaluate=True,
        one_click=False,
        expected_hash=EXPECTED_PROTOCOL_HASH,
        manifest=str(MANIFEST),
        outdir=str(OUTPUT_DIR),
    )

    print("\n" + "=" * 96)
    print("STARTING FROZEN HELD-OUT EVALUATION")
    print("=" * 96)

    scientific_return_code = evaluate(
        evaluate_args
    )

    print(
        f"\nscientific_return_code="
        f"{scientific_return_code}"
    )


# 3. Verify result artifacts
required_artifacts = [
    "predicted_ranking_frozen_before_heldout.json",
    "candidate_ranking_results.csv",
    "heldout_results.csv",
    "candidate_predictor_audit.json",
    "reference_control.csv",
    "selected_control.csv",
    "summary.json",
]

missing = [
    name for name in required_artifacts
    if not (OUTPUT_DIR / name).exists()
]

if missing:
    raise RuntimeError(
        "Missing artifacts:\n" + "\n".join(missing)
    )

summary = json.loads(
    summary_path.read_text(encoding="utf-8")
)

ranking_path = (
    OUTPUT_DIR /
    "predicted_ranking_frozen_before_heldout.json"
)

ranking_sha256 = hashlib.sha256(
    ranking_path.read_bytes()
).hexdigest()

if (
    ranking_sha256
    != summary.get("ranking_certificate_sha256")
):
    raise RuntimeError(
        "Frozen ranking certificate hash mismatch."
    )


# 4. Package result
zip_path = Path(
    shutil.make_archive(
        ZIP_BASENAME,
        "zip",
        root_dir=OUTPUT_DIR,
    )
)

zip_sha256 = hashlib.sha256(
    zip_path.read_bytes()
).hexdigest()

certificate = {
    "script_id": "KQS-PROSPECTIVE-DETUNING-RANKING-v3.0.2",
    "protocol_sha256": EXPECTED_PROTOCOL_HASH,
    "source_sha256": runtime_source_hash_1,
    "ranking_sha256": ranking_sha256,
    "result_zip_sha256": zip_sha256,
    "scientific_status":
        summary.get("scientific_status"),
    "all_gates_pass":
        summary.get("all_gates_pass"),
    "candidate_audit":
        summary.get("candidate_audit"),
    "heldout_rows":
        summary.get("heldout_rows"),
    "gates":
        summary.get("gates"),
    "claim_boundary":
        summary.get("claim_boundary"),
}

certificate_path = Path(
    f"{ZIP_BASENAME}_certificate.json"
)

certificate_path.write_text(
    json.dumps(
        certificate,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print("\n" + "=" * 96)
print("FINAL CERTIFICATE")
print("=" * 96)
print(json.dumps(certificate, indent=2, ensure_ascii=False))
print(f"\nZIP={zip_path.resolve()}")
print(f"CERTIFICATE={certificate_path.resolve()}")


# 5. Download
try:
    from google.colab import files

    files.download(str(zip_path))
    files.download(str(certificate_path))
except ImportError:
    print("Download the files manually.")