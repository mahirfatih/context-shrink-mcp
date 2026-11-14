# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional real tokenizer: `tiktoken` is used when installed (`cl100k_base` by
  default), with a character-based heuristic fallback, controlled by
  `OMLX_SHRINK_TOKENIZER`.
- `pytest` unit tests for the pure helpers and the tokenizer resolution logic.
- `test/` folder with a single runner, `test/test.sh` (Ruff + pytest), and
  kebab-case test file names.
- GitHub Actions CI workflow (Ruff, `py_compile`, `pytest`), **manual dispatch
  only**.
- Turkish README (`README.tr.md`) and a language switcher between both READMEs.
- `CONTRIBUTING.md` and this changelog.
- Vendor-neutral `OPENAI_SHRINK_*` environment aliases for every configuration
  variable (the legacy `OMLX_SHRINK_*` names still win when both are set).
- `*_MAX_CONTEXT_TOKENS` overrides the default context budget.
- Startup hardening: clear messages on missing/outdated `mcp` and Python < 3.10,
  UTF-8 stdio on Windows, tolerant parsing of invalid timeout values, clean exit
  on Ctrl-C / closed pipe.

### Changed

- MCP server display name is now **oMLX Prompt Shrink**.
- Renamed `server.py` to `omlx-prompt-shrink.py`.
- `estimate_context` output now includes a `tokenizer` field.
- Positioned as a generic OpenAI-compatible context guard: any
  `/v1/chat/completions` endpoint works (llama.cpp, LM Studio, Ollama, vLLM,
  OpenAI gateways), documented with per-backend base URLs in both READMEs.

### Documentation

- Rewrote `README.md` in a structured, project-style layout and documented the
  three `compact_context` modes.

## [1.0.0]

### Added

- Initial release: `estimate_context`, `trim_context`, and `compact_context`
  tools that keep local OpenAI-compatible models under their context window.
