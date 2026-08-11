"""Release-run core integrity tests; aggregate-only and dependency-free."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent


class Stage7CoreReleaseTests(unittest.TestCase):
    def test_authoritative_release_is_deterministic(self):
        script = PACKAGE / "scripts" / "integrate_release_run.py"
        proc = subprocess.run([sys.executable, str(script), "--verify-only"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["unresolved"], 0)
        self.assertEqual(summary["public_scan_failures"], 0)


if __name__ == "__main__":
    unittest.main()
