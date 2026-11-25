#!/usr/bin/env python3
"""Integration tests for context-shrink-mcp: MCP stdio round-trip."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "context-shrink.py"


class IntegrationTests(unittest.TestCase):
    def test_stdio_handshake_and_tools_list(self):
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPT_PATH)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "t", "version": "1"}}}
        proc.stdin.write(json.dumps(init) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        self.assertTrue(line)
        resp = json.loads(line)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "Context Shrink MCP")
        proc.stdin.close()
        proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
