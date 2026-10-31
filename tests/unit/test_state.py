from argparse import Namespace
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import state


def sample_state():
    return {
        "version": 1,
        "year": 2026,
        "limit": 5300,
        "rate": 2,
        "base": 1000,
        "bonus13": 1000,
        "bonus14": 500,
        "months": {"5": {"employee": 20, "employer": 30}},
        "voluntary": [{"date": "01/05/2026", "amount": 100}],
    }


class StateUnitTests(unittest.TestCase):
    def test_bundled_template_has_a_valid_empty_state(self):
        _, current = state.read_state(state.TEMPLATE)
        state.validate(current)
        self.assertEqual(current["year"], 2026)
        self.assertEqual(current["months"], {})
        self.assertEqual(current["voluntary"], [])

    def test_recap_sums_contributions_and_projects_through_year_end(self):
        recap = state.recap(sample_state())
        self.assertEqual(recap["employee"], 20)
        self.assertEqual(recap["employer"], 30)
        self.assertEqual(recap["voluntary"], 100)
        self.assertEqual(recap["total_deductible"], 150)
        self.assertEqual(recap["remaining_today"], 5150)
        self.assertEqual(recap["estimates"]["6"], 30)
        self.assertEqual(recap["estimates"]["12"], 40)
        self.assertEqual(recap["estimate_total"], 170)
        self.assertEqual(recap["remaining_year_end"], 4980)

    def test_recap_skips_estimates_without_months_or_required_parameters(self):
        current = sample_state()
        current["months"] = {}
        self.assertFalse(state.recap(current)["estimate_available"])

        current["months"] = {"5": {"employee": 20, "employer": 30}}
        current["rate"] = 0
        recap = state.recap(current)
        self.assertFalse(recap["estimate_available"])
        self.assertEqual(recap["estimate_missing_inputs"], ["rate"])

    def test_markdown_recap_localizes_and_reports_over_limit(self):
        current = sample_state()
        current["limit"] = 100
        output = state.recap_markdown(state.recap(current), "it")
        self.assertIn("Totale già deducibile", output)
        self.assertIn("Eccedenza oggi", output)
        self.assertIn("I contributi oltre il limite non sono deducibili.", output)

    def test_validate_rejects_invalid_month_and_boolean_amount(self):
        current = sample_state()
        current["months"]["13"] = {"employee": 1, "employer": 1}
        with self.assertRaises(state.Failure):
            state.validate(current)

        current = sample_state()
        current["months"]["5"]["employee"] = True
        with self.assertRaises(state.Failure):
            state.validate(current)

    def test_apply_rejects_a_payslip_total_mismatch(self):
        current = sample_state()
        with self.assertRaises(state.Failure):
            state.apply_changes(current, {"months": {"9": {"employee": 10, "employer": 20, "control_total": 35}}})
        self.assertNotIn("9", current["months"])

    def test_overwrites_and_duplicate_payments_require_confirmation(self):
        current = sample_state()
        changes = {
            "months": {"5": {"employee": 21, "employer": 30}},
            "voluntary_add": [{"date": "01/05/2026", "amount": 100}],
        }
        with self.assertRaises(state.Failure) as caught:
            state.apply_changes(current, changes)
        self.assertEqual(caught.exception.code, state.EXIT_CONFIRM)
        self.assertEqual(len(caught.exception.details), 2)
        self.assertEqual(current["months"]["5"]["employee"], 20)
        self.assertEqual(len(current["voluntary"]), 1)

        changes["confirmed"] = True
        state.apply_changes(current, changes)
        self.assertEqual(current["months"]["5"]["employee"], 21)
        self.assertEqual(len(current["voluntary"]), 2)

    def test_year_change_requires_full_reset_and_new_limit(self):
        invalid_changes = (
            {"params": {"year": 2027}},
            {"reset": {"year": 2027}},
            {"reset": {"year": 2027, "months": True, "voluntary": True}},
        )
        for changes in invalid_changes:
            current = sample_state()
            with self.subTest(changes=changes), self.assertRaises(state.Failure):
                state.apply_changes(current, changes)
            self.assertEqual(current["year"], 2026)
            self.assertTrue(current["months"])
            self.assertTrue(current["voluntary"])

        current = sample_state()
        state.apply_changes(current, {"reset": {"year": 2027, "limit": 5500, "months": True, "voluntary": True}})
        self.assertEqual((current["year"], current["limit"]), (2027, 5500))
        self.assertEqual(current["months"], {})
        self.assertEqual(current["voluntary"], [])

    def test_state_round_trip_escapes_script_openers(self):
        current = sample_state()
        current["extra"] = "</script><script>"
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            html = state.TEMPLATE.read_text(encoding="utf-8")
            state.write_state(page, html, current)
            saved_html, saved_state = state.read_state(page)
        self.assertIn("\\u003c/script>", saved_html)
        self.assertEqual(saved_state["extra"], "</script><script>")

    def test_init_requires_the_generated_single_file_template(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "tracker.html"
            with patch.object(state, "PUBLISHED_TEMPLATE", Path(directory) / "missing.html"):
                with self.assertRaises(state.Failure) as caught:
                    state.cmd_init(Namespace(page=str(page), year=2026, limit=5300))
        self.assertIn("npm run build", str(caught.exception))
        self.assertFalse(page.exists())

    def test_read_state_rejects_missing_and_invalid_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text("<html></html>", encoding="utf-8")
            with self.assertRaises(state.Failure):
                state.read_state(page)

            page.write_text('<script type="application/json" id="state">{</script>', encoding="utf-8")
            with self.assertRaises(state.Failure):
                state.read_state(page)

    def test_cli_apply_failure_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            html, initial_state = state.read_state(state.TEMPLATE)
            state.write_state(page, html, initial_state)
            original = page.read_text(encoding="utf-8")

            changes = Path(directory) / "changes.json"
            changes.write_text(json.dumps({"months": {"9": {"employee": 10, "employer": 20, "control_total": 35}}}), encoding="utf-8")
            applied = subprocess.run(
                [sys.executable, str(SCRIPTS / "state.py"), "apply", str(page), str(changes)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(applied.returncode, state.EXIT_INVALID)
            self.assertEqual(page.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()