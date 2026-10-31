import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import extract_zucchetti


class ZucchettiUnitTests(unittest.TestCase):
    def test_number_helpers_parse_italian_amounts(self):
        self.assertEqual(extract_zucchetti.to_number("1.234,56"), 1234.56)
        self.assertEqual(extract_zucchetti.last_number("base 1.234,56 contributo 23,57"), 23.57)
        self.assertIsNone(extract_zucchetti.last_number("nessun importo"))

    def test_parse_file_splits_employee_employer_and_total(self):
        pages = [
            "Zucchetti\nGennaio 2026\nF01998 90,00\n"
            "Z20000 Fondo pensione 23,57\nZ20000 Fondo pensione C/Ditta 66,43"
        ]
        with patch.object(extract_zucchetti, "read_pages", return_value=pages):
            result = extract_zucchetti.parse_file("cedolino.pdf")
        self.assertEqual(
            result[(2026, 1)],
            {"total": 90.0, "employee": 23.57, "employer": 66.43, "rows": 2},
        )

    def test_parse_file_returns_none_for_unrecognized_content(self):
        with patch.object(extract_zucchetti, "read_pages", return_value=["not a Zucchetti payslip"]):
            self.assertIsNone(extract_zucchetti.parse_file("other.pdf"))

    def test_extract_files_classifies_months_and_problems(self):
        parsed = {
            "valid.pdf": {(2026, 9): {"total": 90, "employee": 23.57, "employer": 66.43, "rows": 2}},
            "mismatch.pdf": {(2026, 8): {"total": 50, "employee": 20, "employer": 20, "rows": 2}},
            "other-year.pdf": {(2025, 1): {"total": 10, "employee": 5, "employer": 5, "rows": 2}},
            "no-pension.pdf": {(2026, 7): {"total": None, "employee": 0, "employer": 0, "rows": 0}},
            "missing-total.pdf": {(2026, 6): {"total": None, "employee": 2, "employer": 3, "rows": 1}},
            "missing-split.pdf": {(2026, 5): {"total": 20, "employee": 0, "employer": 0, "rows": 0}},
            "unknown.pdf": None,
        }

        def fake_parse(path):
            return parsed[Path(path).name]

        with patch.object(extract_zucchetti, "parse_file", side_effect=fake_parse):
            result = extract_zucchetti.extract_files(list(parsed), 2026, "it")

        self.assertEqual(result["changes"]["months"]["9"], {"employee": 23.57, "employer": 66.43, "control_total": 90})
        self.assertIn("Settembre", result["table"])
        self.assertEqual(result["no_pension"], ["Luglio 2026"])
        self.assertEqual(result["unrecognized"], ["unknown.pdf"])
        self.assertEqual({problem["issue"] for problem in result["problems"]}, {
            "mismatch", "other_year", "total_missing", "split_missing",
        })

    def test_conflicting_duplicate_month_stays_excluded(self):
        parsed = {
            "first.pdf": {(2026, 9): {"total": 10, "employee": 4, "employer": 6, "rows": 2}},
            "second.pdf": {(2026, 9): {"total": 12, "employee": 5, "employer": 7, "rows": 2}},
            "third.pdf": {(2026, 9): {"total": 10, "employee": 4, "employer": 6, "rows": 2}},
        }
        with patch.object(extract_zucchetti, "parse_file", side_effect=lambda path: parsed[Path(path).name]):
            result = extract_zucchetti.extract_files(list(parsed), 2026)
        self.assertEqual(result["changes"], {})
        self.assertEqual(result["problems"][0]["issue"], "conflicting_duplicate")

    def test_control_total_uses_two_cent_tolerance(self):
        parsed = {
            "within-tolerance.pdf": {(2026, 1): {"total": 10.02, "employee": 5, "employer": 5, "rows": 2}},
            "outside-tolerance.pdf": {(2026, 2): {"total": 10.03, "employee": 5, "employer": 5, "rows": 2}},
        }
        with patch.object(extract_zucchetti, "parse_file", side_effect=lambda path: parsed[Path(path).name]):
            result = extract_zucchetti.extract_files(list(parsed), 2026)
        self.assertIn("1", result["changes"]["months"])
        self.assertNotIn("2", result["changes"]["months"])
        self.assertEqual(result["problems"][0]["issue"], "mismatch")


if __name__ == "__main__":
    unittest.main()