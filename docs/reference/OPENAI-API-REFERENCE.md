# OpenAI API Reference (Chat Completions)

A compact reference to the part of the OpenAI API this project uses, plus the
shared behaviour any OpenAI-compatible implementation follows. It exists so the
configuration surface (`*_BASE_URL`, `*_MODEL`, `*_API_KEY`,
`*_EXTRA_HEADERS`) has one written source instead of guesswork.

> Full official reference: <https://developers.openai.com/api/reference/overview>
> Chat Completions method reference:
> <https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create>

## What the OpenAI API is

The OpenAI API is an HTTP API for text generation. You send a list of chat
messages and a model id; you get back the assistant's message. The same wire
format is implemented by many local servers and gateways, which is why one
configuration set works everywhere. For example:

- Ollama
- llama.cpp
- LM Studio
- vLLM
- Text Generation Inference (TGI)
- SGLang
- LocalAI
- OpenRouter
- LiteLLM

The API is organised into endpoint groups. New projects are encouraged to use
the **Responses** API; this server deliberately uses **Chat Completions**
because it is the most widely re-implemented surface. The groups include:

- Responses
- Chat
- Audio
- Images
- Embeddings
- Models
- Administration

## Endpoint used here

```text
POST {base_url}/chat/completions
Content-Type: application/json
Authorization: Bearer <api key>      # sent only when *_API_KEY is non-empty
```

The base URL is configurable. If it does not already end with
`/chat/completions`, that suffix is appended automatically — so both
`http://127.0.0.1:8000/v1` and `http://127.0.0.1:8000/v1/chat/completions`
are accepted.

### Request body (fields this server sends)

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `model` | string | Model id served by the endpoint |
| `messages` | array | `role` + `content` pairs (system/user/assistant) |
| `temperature` | number | Sampling temperature; this server uses `0.2` for summaries |
| `max_tokens` | integer | Upper bound for generated tokens |
| `stream` | boolean | Always `false` — this server waits for the full answer |

Other parameters defined by the API are optional and not sent:

- `top_p`
- `stop`
- `n`
- `seed`
- `response_format`
- `tools`

### Response body (fields this server reads)

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1731500000,
  "model": "qwen2.5-coder",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": { "role": "assistant", "content": "summary text" }
    }
  ],
  "usage": { "prompt_tokens": 1200, "completion_tokens": 200, "total_tokens": 1400 }
}
```

Only `choices[0].message.content` is used; a missing or malformed shape raises
a clear error instead of returning empty text.

### Streaming

With `"stream": true` the response becomes a sequence of Server-Sent Events
(`data: {...}` chunks ending with `data: [DONE]`). This server never streams;
local summarisation runs in short, bounded calls.

## Authentication and headers

- **OpenAI and most providers:** `Authorization: Bearer $API_KEY`.
  Keys are secrets — keep them in environment variables, never in code.
- **Organization / project scoping** (multi-org accounts):

  ```text
  OpenAI-Organization: <org-id>
  OpenAI-Project: <project-id>
  ```

- **Azure OpenAI** does not accept a bearer header. Pass the deployment
  secret as `api-key` via `CONTEXT_SHRINK_EXTRA_HEADERS`:

  ```bash
  export CONTEXT_SHRINK_EXTRA_HEADERS='{"api-key": "azure-secret"}'
  ```

- Any other static header (gateway routing, org ids) can be supplied the same
  way; values are strings in a JSON object.

## Errors

Errors follow the usual HTTP status codes; the body contains an `error` object:

```json
{ "error": { "message": "Invalid API key", "type": "invalid_request_error", "param": null, "code": "invalid_api_key" } }
```

Common cases this server reports as plain messages:

- `401` / `403` — authentication
- `429` — rate limit
- `5xx` — upstream failure
- connection refused / timeout — unreachable endpoint

Response headers worth logging in production:

- `x-request-id` — unique per request, quote it in support tickets
- `openai-processing-ms`, `openai-version`, `openai-organization`
- `x-ratelimit-*` — remaining requests/tokens before throttling

## Minimal curl example

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "qwen2.5-coder",
        "messages": [{"role": "user", "content": "Summarise: the build failed."}],
        "temperature": 0.2,
        "max_tokens": 200
      }'
```

## Compatibility notes per implementation

| Implementation | Quirk to know |
| :--- | :--- |
| OpenAI | Requires `Authorization`; `max_tokens` still accepted (superseded by `max_completion_tokens`) |
| Azure OpenAI | Deployment-scoped base URL; `api-key` header instead of `Authorization`; model = deployment name |
| Ollama | `/v1` endpoint requires no key; some builds need `--compat` or a recent version |
| llama.cpp (`llama-server`) | Model value is your GGUF filename without extension |
| LM Studio | Key not needed locally; model id is the loaded model's |
| vLLM / TGI / SGLang | Model must exactly match the `--served-model-name` |
| OpenRouter / LiteLLM | Accept `Authorization`; can route to cloud and local backends behind one URL |

## Sources

- API overview: <https://developers.openai.com/api/reference/overview>
- Chat Completions create: <https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create>
- Error codes: <https://developers.openai.com/api/docs/guides/error-codes>
- Rate limits: <https://developers.openai.com/api/docs/guides/rate-limits>
