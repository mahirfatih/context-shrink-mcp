"""End-to-end test over the real MCP stdio transport.

The unit suite imports the server module directly. This file instead launches
``context_shrink.py`` as a subprocess and speaks JSON-RPC to it on stdin/stdout,
so the handshake, ``tools/list`` and one ``tools/call`` are exercised on the
actual wire path. It still never touches the network: only ``estimate_context``
is called, which is pure arithmetic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

MODULE_PATH = Path(__file__).resolve().parents[2] / "context_shrink.py"
_TIMEOUT_SECONDS = 15


def _spawn() -> subprocess.Popen[str]:
    # Force the dependency-free counter so the round-trip result is deterministic
    # whether or not tiktoken happens to be installed.
    env = {**os.environ, "CONTEXT_SHRINK_TOKENIZER": "heuristic"}
    return subprocess.Popen(
        [sys.executable, str(MODULE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def _send(proc: subprocess.Popen[str], payload: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()


def _read(proc: subprocess.Popen[str], *, timeout: int = _TIMEOUT_SECONDS) -> dict[str, Any]:
    assert proc.stdout is not None
    holder: dict[str, str] = {}

    def _readline() -> None:
        holder["line"] = proc.stdout.readline()  # type: ignore[union-attr]

    thread = threading.Thread(target=_readline, daemon=True)
    thread.start()
    thread.join(timeout)
    if "line" not in holder:
        raise AssertionError("timed out waiting for a message from the MCP server")
    return json.loads(holder["line"])


def _request(proc: subprocess.Popen[str], request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Send a request and return the response with the matching id."""
    _send(proc, {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
    for _ in range(10):  # skip any interleaved notifications
        message = _read(proc)
        if message.get("id") == request_id:
            return message
    raise AssertionError(f"no response for {method!r}")


def test_stdio_handshake_lists_tools_and_calls_one() -> None:
    proc = _spawn()
    try:
        init = _request(
            proc,
            1,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        )
        assert init["result"]["serverInfo"]["name"] == "Context Shrink"

        # The protocol expects an `initialized` notification before normal calls.
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        listing = _request(proc, 2, "tools/list", {})
        names = {tool["name"] for tool in listing["result"]["tools"]}
        assert {"estimate_context", "trim_context", "compact_context", "describe_config"} <= names

        call = _request(
            proc,
            3,
            "tools/call",
            {
                "name": "estimate_context",
                "arguments": {
                    "messages": [{"role": "user", "content": "x" * 40}],
                    "max_context_tokens": 4,
                },
            },
        )
        payload = json.loads(call["result"]["content"][0]["text"])
        assert payload["estimated_context_tokens"] == 10
        assert payload["should_trim"] is True
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            proc.kill()
