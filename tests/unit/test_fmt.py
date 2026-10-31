import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fmt


class FormatTests(unittest.TestCase):
    def test_language_prefix_and_unknown_languages_use_expected_labels(self):
        self.assertEqual(fmt.labels("it-IT"), fmt.labels("it"))
        self.assertEqual(fmt.labels("fr"), fmt.labels("en"))

    def test_money_uses_locale_separators_and_keeps_sign(self):
        self.assertEqual(fmt.money(1234.5, "it"), "1.234,50 €")
        self.assertEqual(fmt.money(-1234.5, "en"), "-€1,234.50")

    def test_table_renders_headers_and_rows(self):
        self.assertEqual(fmt.table(["A", "B"], [[1, 2]]), "| A | B |\n|---|---|\n| 1 | 2 |")


if __name__ == "__main__":
    unittest.main()