import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

BASE = Path(__file__).resolve().parent.parent
OK_MAX = [{"success": True, "results": [{"m": 12}]}]
OK_ROWS = [{"success": True, "results": [{"seq": 12, "note": "fixture only"}]}]
OK_UPDATE = [{"success": True, "results": []}]
SENSITIVE = "fixture-sensitive-value-do-not-print"


class PullCorrectionsTests(unittest.TestCase):
    def run_fixture(self, response, phase="max", status=0):
        with tempfile.TemporaryDirectory(prefix="stringhomes-fixture-", dir="/tmp") as tmp:
            root = Path(tmp)
            for name in ["pull_corrections.sh", "parse_d1_response.py"]:
                if (BASE / name).exists():
                    shutil.copyfile(BASE / name, root / name)
            fixtures = {"max": OK_MAX, "rows": OK_ROWS, "update": OK_UPDATE}
            fixtures[phase] = response
            (root / "fixtures.json").write_text(json.dumps(fixtures))
            stub = root / "wrangler"
            stub.write_text('''#!/usr/bin/python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ["FIXTURE_ROOT"])
query = sys.argv[-1]
phase = "max" if "max(seq)" in query else "update" if query.startswith("update") else "rows"
with (root / "calls").open("a") as f:
    f.write(phase + "\\n")
value = json.loads((root / "fixtures.json").read_text())[phase]
print(value if isinstance(value, str) else json.dumps(value))
if phase == os.environ["FAIL_PHASE"]:
    print("fixture-sensitive-value-do-not-print", file=sys.stderr)
    sys.exit(int(os.environ["FAIL_STATUS"]))
''')
            stub.chmod(0o700)
            env = {"PATH": str(root) + ":/usr/bin:/bin", "FIXTURE_ROOT": str(root),
                   "FAIL_PHASE": phase, "FAIL_STATUS": str(status)}
            proc = subprocess.run(["/bin/bash", str(root / "pull_corrections.sh")],
                                  capture_output=True, text=True, env=env)
            calls = (root / "calls").read_text().splitlines()
            return proc, calls

    def test_success_and_empty_corrections(self):
        for rows in [OK_ROWS, [{"success": True, "results": []}]]:
            with self.subTest(rows=rows):
                proc, calls = self.run_fixture(rows, "rows")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(calls, ["max", "rows", "update"])
                self.assertEqual([json.loads(line) for line in proc.stdout.splitlines()], rows[0]["results"])

    def test_rejects_error_envelopes_without_ack_or_disclosure(self):
        for status in [0, 1]:
            for error in [{"text": "fetch failed " + SENSITIVE}, {"code": 10000, "text": SENSITIVE}]:
                with self.subTest(status=status, error=error):
                    proc, calls = self.run_fixture({"error": error}, status=status)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertEqual(calls, ["max"])
                    self.assertEqual(proc.stdout, "")
                    self.assertNotIn(SENSITIVE, proc.stderr)
                    self.assertNotIn("Traceback", proc.stderr)
                    self.assertIn("transport-error" if "fetch failed" in error["text"] else "error-envelope", proc.stderr)

    def test_rejects_malformed_and_unproven_success_shapes(self):
        invalid = ["not json " + SENSITIVE, [], {}, {"success": True, "results": [{"m": 12}]},
                   [{"success": False, "results": [{"m": 12}]}],
                   [{"success": True, "results": [{"m": "12; delete from corrections"}]}],
                   [{"success": True, "results": [{"m": True}]}],
                   [{"success": True, "results": [{"m": -1}]}],
                   [{"success": True, "results": []}],
                   [{"success": True, "results": [{"m": 1}]}, {"success": True, "results": []}]]
        for response in invalid:
            with self.subTest(response=response):
                proc, calls = self.run_fixture(response)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(calls, ["max"])
                self.assertEqual(proc.stdout, "")
                self.assertNotIn(SENSITIVE, proc.stderr)

    def test_nonzero_exit_rejects_even_success_shaped_stdout(self):
        proc, calls = self.run_fixture(OK_MAX, status=23)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(calls, ["max"])
        self.assertEqual(proc.stdout, "")
        self.assertNotIn(SENSITIVE, proc.stderr)

    def test_rows_rejected_before_output_and_ack(self):
        for response in [{"error": {"text": SENSITIVE}},
                         [{"success": True, "results": [{"seq": 1}, None]}]]:
            proc, calls = self.run_fixture(response, "rows")
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(calls, ["max", "rows"])
            self.assertEqual(proc.stdout, "")
            self.assertNotIn(SENSITIVE, proc.stderr)

    def test_update_failure_is_not_success(self):
        proc, calls = self.run_fixture({"error": {"text": SENSITIVE}}, "update", status=1)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(calls, ["max", "rows", "update"])
        self.assertNotIn(SENSITIVE, proc.stderr)


if __name__ == "__main__":
    unittest.main()
