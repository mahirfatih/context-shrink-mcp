# Contributing

Thanks for your interest in **Context Shrink**. This is a small, dependency-light
MCP server, so the contribution surface is intentionally narrow.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # mcp + pytest + ruff + tiktoken
```

The runtime dependency (`mcp`) alone is enough to run the server; it is pinned
in `requirements.txt`. Optional local git hooks (Ruff + basic hygiene) live in
`.pre-commit-config.yaml`: `pip install pre-commit && pre-commit install`.

## Running the checks

```bash
./test/test.sh              # install dev deps, then ruff + pytest
./test/test.sh --lint       # ruff only
./test/test.sh --no-install # skip the pip install step
```

The runner and both checks run in CI (`.github/workflows/ci.yml`). CI is
**manual only** (`workflow_dispatch`) — start it from the Actions tab.

## The server

Everything ships in a single module, `context_shrink.py`. Keep it that way:

- Standard library only at runtime, except the required `mcp` SDK.
- `tiktoken` must stay **optional** — import it defensively and fall back to the
  character heuristic when it is missing or fails to load.
- New behaviour belongs in a pure helper (easy to unit-test) with the MCP tool
  acting as a thin JSON wrapper.

The importable module is what `pyproject.toml` packages and what the
`context-shrink` console script calls. The hyphenated `context-shrink.py` at the
root is only a four-line shim that runs the same module for existing setups; keep
it in sync by changing nothing but the module.

## Tests

Add tests under `test/py/`. The server module is imported by path with a fresh
module instance per test, so the lazily cached tokenizer resets automatically.
Never call the network in a test — mock the tokenizer or the summariser endpoint
instead.

`test/py/context-shrink-tests.py` holds the unit tests and the shared fixtures;
`test/py/context-shrink-mcp-tests.py` spawns the server and exercises the real
STDIO transport (handshake, `tools/list`, one `tools/call`), still without the
network. The full suite map, the flags and the opt-in live tests are in
[`docs/testing/TESTING.md`](./docs/testing/TESTING.md).

### File names

File names follow one rule: **scripts and data files are kebab-case**, with the
Python **test files carrying a `-tests` suffix** (for example
`context-shrink-tests.py`). A hyphen is not legal in an importable module
name, so `pytest.ini` pins `python_files = *-tests.py`; pytest imports the file
by path. A name fixed by a tool — `pytest.ini` — keeps its name; the shared
fixtures live at the top of `context-shrink-tests.py`.

Run a single file or test while iterating:

```bash
./test/test.sh --only test/py/context-shrink-tests.py
./test/test.sh --only test/py/context-shrink-tests.py::test_compact_uses_provided_summary
```

## Commit conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short imperative summary>
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. Keep
each commit to one logical change.

## Releasing

A release bumps `version` in `pyproject.toml`, builds with `uv build` and
publishes with `uv publish`. The full checklist — including the from-GitHub
alternative that needs no PyPI upload — is in
[`docs/guides/RELEASING.md`](./docs/guides/RELEASING.md).

## Syncing a local OpenCode install

If you run the server from OpenCode, keep the deployed copy in step with the
repository (for example by copying or symlinking the file):

```bash
cp context_shrink.py ~/.config/opencode/mcp/context_shrink.py
```

OpenCode reloads MCP servers when configuration changes; run `/reload` in the TUI
if a code-only change does not take effect.
