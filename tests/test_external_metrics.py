"""Independent examples for the frozen evaluator, requiring no model or data."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / "scripts/evaluate_external.py"
spec = importlib.util.spec_from_file_location("external_eval", source)
external = importlib.util.module_from_spec(spec)
spec.loader.exec_module(external)


class ExternalMetricsTests(unittest.TestCase):
    def test_exact_match(self):
        result = external.score({(2, 8, "PERSON")}, {(2, 8, "PERSON")})["PERSON"]
        self.assertEqual((result["tp"], result["fp"], result["fn"], result["f1"]), (1, 0, 0, 1))

    def test_overlap_does_not_get_partial_credit(self):
        result = external.score({(2, 8, "PERSON")}, {(2, 7, "PERSON")})["PERSON"]
        self.assertEqual((result["tp"], result["fp"], result["fn"], result["f1"]), (0, 1, 1, 0))

    def test_wrong_label_counts_false_positive_and_false_negative(self):
        result = external.score({(2, 8, "PERSON")}, {(2, 8, "ORG")})
        self.assertEqual(result["PERSON"]["fn"], 1)
        self.assertEqual(result["ORG"]["fp"], 1)

    def test_undefined_metrics_and_missed_entity(self):
        self.assertIsNone(external.prf(0, 0, 0)["f1"])
        self.assertEqual(external.prf(0, 0, 1)["f1"], 0)
        self.assertIsNone(external.prf(0, 0, 1)["precision"])

    def test_selection_is_fixed_unique_and_not_prefix(self):
        indices = external.selection(1500)
        self.assertEqual(len(indices), 500)
        self.assertEqual(len(set(indices)), 500)
        self.assertEqual(indices, external.selection(1500))
        self.assertNotEqual(indices, list(range(500)))

    def test_modified_data_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text("[]")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                external.load_dataset(path)

    def test_percentiles_are_nearest_rank(self):
        self.assertEqual(external.percentile([10, 30, 20, 40], 0.5), 20)
        self.assertEqual(external.percentile([10, 30, 20, 40], 0.95), 40)


if __name__ == "__main__":
    unittest.main()
