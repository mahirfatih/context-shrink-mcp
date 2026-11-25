#!/usr/bin/env python3
"""Automated UI (CLI output contract) tests for context-shrink-mcp."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "context-shrink.py"


class AutomatedUiTests(unittest.TestCase):
    def test_version_prints_version(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--version"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("context-shrink-mcp", proc.stdout)

    def test_help_prints_usage(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("context-shrink", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
