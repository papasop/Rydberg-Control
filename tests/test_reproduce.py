import math
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import reproduce
import verify_v201_strict_v1 as v201


class ReproduceWrapperTests(unittest.TestCase):
    def test_canonical_protocol_hash_v3(self):
        manifest = reproduce.read_json(reproduce.REPO_ROOT / "manifests/v3.0.2/prospective_protocol.json")
        self.assertEqual(
            reproduce.canonical_json_hash(manifest["protocol"]),
            reproduce.PROTOCOLS["v3"].expected_protocol_hash,
        )

    def test_canonical_protocol_hash_v2(self):
        manifest = reproduce.read_json(reproduce.REPO_ROOT / "manifests/v2.0.1/prospective_protocol.json")
        self.assertEqual(
            reproduce.canonical_json_hash(manifest["protocol"]),
            reproduce.PROTOCOLS["v2"].expected_protocol_hash,
        )

    def test_unique_run_dir_never_overwrites(self):
        fixed = datetime(2026, 7, 28, 1, 2, 3, tzinfo=timezone.utc)
        ids = iter(["abcd1234", "abcd1234", "efef5678"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = reproduce.unique_run_dir(root, now=lambda: fixed, short_id_fn=lambda: next(ids))
            second = reproduce.unique_run_dir(root, now=lambda: fixed, short_id_fn=lambda: next(ids))
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_build_commands_use_current_python(self):
        cmd = reproduce.build_commit_command(reproduce.PROTOCOLS["v3"], Path("out"))
        self.assertEqual(cmd[0], sys.executable)

    def test_v3_classifies_expected_pass(self):
        summary = reproduce.read_json(reproduce.REPO_ROOT / "results/v3.0.2/summary.json")
        status, warnings, details = reproduce.classify_summary(reproduce.PROTOCOLS["v3"], summary)
        self.assertEqual(status, "REPRODUCED_EXPECTED_PASS")
        self.assertTrue(details["numerical_reproduction"])
        self.assertEqual(warnings, [])

    def test_v2_classifies_expected_negative(self):
        summary = reproduce.read_json(reproduce.REPO_ROOT / "results/v2.0.1/summary.json")
        status, warnings, details = reproduce.classify_summary(reproduce.PROTOCOLS["v2"], summary)
        self.assertEqual(status, "REPRODUCED_EXPECTED_NEGATIVE")
        self.assertTrue(details["numerical_reproduction"])
        self.assertEqual(warnings, [])

    def test_missing_summary_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = reproduce.validate_evaluation(reproduce.PROTOCOLS["v3"], root / "commitment", root / "evaluation")
            self.assertEqual(result["execution_status"], "REPRODUCTION_ERROR")
            self.assertFalse(result["numerical_reproduction"])

    def test_nonfinite_numeric_detection(self):
        self.assertFalse(reproduce.finite_numbers({"x": math.nan}))
        self.assertFalse(reproduce.finite_numbers({"x": math.inf}))
        self.assertTrue(reproduce.finite_numbers({"x": 1.0, "nested": [2, True]}))

    def test_strict_environment_rejects_non_312(self):
        env = {
            "python": {"implementation": "CPython", "version_info": [3, 11, 9, "final", 0]},
            "packages": {"numpy": "2.0.2", "scipy": "1.13.1"},
        }
        warnings, errors = reproduce.environment_warnings(env, strict=True)
        self.assertEqual(warnings, [])
        self.assertTrue(errors)

    def test_exit_code_reflects_reproduction_error(self):
        self.assertEqual(reproduce.exit_code_for_summary({"overall_reproduction_status": "REPRODUCTION_ERROR"}), 1)
        self.assertEqual(reproduce.exit_code_for_summary({"overall_reproduction_status": "REPRODUCED_EXPECTED_RESULTS"}), 0)

    def test_v201_ranking_hash_matches_summary(self):
        summary = v201.read_json(v201.REPO_ROOT / "results/v2.0.1/summary.json")
        ranking_path = v201.REPO_ROOT / "results/v2.0.1/predicted_ranking_frozen_before_heldout.json"
        self.assertEqual(v201.sha256_bytes(ranking_path), summary["ranking_certificate_sha256"])

    def test_v201_selected_candidate_cross_check(self):
        ranking = v201.read_json(v201.REPO_ROOT / "results/v2.0.1/predicted_ranking_frozen_before_heldout.json")
        self.assertEqual(v201.selected_from_ranking(ranking), "v00_m_0.030")


if __name__ == "__main__":
    unittest.main()
