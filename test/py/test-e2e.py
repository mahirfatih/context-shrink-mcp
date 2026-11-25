#!/usr/bin/env python3
"""E2E tests for context-shrink-mcp: real CLI subprocess."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "context-shrink.py"


class E2ETests(unittest.TestCase):
    def test_version_subprocess(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--version"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.2.0", proc.stdout)

    def test_max_context_flag(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--max-context", "65536", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
