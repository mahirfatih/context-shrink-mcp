# Testing

How the Context Shrink suites are organised, and how to run them. The single
entry point is [`test/test.sh`](../../test/test.sh); the folder guide is
[`test/README.md`](../../test/README.md).

## The suites

| Suite | Path | Runs | Network |
| :--- | :--- | :--- | :--- |
| Unit | [`test/py/context-shrink-tests.py`](../../test/py/context-shrink-tests.py) | always | no |
| STDIO end-to-end | [`test/py/context-shrink-mcp-tests.py`](../../test/py/context-shrink-mcp-tests.py) | always | no |
| Live integration (Python) | [`test/py/context-shrink-live-tests.py`](../../test/py/context-shrink-live-tests.py) | opt-in | yes |
| Integration (Node) | [`test/js/`](../../test/js) | always; model test opt-in | model test only |

The unit suite covers the pure helpers — token estimation, trimming, compaction
splitting and chunking — the tokenizer resolution logic and the environment-variable
parsing. The STDIO suite spawns the server and drives a real JSON-RPC handshake,
`tools/list` and one `tools/call`. Neither touches the network.

## Running

```bash
./test/test.sh                                    # install deps + ruff + pytest
./test/test.sh --lint                             # ruff only
./test/test.sh --no-install                       # skip the pip install step
./test/test.sh --only test/py/context-shrink-tests.py::test_compact_uses_provided_summary
./test/test.sh --only test/py/context-shrink-live-tests.py
```

A bare `./test/test.sh` is what you run while working and before a commit. The
interpreter is the project `.venv` when present, otherwise `python3` (override
with `PYTHON`). Out of the box nothing touches the network; the live suite below
is the only exception, and it is skipped unless you enable it.

## Live tests (opt-in)

The live suite reaches a real OpenAI-compatible endpoint. It is skipped unless
`CONTEXT_SHRINK_LIVE=1` is set **and** the endpoint answers, so the default run
stays offline and green. No key is stored in the repository — it is read from the
environment:

```bash
export CONTEXT_SHRINK_LIVE=1
export CONTEXT_SHRINK_API_KEY=omlx-...          # the endpoint requires a bearer token
export CONTEXT_SHRINK_MODEL=Qwen3.6-35B-A3B-4bit
./test/test.sh --no-install --only test/py/context-shrink-live-tests.py
```

The Python live suite checks a real `compact_context` round-trip, the plan-only
mode (`model=""`) and a clear error for an unknown model.

## Node tests

The Node suite in [`test/js/`](../../test/js) mirrors the Python one through the
official MCP JS SDK over stdio:

```bash
cd test/js
npm install
npm test                                          # protocol tests, offline
CONTEXT_SHRINK_LIVE=1 CONTEXT_SHRINK_API_KEY=omlx-... npm test   # + the model test
```

`tools/list` and `estimate_context` always run and need no network; the
`compact_context` model test is gated by the same `CONTEXT_SHRINK_LIVE` flag.

## CI

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs Ruff, a
`py_compile` check and `pytest`. It is **manual only** — trigger it with
`workflow_dispatch` from the Actions tab. The live and Node suites are not wired
into CI, because neither has a model endpoint.
