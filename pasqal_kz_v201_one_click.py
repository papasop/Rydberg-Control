# ================================================================
# v2.0.1 — ONE-CLICK FROZEN K(z) RANKING EVALUATION + EXPORT
# ================================================================
# Standalone verifier/packager for the frozen v2.0.1 commitment
# (weak local Markovian dephasing). It imports the frozen protocol
# machinery from the main v2.0.1 script; run from the directory
# containing both files, after stage 1 has produced the manifest.
#
#   python pasqal_kz_v201_one_click.py

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from pasqal_kz_task_ranking_prospective_v2_0_1 import (
    evaluate,
    protocol_hash,
    source_hash,
)

EXPECTED_PROTOCOL_HASH = (
    "2c05a45f5d534f581c0491a5215534ae"
    "657f3eae26e7362ea436850d51d909c4"
)

# Known source hashes for the v2.0.1 evaluator (see README section 5,
# commitment history). The frozen protocol — and therefore
# EXPECTED_PROTOCOL_HASH — is identical across all of them; only the
# source-hash *definition* and docstrings changed.
KNOWN_SOURCE_HASHES = {
    # Notebook-global hash at the first (superseded, never evaluated)
    # v2.0 freeze.
    "42de3826395c0d56ef31a1c360d40501d4a7c133be592c5c3aba8bf24a0a9285",
    # Notebook-global hash recorded in the evaluated v2.0.1 manifest.
    "7e8828728455e58e629d359bf084f66c8123c3e85f05771cafe5b84652dcd115",
    # Colab-stable hash under which v2.0.1 was actually evaluated.
    "620f8c43655498bfb1be67c4d72e799539508222f2bb0e84b6d545191e18e821",
    # Hash of the byte-identical script shipped in this repository,
    # recomputed under the frozen stable-hash inventory (Python 3.12).
    "8442f0282845be197446299692af57ebd99a45cb5877674bc3d9abb79ebd518b",
}

EXPECTED_SOURCE_HASH = (
    "620f8c43655498bfb1be67c4d72e799539508222f2bb0e84b6d545191e18e821"
)

MANIFEST = Path(
    "pasqal_kz_commit_2c05a45f5d53/"
    "prospective_protocol.json"
)

OUTPUT_DIR = Path("pasqal_kz_ranking_eval_2c05a45f5d53")
ZIP_BASENAME = "pasqal_kz_ranking_eval_2c05a45f5d53_frozen"


# ----------------------------------------------------------------
# 1. Imported evaluator functions are verified below via their hashes
# ----------------------------------------------------------------


# ----------------------------------------------------------------
# 2. Verify the frozen manifest
# ----------------------------------------------------------------

if not MANIFEST.exists():
    raise FileNotFoundError(
        f"Frozen manifest not found: {MANIFEST}"
    )

manifest_data = json.loads(
    MANIFEST.read_text(encoding="utf-8")
)

manifest_protocol_hash = manifest_data.get("protocol_sha256")
manifest_source_hash = manifest_data.get("source_sha256")
current_protocol_hash = protocol_hash()
current_source_hash = source_hash()

verification = {
    "expected_protocol_hash": EXPECTED_PROTOCOL_HASH,
    "manifest_protocol_hash": manifest_protocol_hash,
    "current_protocol_hash": current_protocol_hash,
    "expected_source_hash": EXPECTED_SOURCE_HASH,
    "manifest_source_hash": manifest_source_hash,
    "current_source_hash": current_source_hash,
    "manifest_outcomes_computed": manifest_data.get(
        "outcomes_computed"
    ),
}

print("=" * 96)
print("FROZEN COMMITMENT VERIFICATION")
print("=" * 96)
print(json.dumps(verification, indent=2))

if manifest_protocol_hash != EXPECTED_PROTOCOL_HASH:
    raise RuntimeError(
        "Manifest protocol hash does not match the frozen hash."
    )

if current_protocol_hash != EXPECTED_PROTOCOL_HASH:
    raise RuntimeError(
        "Current protocol differs from the frozen protocol."
    )

