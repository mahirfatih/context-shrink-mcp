# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]

### Added

- `estimate_context`, `trim_context`, and `compact_context` tools that keep
  OpenAI-compatible models under their context window.
- Optional real tokenizer: `tiktoken` is used when installed (`cl100k_base` by
  default), with a character-based heuristic fallback, controlled by
  `CONTEXT_SHRINK_TOKENIZER`.
- `pytest` unit tests for the pure helpers and the tokenizer resolution logic.
- `test/` folder with a single runner, `test/test.sh` (Ruff + pytest), and
  kebab-case test file names.
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
- `OPENAI-API-REFERENCE.md`: the endpoint, request/response fields, headers and
  error shapes the server relies on.
- Startup hardening: clear messages on missing/outdated `mcp` and Python < 3.10,
  UTF-8 stdio on Windows, tolerant parsing of invalid timeout values, clean exit
  on Ctrl-C / closed pipe.
- `*_LOG_LEVEL` sets the stderr log level (default `INFO`); an invalid name falls
  back to `INFO`.
- Input hardening: out-of-range `max_context_tokens` is clamped to `1…1000000`,
  `keep_last`/`summary_budget_tokens` to `>= 1`, `threshold` to `0…1`, and a
  base URL that is not `http(s)` is logged as a warning.
- End-to-end test over the real STDIO transport (`test/context-shrink-mcp-tests.py`):
  handshake, `tools/list` and one `tools/call`.
- `requirements.txt` pins the single runtime dependency (`mcp>=2.0,<3.0`); the
  same bound is applied in `requirements-dev.txt`.
- Optional `.pre-commit-config.yaml` (Ruff + basic hygiene hooks).

### Changed

- Project name is **Context Shrink**: the server file is `context-shrink.py` and
  the repository is `context-shrink-mcp`. The MCP server display name is
  **Context Shrink**, so tools are grouped under `tools.Context_Shrink.*`; the
  tool names themselves are unchanged.
- `estimate_context` output now includes a `tokenizer` field.
- Positioned as a generic OpenAI-compatible context guard: any
  `/v1/chat/completions` endpoint works (llama.cpp, LM Studio, Ollama, vLLM,
  OpenAI gateways), documented with per-backend base URLs in both READMEs.

### Documentation

- Rewrote `README.md` in a structured, project-style layout and documented the
  three `compact_context` modes.
- Documented the full tool parameter surface (including `threshold`,
  `summary_budget_tokens` and `summary_role`).
- Added a migration guide to both READMEs for the rename (file path, tool
  namespace, repository and environment variables).
- Added a "Common pitfalls" list, the `CONTEXT_SHRINK_LOG_LEVEL` variable and a
  link to the MCP Python SDK to both READMEs.
- Added `examples/python-client.py`, a runnable MCP client (list tools + call
  one), linked from both READMEs.
