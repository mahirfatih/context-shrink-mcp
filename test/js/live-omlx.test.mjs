// Integration tests for the Context Shrink MCP server, driven through the
// official MCP JS SDK over the stdio transport.
//
// The protocol tests (list tools, estimate_context) always run and need no
// network. The model test only runs when a live OpenAI-compatible endpoint is
// reachable and authorised, so it stays green offline. No key is hardcoded:
// it is read from the environment.
//
//   npm install
//   CONTEXT_SHRINK_LIVE=1 CONTEXT_SHRINK_API_KEY=omlx-... npm test

import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const here = dirname(fileURLToPath(import.meta.url));
const serverFile = resolve(here, "..", "..", "context_shrink.py");

const BASE_URL = process.env.CONTEXT_SHRINK_BASE_URL ?? "http://127.0.0.1:8000/v1";
const API_KEY = process.env.CONTEXT_SHRINK_API_KEY ?? "";
const LIVE = process.env.CONTEXT_SHRINK_LIVE === "1";

function pythonCommand() {
  if (process.env.CONTEXT_SHRINK_PYTHON) return process.env.CONTEXT_SHRINK_PYTHON;
  const venv = resolve(here, "..", "..", ".venv", "bin", "python3");
  return existsSync(venv) ? venv : "python3";
}

async function endpointReachable() {
  if (!LIVE) return false;
  try {
    const response = await fetch(`${BASE_URL.replace(/\/$/, "")}/models`, {
      headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {},
      signal: AbortSignal.timeout(3000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function withClient(fn) {
  const transport = new StdioClientTransport({
    command: pythonCommand(),
    args: [serverFile],
    // Deterministic token counts; also proves the server accepts custom env.
    env: { ...process.env, CONTEXT_SHRINK_TOKENIZER: "heuristic" },
  });
  const client = new Client({ name: "context-shrink-js-test", version: "0.0.0" });
  await client.connect(transport);
  try {
    return await fn(client);
  } finally {
    await client.close();
  }
}

function parse(result) {
  return JSON.parse(result.content[0].text);
}

test("lists the four Context Shrink tools", async () => {
  const names = await withClient(async (client) => {
    const { tools } = await client.listTools();
    return tools.map((tool) => tool.name).sort();
  });
  assert.deepEqual(names, [
    "compact_context",
    "describe_config",
    "estimate_context",
    "trim_context",
  ]);
});

test("estimate_context returns a token estimate", async () => {
  const payload = await withClient(async (client) =>
    parse(
      await client.callTool({
        name: "estimate_context",
        arguments: {
          messages: [{ role: "user", content: "x".repeat(40) }],
          max_context_tokens: 4,
        },
      }),
    ),
  );
  assert.equal(payload.estimated_context_tokens, 10);
  assert.equal(payload.should_trim, true);
  assert.equal(payload.tokenizer, "heuristic(chars/4)");
});

const live = await endpointReachable();

test(
  "compact_context summarises with the live model",
  { skip: live ? false : "set CONTEXT_SHRINK_LIVE=1 + CONTEXT_SHRINK_API_KEY and start oMLX" },
  async () => {
    const history = [
      { role: "system", content: "You are a senior engineer. Be concise." },
      { role: "user", content: "We have a file-descriptor leak in our FastAPI service." },
      {
        role: "assistant",
        content: "Check BackgroundTasks, StreamingResponse disconnects and per-request clients.",
      },
      { role: "user", content: "We added finally blocks but the fd count still climbs." },
      {
        role: "assistant",
        content: "Suspect httpx.AsyncClient without aclose() and Uvicorn --limit-concurrency.",
      },
      { role: "user", content: "Root cause was the SSE endpoint leaking on client disconnect." },
      { role: "assistant", content: "Wrap the generator in try/finally and close the client there." },
      { role: "user", content: "Write the final report of what we found." },
    ];
    const payload = await withClient(async (client) =>
      parse(
        await client.callTool({
          name: "compact_context",
          arguments: { messages: history, max_context_tokens: 300, keep_last: 2, force: true },
        }),
      ),
    );
    assert.equal(payload.compacted, true);
    assert.equal(payload.method, "model");
    assert.ok(payload.summary.trim().length > 0);
    assert.equal(payload.kept_count, 2);
  },
);
