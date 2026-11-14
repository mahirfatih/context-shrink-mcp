"""Live integration tests against a real OpenAI-compatible endpoint (oMLX).

Unlike the other suites, these tests do reach the network. They are skipped
unless you opt in, so the default ``pytest`` run stays offline and green:

    export CONTEXT_SHRINK_LIVE=1
    export CONTEXT_SHRINK_API_KEY=omlx-...          # oMLX requires a bearer token
    # optional overrides:
    export CONTEXT_SHRINK_BASE_URL=http://127.0.0.1:8000/v1
    export CONTEXT_SHRINK_MODEL=Qwen3.6-35B-A3B-4bit

Then run just this file:

    ./test/test.sh --no-install --only test/context-shrink-live-tests.py

The API key is read from the environment and is never written into this file.
The whole module skips when ``CONTEXT_SHRINK_LIVE`` is unset or the endpoint is
unreachable or unauthorised.
"""

from __future__ import annotations

import importlib.util
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "context-shrink.py"

BASE_URL = os.environ.get("CONTEXT_SHRINK_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("CONTEXT_SHRINK_API_KEY", "")
# Not read here; the server module reads CONTEXT_SHRINK_MODEL itself. Kept as a
# readable default for the skip reason below.
MODEL = os.environ.get("CONTEXT_SHRINK_MODEL", "Qwen3.6-35B-A3B-4bit")


def _reachable() -> bool:
    request = urllib.request.Request(
        BASE_URL.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


pytestmark = pytest.mark.skipif(
    os.environ.get("CONTEXT_SHRINK_LIVE") != "1" or not _reachable(),
    reason=(
        "live endpoint disabled/unreachable: set CONTEXT_SHRINK_LIVE=1 and "
        "CONTEXT_SHRINK_API_KEY (e.g. model " + MODEL + ") to run against a real server"
    ),
)


def _load_module() -> ModuleType:
    """Import the server fresh so it reads the current environment."""
    spec = importlib.util.spec_from_file_location("context_shrink_live", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def shrink() -> ModuleType:
    return _load_module()


def _history() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "You are a senior engineer. Be concise."},
        {"role": "user", "content": "We have a file-descriptor leak in our FastAPI service."},
        {
            "role": "assistant",
            "content": "Check BackgroundTasks, StreamingResponse disconnects and per-request clients.",
        },
        {"role": "user", "content": "We added finally blocks but the fd count still climbs."},
        {
            "role": "assistant",
            "content": "Suspect httpx.AsyncClient without aclose() and Uvicorn --limit-concurrency.",
        },
        {"role": "user", "content": "Root cause was the SSE endpoint leaking on client disconnect."},
        {
            "role": "assistant",
            "content": "Wrap the generator in try/finally and close the client there.",
        },
        {"role": "user", "content": "Write the final report of what we found."},
    ]


def test_live_compact_summarises_with_the_model(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.compact_context(_history(), max_context_tokens=300, keep_last=2, force=True)
    )
    assert payload["compacted"] is True
    assert payload["method"] == "model"
    assert payload["summary"].strip()
    assert payload["summarized_count"] >= 1
    assert payload["kept_count"] == 2
    assert any("summary of earlier conversation" in m["content"] for m in payload["messages"])


def test_live_model_empty_forces_plan_only(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.compact_context(
            _history(), max_context_tokens=300, keep_last=2, force=True, model=""
        )
    )
    assert payload["compacted"] is False
    assert payload.get("needs_summary") is True
    assert "summary_prompt" in payload


def test_live_unknown_model_reports_a_clear_error(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.compact_context(
            _history(),
            max_context_tokens=300,
            keep_last=2,
            force=True,
            model="definitely-not-a-model",
        )
    )
    assert payload["compacted"] is False
    assert payload.get("needs_summary") is True
    assert "error" in payload and "404" in payload["error"]