if manifest_source_hash not in KNOWN_SOURCE_HASHES:
    raise RuntimeError(
        "Manifest source hash is not a known v2.0.1 source hash."
    )

if current_source_hash not in KNOWN_SOURCE_HASHES:
    raise RuntimeError(
        "Current evaluator source is not a known v2.0.1 source."
    )

if manifest_data.get("outcomes_computed") is not False:
    raise RuntimeError(
        "Manifest does not certify outcomes_computed=False."
    )

print("\nCOMMITMENT VERIFIED.")
print("No threshold, protocol, or source change detected.")


# ----------------------------------------------------------------
# 3. Run the held-out evaluation
# ----------------------------------------------------------------

summary_path = OUTPUT_DIR / "summary.json"

if OUTPUT_DIR.exists():
    if summary_path.exists():
        print(
            "\nA completed output directory already exists. "
            "The existing result will be packaged without rerunning."
        )
    else:
        raise RuntimeError(
            f"Partial output directory exists: {OUTPUT_DIR}\n"
            "It will not be overwritten. Inspect it or choose a new "
            "OUTPUT_DIR name."
        )
else:
    evaluate_args = argparse.Namespace(
        evaluate=True,
        expected_hash=EXPECTED_PROTOCOL_HASH,
        manifest=str(MANIFEST),
        outdir=str(OUTPUT_DIR),
    )

    print("\n" + "=" * 96)
    print("STARTING FROZEN HELD-OUT EVALUATION")
    print("=" * 96)

    evaluate(evaluate_args)


# ----------------------------------------------------------------
# 4. Verify required output artifacts
# ----------------------------------------------------------------

required_outputs = [
    "predicted_ranking_frozen_before_heldout.json",
    "candidate_ranking_results.csv",
    "heldout_results.csv",
    "candidate_predictor_audit.json",
    "reference_control.csv",
    "selected_control.csv",
    "summary.json",
]

missing_outputs = [
    name for name in required_outputs
    if not (OUTPUT_DIR / name).exists()
]

if missing_outputs:
    raise RuntimeError(
        "Evaluation did not produce all required artifacts:\n"
        + "\n".join(missing_outputs)
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

print("\n" + "=" * 96)
print("FINAL SCIENTIFIC STATUS")
print("=" * 96)
print(
    json.dumps(
        {
            "scientific_status":
                summary.get("scientific_status"),
            "all_gates_pass":
                summary.get("all_gates_pass"),
            "protocol_sha256":
                summary.get("protocol_sha256"),
            "ranking_certificate_sha256":
                summary.get("ranking_certificate_sha256"),
            "independently_recomputed_ranking_sha256":
                ranking_sha256,
            "gates":
                summary.get("gates"),
        },
        indent=2,
        ensure_ascii=False,
    )
)


# ----------------------------------------------------------------
# 5. Package all artifacts
# ----------------------------------------------------------------

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

export_certificate = {
    "protocol_sha256": EXPECTED_PROTOCOL_HASH,
    "source_sha256": current_source_hash,
    "ranking_certificate_sha256": ranking_sha256,
    "zip_file": str(zip_path),
    "zip_sha256": zip_sha256,
    "scientific_status": summary.get("scientific_status"),
    "all_gates_pass": summary.get("all_gates_pass"),
}

export_certificate_path = Path(
    f"{ZIP_BASENAME}_certificate.json"
)

export_certificate_path.write_text(
    json.dumps(
        export_certificate,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print("\n" + "=" * 96)
print("EXPORT COMPLETE")
print("=" * 96)
print(json.dumps(export_certificate, indent=2))
print(f"\nZIP: {zip_path.resolve()}")
print(f"CERTIFICATE: {export_certificate_path.resolve()}")


# ----------------------------------------------------------------
# 6. Download from Colab
# ----------------------------------------------------------------

try:
    from google.colab import files

    files.download(str(zip_path))
    files.download(str(export_certificate_path))
except ImportError:
    print(
        "\nNot running in Google Colab. "
        "Download the ZIP and certificate manually."
    )