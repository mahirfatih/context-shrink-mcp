# Releasing

How a Context Shrink release is cut. The package name is **`context-shrink-mcp`**
and installing it exposes the **`context-shrink`** console script. Everything is
built from `pyproject.toml`; the implementation is the single file
`context-shrink.py`.

## 1. Bump the version

Edit `version` in [`pyproject.toml`](../../pyproject.toml) and add a matching
`## [x.y.z]` section to [`CHANGELOG.md`](../../CHANGELOG.md). PyPI refuses a
version that already exists, so every release needs a new number.

## 2. Run the checks

```bash
./test/test.sh --no-install     # ruff + pytest
cd test/js && npm test          # Node protocol tests
```

Both must be green before building.

## 3. Build

```bash
uv build
```

This writes `dist/context_shrink_mcp-<version>.tar.gz` and
`dist/context_shrink_mcp-<version>-py3-none-any.whl`. `dist/` is gitignored.

## 4. Verify the wheel

Run the packaged console script from the wheel, in an isolated environment:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | uvx --from ./dist/context_shrink_mcp-<version>-py3-none-any.whl context-shrink
```

Expect the three tools: `compact_context`, `estimate_context`, `trim_context`.

## 5. Publish — safely

A published version cannot be deleted or re-uploaded, so rehearse before the real
upload. Three gates, cheapest first:

**a. Dry run** — validates the files and checks the index for duplicates without
uploading anything:

```bash
uv publish --dry-run
```

**b. TestPyPI rehearsal** — the public sandbox at <https://test.pypi.org>. It is a
**separate account system**: register there and create a token; your pypi.org
token does not work. Upload and install from the sandbox to prove the whole path:

```bash
uv publish --publish-url https://test.pypi.org/legacy/ --token "$(cat ~/.config/testpypi-token)"

# install from TestPyPI (deps live on PyPI, hence the extra index)
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple \
  --from context-shrink-mcp context-shrink
```

**c. Real upload** — only once a and b pass. The token is **never** stored in the
repository; keep it in a file outside the checkout:

```bash
uv publish --token "$(cat ~/.config/pypi-token)"
# add --check-url https://pypi.org/simple/ to skip files that already exist
```

To publish without a stored secret, configure PyPI
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) for the GitHub
repository and use an OIDC workflow instead.

## 6. Verify the published package

```bash
pip install context-shrink-mcp                   # the package + `context-shrink` command
uvx --from context-shrink-mcp context-shrink     # from PyPI
```

The project page is <https://pypi.org/project/context-shrink-mcp/>.

## Publishing without PyPI

The same `pyproject.toml` also makes the server runnable straight from GitHub,
so a release can ship before (or instead of) a PyPI upload:

```bash
uvx --from git+https://github.com/mahirfatih/context-shrink-mcp context-shrink
```

Pin a tag with `...context-shrink-mcp@v<version>`. The registered command is
identical either way:

```bash
opencode mcp add context-shrink --global -- uvx --from context-shrink-mcp context-shrink
```
