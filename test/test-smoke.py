#!/usr/bin/env python3
"""Smoke tests for context-shrink-mcp.

Smoke = fastest safety net: does the script run, compile, and import?
"""
from __future__ import annotations

import importlib.util
import py_compile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "context-shrink.py"


def load_module():
    spec = importlib.util.spec_from_file_location("context_shrink", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_script_file_exists(self):
        self.assertTrue(SCRIPT_PATH.is_file())

    def test_script_compiles(self):
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as f:
            py_compile.compile(str(SCRIPT_PATH), cfile=f.name, doraise=True)

    def test_module_loads(self):
        self.assertTrue(hasattr(self.mod, "main"))
        self.assertTrue(hasattr(self.mod, "server"))

    def test_version_flag(self):
        import subprocess, sys
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--version"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("context-shrink-mcp", proc.stdout)

    def test_help_flag_does_not_crash(self):
        import subprocess, sys
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True, text=True, timeout=30,
        )
        # argparse exits 0 on --help
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
