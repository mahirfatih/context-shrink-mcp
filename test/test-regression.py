#!/usr/bin/env python3
"""Regression tests for context-shrink-mcp."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "context-shrink.py"


def load_module():
    spec = importlib.util.spec_from_file_location("context_shrink", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_crlf_injection_in_content(self):
        msgs = [{"role": "user", "content": "line1\r\nline2"}]
        out = self.mod._estimate_tokens(msgs)
        self.assertGreater(out, 0)

    def test_utf8_emojis(self):
        msgs = [{"role": "user", "content": "merhaba 🚀🎉"}]
        out = self.mod._estimate_tokens(msgs)
        self.assertGreater(out, 0)

    def test_empty_messages(self):
        self.assertEqual(self.mod._estimate_tokens([]), 1)

    def test_compact_nothing_to_compact(self):
        msgs = [{"role": "user", "content": "hi"}]
        out = json.loads(self.mod.compact_context(msgs, keep_last=8))
        self.assertFalse(out["compacted"])
        self.assertEqual(out["reason"], "nothing_to_compact")

    def test_trim_idempotent(self):
        msgs = [{"role": "user", "content": "a" * 500} for _ in range(5)]
        first = self.mod._trim_messages(msgs, keep_last=2, max_context_tokens=1)
        second = self.mod._trim_messages(first, keep_last=2, max_context_tokens=1)
        self.assertEqual(len(first), len(second))


if __name__ == "__main__":
    unittest.main()
