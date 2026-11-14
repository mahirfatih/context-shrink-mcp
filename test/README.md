# Test

Local test runner for Context Shrink. Everything is one command; there is no
device matrix and nothing to install beyond the dev dependencies.

Strategy and conventions live in [`CONTRIBUTING.md`](../CONTRIBUTING.md); the
suite itself is described in the [README](../README.md#-testing--ci).

## Contents

| Path | Purpose |
| :--- | :--- |
| [`test.sh`](./test.sh) | Single test runner. Installs dev deps, runs Ruff, then pytest. |
| [`context-shrink-tests.py`](./context-shrink-tests.py) | Unit tests for the pure helpers and the tokenizer resolution logic; also defines the shared `shrink` fixture and the autouse heuristic token counter. |
| [`context-shrink-mcp-tests.py`](./context-shrink-mcp-tests.py) | End-to-end test: spawns the server and drives a JSON-RPC handshake, `tools/list` and one `tools/call` over STDIO. No network. |
| [`context-shrink-live-tests.py`](./context-shrink-live-tests.py) | Opt-in live tests: a real `compact_context` round-trip against a local OpenAI-compatible endpoint (oMLX). Skipped unless enabled. |
| [`js/`](./js) | Node integration tests using the official MCP JS SDK (stdio transport). Protocol tests always run; the model test is opt-in. |

## Quick start

```bash
./test/test.sh                                   # install deps + ruff + pytest
./test/test.sh --lint                            # ruff only
./test/test.sh --no-install                      # skip the pip install step
./test/test.sh --only test/context-shrink-tests.py::test_compact_uses_provided_summary
./test/test.sh --help                            # full flag list
```

A bare `./test/test.sh` is what you run while working and before a commit. The
interpreter is the project `.venv` when present, otherwise `python3` (override
with `PYTHON`). By default tests never touch the network: the optional tokenizer
is faked and the summariser endpoint is never called. The live suite below is the
only exception, and it is skipped unless you enable it.

## Live tests (opt-in)

`context-shrink-live-tests.py` reaches a real endpoint. It is skipped unless
`CONTEXT_SHRINK_LIVE=1` is set *and* the endpoint answers, so the default run
stays offline and green. No key is stored in the repo — it is read from the
environment:

```bash
export CONTEXT_SHRINK_LIVE=1
export CONTEXT_SHRINK_API_KEY=omlx-...          # oMLX requires a bearer token
export CONTEXT_SHRINK_MODEL=Qwen3.6-35B-A3B-4bit
./test/test.sh --no-install --only test/context-shrink-live-tests.py
```

The Node suite in [`js/`](./js) mirrors this: `npm install && npm test` runs the
protocol tests offline, and the model test only when `CONTEXT_SHRINK_LIVE=1`.

## Outputs

pytest writes its cache to `.pytest_cache/` (gitignored). Ruff writes to
`.ruff_cache/` (gitignored). The Node suite installs into `js/node_modules/`
(gitignored). Nothing else is produced.

## Further reading

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — setup, tests and commit conventions
- [`README.md`](../README.md) — install, tools and the three compaction modes
