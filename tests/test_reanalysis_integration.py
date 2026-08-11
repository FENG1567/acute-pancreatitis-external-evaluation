"""Tests for aggregate-only release integration; never read controlled artifacts."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReanalysisIntegrationTests(unittest.TestCase):
    def test_release_and_public_package_verify(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "integrate_release_run.py"), "--verify-only"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["unresolved"], 0)
        self.assertEqual(result["claims_unresolved"], 0)
        self.assertEqual(result["public_scan_failures"], 0)


if __name__ == "__main__":
    unittest.main()
