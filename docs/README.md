# Documentation

A map of the documents in this repository. The top-level
[`README.md`](../README.md) is the quick tour; start here when you want the
detail behind a tool, a test run or a migration. Each folder answers one
question — read the one that matches what you are doing.

Everything here is written in **English**. The Turkish quick tour is
[`README.tr.md`](../README.tr.md) at the repository root.

## How the folders are organised

| Folder | The question it answers | Written or generated |
| :--- | :--- | :--- |
| [`guides/`](./guides) | How do I move from the old project name | written |
| [`reference/`](./reference) | What endpoint, headers and errors does the server rely on | written |
| [`testing/`](./testing) | How do I verify the server | written |

## Start here

- [`../README.md`](../README.md) — install, the three tools and every parameter.
- [`../README.tr.md`](../README.tr.md) — the same tour in Turkish.

## Guides — how do I work on it

- [`guides/MIGRATION.md`](./guides/MIGRATION.md) — renaming from oMLX Prompt Shrink
  to Context Shrink: file path, tool namespace, repository and environment
  variables.

## Reference — what the server relies on

- [`reference/OPENAI-API-REFERENCE.md`](./reference/OPENAI-API-REFERENCE.md) — the
  OpenAI-compatible endpoint, request/response fields, headers and error shapes
  `compact_context` uses.

## Testing — how do I verify it

- [`testing/TESTING.md`](./testing/TESTING.md) — the suites, the runner and the
  opt-in live tests for Python and Node.

## Also at the repository root

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — development setup, tests and commit
  conventions.
- [`../CHANGELOG.md`](../CHANGELOG.md) — release notes.
