"""Tests for the Bills and Renewals plugin script."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/bills-and-renewals/scripts/renewals.py"


class RenewalsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / "data" / "items.json"
        self.today = "2026-11-08"

    def run_cli(self, *args, ok=True):
        env = {**os.environ, "RENEWALS_FILE": str(self.file), "RENEWALS_TODAY": self.today}
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def json_cli(self, *args):
        return json.loads(self.run_cli(*args, "--json"))

    def item(self, item_id=1):
        return next(i for i in json.loads(self.file.read_text())["items"] if i["id"] == item_id)

    def test_month_end_clamps_and_returns_to_anchor(self):
        self.run_cli("add", "Rent", "--due", "2027-01-31", "--repeat", "monthly")
        expected = ["2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31"]
        for date in expected:
            self.run_cli("paid", "1")
            self.assertEqual(self.item()["due"], date)

    def test_leap_day_yearly(self):
        self.run_cli("add", "Licence", "--due", "2028-02-29", "--repeat", "yearly")
        self.run_cli("paid", "1")
        self.assertEqual(self.item()["due"], "2029-02-28")
        for _ in range(3):
            self.run_cli("paid", "1")
        self.assertEqual(self.item()["due"], "2032-02-29")

    def test_late_payment_keeps_schedule_and_one_off_finishes(self):
        self.run_cli("add", "Power", "--due", "2026-10-05", "--repeat", "monthly")
        self.run_cli("paid", "1", "--on", "2026-11-08")
        self.assertIn("OVERDUE", self.run_cli("list"))
        self.assertEqual(self.item()["due"], "2026-11-05")
        self.assertEqual(self.item()["history"][0]["paid_on"], "2026-11-08")
        self.run_cli("add", "Visa", "--due", "2026-12-01")
        self.run_cli("paid", "2")
        self.assertTrue(self.item(2)["done"])
        self.assertEqual([r["id"] for r in self.json_cli("list")], [1])
        self.assertEqual(len(self.json_cli("list", "--all")), 2)
        self.run_cli("paid", "2", ok=False)

    def test_due_uses_each_reminder_window(self):
        self.run_cli("add", "Soon", "--due", "2026-11-10", "--kind", "bill")
        self.run_cli("add", "Later", "--due", "2026-11-20", "--kind", "bill")
        self.run_cli("add", "Passport", "--due", "2026-12-20", "--kind", "document")
        self.assertEqual([r["name"] for r in self.json_cli("due")], ["Soon", "Passport"])
        self.assertEqual([r["name"] for r in self.json_cli("due", "--within", "15")], ["Soon", "Later"])

    def test_summary_groups_currencies_without_converting(self):
        self.run_cli("add", "A", "--due", "2026-11-20", "--repeat", "monthly", "--amount", "1,000", "--currency", "inr")
        self.run_cli("add", "B", "--due", "2027-06-01", "--repeat", "yearly", "--amount", "1200", "--currency", "INR")
        self.run_cli("add", "C", "--due", "2026-11-09", "--repeat", "weekly", "--amount", "12", "--currency", "USD")
        self.run_cli("add", "D", "--due", "2027-01-01", "--kind", "document")
        report = self.json_cli("summary")
        self.assertEqual(report["currencies"]["INR"]["recurring_per_month"], "1100.00")
        self.assertEqual(report["currencies"]["INR"]["due_through_next_30_days"], "1000.00")
        self.assertEqual(report["currencies"]["USD"]["recurring_per_month"], "52.00")
        self.assertEqual(report["currencies"]["USD"]["due_through_next_30_days"], "60.00")
        self.assertEqual(report["items_without_amount"], 1)

    def test_refuses_account_numbers_and_bad_input(self):
        self.assertIn("card, account", self.run_cli("add", "Card 4111 1111 1111 1111", "--due", "2026-12-01", ok=False))
        self.run_cli("add", "X", "--due", "2026-12-01", "--note", "account 123456789012", ok=False)
        self.run_cli("add", "X", "--due", "2026-02-30", ok=False)
        self.run_cli("add", "X", "--due", "2026-12-01", "--amount", "-5", ok=False)
        self.run_cli("add", "X", "--due", "2026-12-01", "--amount", "NaN", ok=False)
        self.run_cli("add", "X", "--due", "2026-12-01", "--remind", "-1", ok=False)
        self.assertFalse(self.file.exists())

    def test_ids_are_not_reused_and_file_is_private(self):
        self.run_cli("add", "A", "--due", "2026-12-01")
        self.run_cli("remove", "1")
        self.run_cli("add", "B", "--due", "2026-12-01")
        self.assertEqual(self.item(2)["name"], "B")
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)

    def test_damaged_file_is_left_alone(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text("{oops")
        self.assertIn("damaged", self.run_cli("add", "A", "--due", "2026-12-01", ok=False))
        self.assertEqual(self.file.read_text(), "{oops")

    def test_ics_export(self):
        self.run_cli("add", "Rent, flat; A", "--due", "2027-01-31", "--repeat", "monthly", "--amount", "100", "--currency", "INR", "--remind", "2")
        self.run_cli("add", "Quarterly", "--due", "2027-01-15", "--repeat", "quarterly")
        self.run_cli("add", "Leap", "--due", "2028-02-29", "--repeat", "yearly")
        self.run_cli("add", "Now", "--due", "2026-12-01", "--remind", "0")
        self.run_cli("add", "L" * 200, "--due", "2026-12-02")
        out = Path(self.dir.name) / "cal.ics"
        self.run_cli("export-ics", "--out", str(out))
        raw = out.read_bytes()
        self.assertTrue(all(len(line) <= 75 for line in raw.split(b"\r\n")))
        text = raw.decode().replace("\r\n ", "")
        self.assertIn("SUMMARY:Rent\\, flat\\; A (100 INR)", text)
        self.assertIn("RRULE:FREQ=MONTHLY;BYMONTHDAY=28,29,30,31;BYSETPOS=-1", text)
        self.assertIn("RRULE:FREQ=MONTHLY;INTERVAL=3\r\n", text)
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=28,29;BYSETPOS=-1", text)
        self.assertIn("TRIGGER:-P2D", text)
        self.assertIn("TRIGGER:PT0S", text)
        self.assertEqual(text.count("BEGIN:VEVENT"), text.count("END:VEVENT"))
        self.run_cli("export-ics", "--out", str(Path(self.dir.name) / "notes.txt"), ok=False)


if __name__ == "__main__":
    unittest.main()
