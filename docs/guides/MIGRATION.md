# Migrating from oMLX Prompt Shrink

The project was renamed from **oMLX Prompt Shrink** to the vendor-neutral
**Context Shrink**. The MCP tool *names* are unchanged (`estimate_context`,
`trim_context`, `compact_context`) and the GitHub repository redirects the old
URL, so only a few things need attention.

| What | Before | After |
| :--- | :--- | :--- |
| Server file | `omlx-prompt-shrink.py` | `context_shrink.py` (the module); a `context-shrink.py` shim runs the same file |
| `mcp.json` / `opencode.jsonc` command path | `…/omlx-prompt-shrink.py` | `…/context_shrink.py` |
| Install command | copy the file by hand | `uvx --from context-shrink-mcp context-shrink` (see [`RELEASING.md`](./RELEASING.md)) |
| Tool namespace | `tools.oMLX_Prompt_Shrink.*` | `tools.Context_Shrink.*` |
| Repository | `omlx-prompt-shrink` | `context-shrink-mcp` |
| Environment variables | `OMLX_SHRINK_*` / `OPENAI_SHRINK_*` | `CONTEXT_SHRINK_*` (both old names still work) |

After pulling, re-point your local config at `context_shrink.py` (and refresh the
deployed copy if you keep one), then run `/reload`. Existing `OMLX_SHRINK_*` /
`OPENAI_SHRINK_*` environment settings keep working, so no configuration change is
strictly required for them.
