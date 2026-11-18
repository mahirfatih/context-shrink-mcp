# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-15

### Changed

- The default `max_context_tokens` is now **65536** (was `32768`), matching the
  widened oMLX context window. The `*_MAX_CONTEXT_TOKENS` environment variables
  still override it; the tool names and the other defaults (`keep_last = 8`,
  `threshold = 0.8`) are unchanged.

## [1.0.0]

### Added

- `estimate_context`, `trim_context`, and `compact_context` tools that keep
  OpenAI-compatible models under their context window.
- Optional real tokenizer: `tiktoken` is used when installed (`cl100k_base` by
  default), with a character-based heuristic fallback, controlled by
  `CONTEXT_SHRINK_TOKENIZER`.
- `pytest` unit tests for the pure helpers and the tokenizer resolution logic.
- `test/` folder with a single runner, `test/test.sh` (Ruff + pytest), symmetric
  `test/py/` and `test/js/` suites, and kebab-case test file names.
- GitHub Actions CI workflow (Ruff, `py_compile`, `pytest`), **manual dispatch
  only**.
- Turkish README (`README.tr.md`) and a language switcher between both READMEs.
- `CONTRIBUTING.md` and this changelog.
- `CONTEXT_SHRINK_*` environment variables as the canonical names; the legacy
  `OMLX_SHRINK_*` names and the vendor-neutral `OPENAI_SHRINK_*` aliases are
  still accepted, in that precedence order.
- `*_MAX_CONTEXT_TOKENS` overrides the default context budget.
- `*_EXTRA_HEADERS` (a JSON object) sends static HTTP headers for gateways such
  as Azure OpenAI, whose `api-key` header replaces the bearer token.
- Remote/cloud OpenAI-compatible providers, documented with per-provider base
  URLs in both READMEs.
- `docs/reference/OPENAI-API-REFERENCE.md`: the endpoint, request/response
  fields, headers and error shapes the server relies on.
- Startup hardening: clear messages on missing/outdated `mcp` and Python < 3.10,
  UTF-8 stdio on Windows, tolerant parsing of invalid timeout values, clean exit
  on Ctrl-C / closed pipe.
- `*_LOG_LEVEL` sets the stderr log level (default `INFO`); an invalid name falls
  back to `INFO`.
- Input hardening: out-of-range `max_context_tokens` is clamped to `1…1000000`,
  `keep_last`/`summary_budget_tokens` to `>= 1`, `threshold` to `0…1`, and a
  base URL that is not `http(s)` is logged as a warning.
- End-to-end test over the real STDIO transport
  (`test/py/context-shrink-mcp-tests.py`): handshake, `tools/list` and one
  `tools/call`.
- `requirements.txt` pins the single runtime dependency (`mcp>=2.0,<3.0`); the
  same bound is applied in `requirements-dev.txt`.
- Optional `.pre-commit-config.yaml` (Ruff + basic hygiene hooks).
- Opt-in live integration tests (`test/py/context-shrink-live-tests.py`) that
  drive a real `compact_context` round-trip against a local OpenAI-compatible
  endpoint; they skip unless `CONTEXT_SHRINK_LIVE=1` and the endpoint answers,
  and read the API key from the environment rather than the repo.
- Node integration tests (`test/js/`) built on the official MCP JS SDK, covering
  `tools/list` and `estimate_context` offline plus an opt-in live model test.
- `examples/js-client.js`, the Node port of `examples/python-client.py`.

### Changed

- Project name is **Context Shrink**: the server module is `context_shrink.py`
  (with a `context-shrink.py` shim) and the repository is `context-shrink-mcp`.
  The MCP server display name is **Context Shrink**, so tools are grouped under
  `tools.Context_Shrink.*`; the tool names themselves are unchanged.
- Installable as a package: `pyproject.toml` exposes the `context-shrink` console
  script, so the server can be run with `uvx --from context-shrink-mcp
  context-shrink` (or straight from GitHub) instead of copying a file by hand.
  Published to PyPI as [`context-shrink-mcp`](https://pypi.org/project/context-shrink-mcp/),
  also installable with `pip install context-shrink-mcp`.
- `estimate_context` output now includes a `tokenizer` field.
- Positioned as a generic OpenAI-compatible context guard: any
  `/v1/chat/completions` endpoint works (llama.cpp, LM Studio, Ollama, vLLM,
  OpenAI gateways), documented with per-backend base URLs in both READMEs.

### Documentation

- Rewrote `README.md` in a structured, project-style layout and documented the
  three `compact_context` modes.
- Documented the full tool parameter surface (including `threshold`,
  `summary_budget_tokens` and `summary_role`).
- Added a migration guide (`docs/guides/MIGRATION.md`) for the rename (file
  path, tool namespace, repository and environment variables), linked from both
  READMEs.
- Added a `docs/` tree with a [`docs/README.md`](./docs/README.md) map, plus
  `docs/reference/OPENAI-API-REFERENCE.md`, `docs/testing/TESTING.md` and
  `docs/guides/MIGRATION.md`.
- Added a "Common pitfalls" list, the `CONTEXT_SHRINK_LOG_LEVEL` variable and a
  link to the MCP Python SDK to both READMEs.
- Added `examples/python-client.py`, a runnable MCP client (list tools + call
  one), linked from both READMEs.
- Added an "Install (one line)" section to both READMEs and
  [`docs/guides/RELEASING.md`](./docs/guides/RELEASING.md) for versioning,
  building and publishing.
