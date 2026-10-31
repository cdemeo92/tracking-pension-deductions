import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import extract_zucchetti
import state


class PensionWorkflowIntegrationTests(unittest.TestCase):
    def test_verified_payslip_is_applied_and_appears_in_recap(self):
        parsed_month = {
            (2026, 9): {
                "total": 90,
                "employee": 23.57,
                "employer": 66.43,
                "rows": 2,
            }
        }
        with patch.object(extract_zucchetti, "parse_file", return_value=parsed_month):
            extracted = extract_zucchetti.extract_files(["cedolino.pdf"], 2026, "it")

        self.assertEqual(extracted["problems"], [])
        self.assertIn("Settembre", extracted["table"])

        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "tracker.html"
            changes = Path(directory) / "changes.json"
            with patch.object(state, "PUBLISHED_TEMPLATE", state.TEMPLATE):
                state.cmd_init(Namespace(page=str(page), year=2026, limit=5300))
            changes.write_text(json.dumps(extracted["changes"]), encoding="utf-8")

            result = state.cmd_apply(Namespace(page=str(page), changes=str(changes), lang="it"))
            _, saved = state.read_state(page)

        self.assertEqual(saved["months"]["9"], {"employee": 23.57, "employer": 66.43})
        self.assertEqual(result["recap"]["total_deductible"], 90)
        self.assertIn("90,00 €", result["recap_markdown"])


if __name__ == "__main__":
    unittest.main()