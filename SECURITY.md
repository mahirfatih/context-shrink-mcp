# Security policy

Thanks for helping keep Context Shrink safe. This is a local, offline-first
MCP server (a Python module plus the `mcp` SDK); most attacks are limited to
the environments it runs in, but we still handle every report seriously.

## Reporting a vulnerability

If you find a security issue, please report it by opening a private note on
GitHub or by opening an issue at
[context-shrink-mcp](https://github.com/mahirfatih/context-shrink-mcp/issues)
and marking it as private/an invite-only thread, and we will confirm
receipt and, where it is a real fix, patch the next release.

For anything urgent — a serious vulnerability affecting the public
distribution — email the maintainers so it can be triaged quickly.

## What we treat as a report

- Bugs that let untrusted input (history content, tool output, page text)
  influence control flow beyond the context window — for example via tool
  names, URLs or summary prompt injection.
- Unexpected behaviour in the config/env parsing or in the file/dir modes
  (`_fail` paths, env fallback, default values).
- Dependency or supply-chain issues in `requirements.txt` / `pyproject.toml`
  or the bundled `context-shrink.py`.

## Scope

Only the following are in scope:

- Everything in this repository (`context-shrink.py`, `test/`, `docs/`, …).
- The published `context-shrink-mcp` PyPI package and its tag history.

Not in scope: unrelated third-party repos, or changes you make to your local
install that are not shared here.

## Security notes

- This server is **stdio-only**. It reads `CONTEXT_SHRINK_*` /
  `OMLX_SHRINK_*` / `OPENAI_SHRINK_*` environment variables and, when asked,
  the `CONTEXT_SHRINK_EXTRA_HEADERS` JSON object. Secrets like API keys are
  read but never written to disk, never logged (only header *names* are
  reported by `describe_config`), and never printed by the server.
- `compact_context` may make network calls to the configured `base_url`;
  the server does not ship credentials other than the configured bearer
  token.

## Disclosure

We follow a standard 90-day disclosure window. Expect: a reply within
5–10 working days, an assessment of severity, and a public
disclosure or patch as appropriate. Do not publish a fix before the
window closes unless we coordinate first.
