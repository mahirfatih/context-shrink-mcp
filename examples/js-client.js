// Minimal MCP client for Context Shrink (requires @modelcontextprotocol/sdk).
//
// Node port of `python-client.py`: it starts the server over stdio, lists its
// tools and calls one of them. Run it with node >= 18 after `npm install`:
//
//   npm install
//   node js-client.js [path/to/context-shrink.py]

import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const here = dirname(fileURLToPath(import.meta.url));
const defaultServer = resolve(here, "..", "context-shrink.py");
const serverFile = process.argv[2] ?? defaultServer;

function pythonCommand() {
  if (process.env.CONTEXT_SHRINK_PYTHON) return process.env.CONTEXT_SHRINK_PYTHON;
  const venv = resolve(here, "..", ".venv", "bin", "python3");
  return existsSync(venv) ? venv : "python3";
}

const transport = new StdioClientTransport({
  command: pythonCommand(),
  args: [serverFile],
  // Optional: force the dependency-free counter so the numbers are stable.
  env: { ...process.env, CONTEXT_SHRINK_TOKENIZER: "heuristic" },
});

const client = new Client({ name: "context-shrink-js-client", version: "0.0.0" });
await client.connect(transport);

try {
  const { tools } = await client.listTools();
  console.log("tools:", tools.map((tool) => tool.name));

  const result = await client.callTool({
    name: "estimate_context",
    arguments: {
      messages: [{ role: "user", content: "x".repeat(40) }],
      max_context_tokens: 4,
    },
  });
  console.log("estimate_context ->", JSON.parse(result.content[0].text));
} finally {
  await client.close();
}
