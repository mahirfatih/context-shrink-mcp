#!/usr/bin/env python3
"""Sanity tests for context-shrink-mcp: constants, defaults, config."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "context-shrink.py"


def load_module():
    spec = importlib.util.spec_from_file_location("context_shrink", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SanityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_default_max_context_tokens(self):
        self.assertEqual(self.mod.DEFAULT_MAX_CONTEXT_TOKENS, 32768)

    def test_max_context_ceiling(self):
        self.assertEqual(self.mod.MAX_CONTEXT_TOKENS_CEILING, 1_000_000)

    def test_coerce_budget_clamps(self):
        self.assertEqual(self.mod._coerce_budget(0), 1)
        self.assertEqual(self.mod._coerce_budget(2_000_000), 1_000_000)
        self.assertEqual(self.mod._coerce_budget("garbage"), self.mod.MAX_CONTEXT_TOKENS)

    def test_default_keep_last(self):
        self.assertEqual(self.mod.DEFAULT_KEEP_LAST, 8)

    def test_default_threshold(self):
        self.assertEqual(self.mod.DEFAULT_THRESHOLD, 0.8)

    def test_split_for_compaction_keeps_system_leading(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]
        leading, to_sum, keep = self.mod._split_for_compaction(msgs, 1)
        self.assertEqual(len(leading), 1)
        self.assertEqual(leading[0]["content"], "sys")
        self.assertEqual(len(keep), 1)

    def test_describe_config_returns_json(self):
        import json
        out = self.mod.describe_config()
        data = json.loads(out)
        self.assertIn("max_context_tokens", data)
        self.assertIn("tokenizer", data)


if __name__ == "__main__":
    unittest.main()
