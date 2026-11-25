#!/usr/bin/env python3
"""Unit tests for context-shrink-mcp pure helpers."""
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


class UnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_estimate_tokens_nonempty(self):
        msgs = [{"role": "user", "content": "hello world"}]
        self.assertGreater(self.mod._estimate_tokens(msgs), 0)

    def test_trim_messages_keeps_last(self):
        msgs = [{"role": "user", "content": "a" * 1000} for _ in range(10)]
        out = self.mod._trim_messages(msgs, keep_last=3, max_context_tokens=1)
        self.assertEqual(len(out), 3)

    def test_assemble_compaction(self):
        leading = [{"role": "system", "content": "sys"}]
        keep = [{"role": "user", "content": "last"}]
        out = self.mod._assemble_compaction(leading, "summary text", keep)
        self.assertEqual(len(out), 3)
        self.assertIn("summary text", out[1]["content"])

    def test_chunk_messages(self):
        msgs = [{"role": "user", "content": "x" * 100} for _ in range(5)]
        chunks = self.mod._chunk_messages(msgs, 50)
        self.assertGreaterEqual(len(chunks), 1)

    def test_render_tool_calls(self):
        calls = [{"id": "1", "function": {"name": "foo", "arguments": "{}"}}]
        rendered = self.mod._render_tool_calls(calls)
        self.assertIn("foo", rendered)

    def test_extra_headers_invalid_json(self):
        import os
        os.environ["CONTEXT_SHRINK_EXTRA_HEADERS"] = "not-json"
        # re-resolve by calling function
        self.assertEqual(self.mod._extra_headers(), {})
        os.environ.pop("CONTEXT_SHRINK_EXTRA_HEADERS", None)

    def test_chat_completions_url(self):
        url = self.mod._chat_completions_url("http://localhost:8000/v1")
        self.assertTrue(url.endswith("/chat/completions"))


if __name__ == "__main__":
    unittest.main()
