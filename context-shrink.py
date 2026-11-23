#!/usr/bin/env python3
"""Generic OpenAI-compatible context guard MCP server.

Works with any OpenAI-compatible chat-completions endpoint: oMLX, llama.cpp,
LM Studio, Ollama, vLLM, KoboldCpp, the official OpenAI API, or any gateway.
It keeps requests under their context window, with three levels of
intervention:

* ``estimate_context`` - measure only, no changes.
* ``trim_context``     - drop the oldest messages.
* ``compact_context``  - replace the oldest messages with a summary.

The server is deliberately dependency-light: the MCP SDK plus the standard
library. ``compact_context`` can summarise with the model at
``base_url``/``model``, or accept a summary you already produced.

Configuration comes from environment variables. The canonical ``CONTEXT_SHRINK_*``
names are accepted first, then the legacy ``OMLX_SHRINK_*`` ones, then the
``OPENAI_SHRINK_*`` aliases:

* ``*_BASE_URL``      - chat-completions endpoint (default
  ``http://127.0.0.1:8000/v1``)
* ``*_MODEL``         - model id for summarisation (empty = plan-only mode)
* ``*_API_KEY``       - bearer token, sent only when non-empty
* ``*_TIMEOUT``       - request timeout in seconds (default 180)
* ``*_TOKENIZER``     - ``auto`` (default), a tiktoken encoding name, or
  ``heuristic``/``off``/``none``/``chars``
* ``*_MAX_CONTEXT_TOKENS`` - default context budget (default 32768)
* ``*_EXTRA_HEADERS`` - extra HTTP headers as a JSON object, for gateways that
  need them (Azure OpenAI's ``api-key`` header, org ids, ...)
* ``*_LOG_LEVEL`` - stderr log level name (default ``INFO``)

The context budget is resolved once at startup, first match wins:

1. the ``max_context_tokens`` argument of a tool call,
2. the ``--max-context`` command-line flag (``context-shrink --max-context 65536``),
3. the ``*_MAX_CONTEXT_TOKENS`` environment variable,
4. the built-in default, ``32768``.

The default is deliberately small: when the window is unknown, trimming too
early is harmless, while assuming too much makes every request fail.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, NoReturn


def _fail(message: str) -> NoReturn:
    """Write a plain, actionable message to stderr and exit non-zero."""
    sys.stderr.write(f"context-shrink: {message}\n")
    raise SystemExit(1)


# UTF-8 stdio: on Windows the console default (cp1252, cp936, ...) mangles the
# non-ASCII message content that flows over the JSON-RPC channel, and some
# MCP clients read stdout strictly. Reconfigure both streams when possible.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):  # pragma: no cover - exotic stdio wrappers
            pass

if sys.version_info < (3, 10):  # noqa: UP036 - runtime guard for wrong interpreters
    _fail(
        f"requires Python 3.10 or newer (found {sys.version_info.major}."
        f"{sys.version_info.minor}); point your MCP client at a newer "
        "interpreter (see README Installation)"
    )

try:
    from mcp.server import MCPServer
except ImportError as error:  # missing package, or mcp 1.x without MCPServer
    _fail(
        "the 'mcp' package is missing or too old; install or upgrade it with "
        "`pip install -U 'mcp>=2.0'` (the MCPServer class exists from 2.0 on). "
        f"Underlying error: {error}"
    )

try:  # optional: a real tokenizer is used when available, otherwise a heuristic
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

def _env_value(*names: str, default: str) -> str:
    """Return the first non-empty environment variable among ``names``."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def _resolve_log_level() -> tuple[int, str]:
    """Return ``(level, invalid_name)`` from ``CONTEXT_SHRINK_LOG_LEVEL``."""
    raw = _env_value(
        "CONTEXT_SHRINK_LOG_LEVEL",
        "OMLX_SHRINK_LOG_LEVEL",
        "OPENAI_SHRINK_LOG_LEVEL",
        default="INFO",
    )
    level = logging.getLevelName(raw.upper())
    if isinstance(level, int):
        return level, ""
    return logging.INFO, raw


_log_level, _bad_log_level = _resolve_log_level()
logger = logging.getLogger("context-shrink")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(_log_level)
if _bad_log_level:
    logger.warning("*_LOG_LEVEL=%r is not a valid level; using INFO", _bad_log_level)


def _env_float(*names: str, default: float) -> float:
    """Read a float environment variable, falling back on garbage input."""
    raw = _env_value(*names, default="")
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning("%s=%r is not a number; using %s", names[0], raw, default)
        return default
    return max(1.0, value)


def _env_int(*names: str, default: int) -> int:
    """Read an int environment variable, falling back on garbage input."""
    raw = _env_value(*names, default="")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is not an integer; using %s", names[0], raw, default)
        return default
    return max(1, value)


# A budget above this is almost certainly a unit mistake, and a huge one only
# wastes memory; clamp caller- and env-supplied values to it.
MAX_CONTEXT_TOKENS_CEILING = 1_000_000


def _coerce_budget(value: int, *, ceiling: int = MAX_CONTEXT_TOKENS_CEILING) -> int:
    """Clamp a caller-supplied context budget to a sane positive range."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        logger.warning("max_context_tokens=%r is not an integer; using %d", value, MAX_CONTEXT_TOKENS)
        return MAX_CONTEXT_TOKENS
    if number < 1:
        logger.warning("max_context_tokens=%r is not positive; using 1", value)
        return 1
    if number > ceiling:
        logger.warning("max_context_tokens=%r is too large; capping at %d", value, ceiling)
        return ceiling
    return number


def _extra_headers() -> dict[str, str]:
    """Optional extra HTTP headers as a JSON object (for gateways such as Azure).

    Read from the first non-empty of ``CONTEXT_SHRINK_EXTRA_HEADERS``,
    ``OMLX_SHRINK_EXTRA_HEADERS`` or ``OPENAI_SHRINK_EXTRA_HEADERS``.

    Example::

        CONTEXT_SHRINK_EXTRA_HEADERS='{"api-key": "azure-secret"}'
    """
    raw = _env_value(
        "CONTEXT_SHRINK_EXTRA_HEADERS",
        "OMLX_SHRINK_EXTRA_HEADERS",
        "OPENAI_SHRINK_EXTRA_HEADERS",
        default="",
    )
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        logger.warning("*_EXTRA_HEADERS is not valid JSON; ignoring it")
        return {}
    if not isinstance(parsed, dict):
        logger.warning("*_EXTRA_HEADERS must be a JSON object; ignoring it")
        return {}
    return {str(key): str(value) for key, value in parsed.items()}


# Canonical names are CONTEXT_SHRINK_*; the legacy OMLX_SHRINK_* names and the
# vendor-neutral OPENAI_SHRINK_* aliases are still accepted, in that order.
DEFAULT_BASE_URL = _env_value(
    "CONTEXT_SHRINK_BASE_URL",
    "OMLX_SHRINK_BASE_URL",
    "OPENAI_SHRINK_BASE_URL",
    default="http://127.0.0.1:8000/v1",
)
DEFAULT_API_KEY = _env_value(
    "CONTEXT_SHRINK_API_KEY",
    "OMLX_SHRINK_API_KEY",
    "OPENAI_SHRINK_API_KEY",
    default="",
)
DEFAULT_MODEL = _env_value(
    "CONTEXT_SHRINK_MODEL",
    "OMLX_SHRINK_MODEL",
    "OPENAI_SHRINK_MODEL",
    default="",
)
SUMMARY_TIMEOUT_SECONDS = _env_float(
    "CONTEXT_SHRINK_TIMEOUT",
    "OMLX_SHRINK_TIMEOUT",
    "OPENAI_SHRINK_TIMEOUT",
    default=180.0,
)

DEFAULT_MAX_CONTEXT_TOKENS = 32768


def _cli_max_context(argv: list[str]) -> int | None:
    """Return the ``--max-context`` value from argv, or ``None`` when absent.

    Unknown arguments are ignored so an MCP client can pass its own flags
    without breaking startup, and abbreviations are disabled so unrelated
    client arguments are never mistaken for this flag.
    """
    parser = argparse.ArgumentParser(
        prog="context-shrink",
        description="OpenAI-compatible context guard MCP server.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--max-context",
        type=int,
        default=None,
        metavar="N",
        help=(
            "default context window in tokens; overrides the environment "
            f"variable; without either, {DEFAULT_MAX_CONTEXT_TOKENS} is used"
        ),
    )
    parsed, _unknown = parser.parse_known_args(argv)
    return parsed.max_context


CLI_MAX_CONTEXT = _cli_max_context(sys.argv[1:])

_ENV_MAX_CONTEXT_RAW = _env_value(
    "CONTEXT_SHRINK_MAX_CONTEXT_TOKENS",
    "OMLX_SHRINK_MAX_CONTEXT_TOKENS",
    "OPENAI_SHRINK_MAX_CONTEXT_TOKENS",
    default="",
)

if CLI_MAX_CONTEXT is not None:
    MAX_CONTEXT_TOKENS = max(1, CLI_MAX_CONTEXT)
    MAX_CONTEXT_SOURCE = "cli"
elif _ENV_MAX_CONTEXT_RAW:
    MAX_CONTEXT_TOKENS = _env_int(
        "CONTEXT_SHRINK_MAX_CONTEXT_TOKENS",
        "OMLX_SHRINK_MAX_CONTEXT_TOKENS",
        "OPENAI_SHRINK_MAX_CONTEXT_TOKENS",
        default=DEFAULT_MAX_CONTEXT_TOKENS,
    )
    MAX_CONTEXT_SOURCE = "env"
else:
    MAX_CONTEXT_TOKENS = DEFAULT_MAX_CONTEXT_TOKENS
    MAX_CONTEXT_SOURCE = "default"

DEFAULT_KEEP_LAST = 8
DEFAULT_THRESHOLD = 0.8
DEFAULT_SUMMARY_BUDGET_TOKENS = 512

SUMMARY_INSTRUCTIONS = (
    "You compact conversation history. Write a dense summary "
    "that preserves: the user's goal, every decision and constraint, file paths "
    "and code identifiers, commands that were run and their key results, and any "
    "unresolved question or next step. Omit greetings, restated instructions and "
    "redundant detail. Write plain prose in the same language as the conversation. "
    "Do not add a preamble such as 'Here is a summary'."
)

_HEURISTIC_LABEL = "heuristic(chars/4)"
_tokenizer_cache: tuple[Any, str] | None = None


def _resolve_tokenizer() -> tuple[Any, str]:
    """Return ``(encode_callable_or_None, label)``, resolved once and cached.

    ``CONTEXT_SHRINK_TOKENIZER`` (aliases: ``OMLX_SHRINK_TOKENIZER``,
    ``OPENAI_SHRINK_TOKENIZER``) controls the choice:

    * ``auto`` (default) - use ``tiktoken``'s ``cl100k_base`` when installed;
      otherwise fall back to the character heuristic.
    * a tiktoken encoding name (for example ``o200k_base``) - use that encoding.
    * ``heuristic`` / ``off`` / ``none`` / ``chars`` - always use the heuristic.
    """
    global _tokenizer_cache
    if _tokenizer_cache is not None:
        return _tokenizer_cache

    setting = _env_value(
        "CONTEXT_SHRINK_TOKENIZER",
        "OMLX_SHRINK_TOKENIZER",
        "OPENAI_SHRINK_TOKENIZER",
        default="auto",
    ).lower()
    fallback: tuple[Any, str] = (None, _HEURISTIC_LABEL)
    if setting in {"heuristic", "off", "none", "chars", ""}:
        _tokenizer_cache = fallback
        return _tokenizer_cache
    if tiktoken is None:
        if setting != "auto":
            logger.warning(
                "*_TOKENIZER=%r requested but tiktoken is not installed; "
                "using %s",
                setting,
                _HEURISTIC_LABEL,
            )
        _tokenizer_cache = fallback
        return _tokenizer_cache

    encoding_name = "cl100k_base" if setting == "auto" else setting
    try:
        encoder = tiktoken.get_encoding(encoding_name)
    except Exception as error:  # network/IO failure or unknown encoding
        logger.warning("tokenizer %r unavailable (%s); using %s", encoding_name, error, _HEURISTIC_LABEL)
        _tokenizer_cache = fallback
        return _tokenizer_cache

    _tokenizer_cache = (encoder.encode, f"tiktoken:{encoding_name}")
    return _tokenizer_cache


server = MCPServer("Context Shrink")


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    encode, _ = _resolve_tokenizer()
    if encode is not None:
        text = "\n".join(
            _content_to_text(message.get("content", ""))
            for message in messages
            if isinstance(message, dict)
        )
        try:
            return max(1, len(encode(text)))
        except Exception as error:  # pragma: no cover - defensive
            logger.warning("tokenizer failed (%s); using %s", error, _HEURISTIC_LABEL)
    chars = 0
    for message in messages:
        content = message.get("content", "") if isinstance(message, dict) else ""
        chars += len(_content_to_text(content))
    return max(1, int(math.ceil(chars / 4)))


def _estimate_capped_tokens(
    messages: list[dict[str, Any]],
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> int:
    return min(_estimate_tokens(messages), max_context_tokens)


def _trim_messages(
    messages: list[dict[str, Any]],
    keep_last: int = DEFAULT_KEEP_LAST,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> list[dict[str, Any]]:
    result = list(messages)
    while len(result) > keep_last and _estimate_tokens(result) > max_context_tokens:
        result = result[1:]
    return result


def _split_for_compaction(
    messages: list[dict[str, Any]],
    keep_last: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Split into (leading system, to summarise, to keep verbatim)."""
    keep_last = max(1, keep_last)
    leading: list[dict[str, Any]] = []
    index = 0
    total = len(messages)
    while index < total and isinstance(messages[index], dict) and messages[index].get("role") == "system":
        leading.append(messages[index])
        index += 1
    rest = list(messages[index:])
    if len(rest) <= keep_last:
        return leading, [], rest
    return leading, rest[:-keep_last], rest[-keep_last:]


def _assemble_compaction(
    leading: list[dict[str, Any]],
    summary: str,
    keep: list[dict[str, Any]],
    summary_role: str = "system",
) -> list[dict[str, Any]]:
    note = {
        "role": summary_role,
        "content": "[summary of earlier conversation]\n" + summary.strip() + "\n[end of summary]",
    }
    return [*leading, note, *keep]


def _render_tool_calls(tool_calls: Any) -> str:
    """Render assistant ``tool_calls`` as compact text for the summariser.

    Tool calls are structural: dropping them from the summary makes the model
    see a half-finished tool exchange and later emit malformed tool calls
    ("unrecoverable tool call").  Keep the name, arguments and id in the
    rendered text so the summariser can describe the call.
    """
    if not isinstance(tool_calls, list):
        return ""
    parts: list[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function") if isinstance(call.get("function"), dict) else {}
        name = function.get("name") or "?"
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            try:
                arguments = json.dumps(arguments, ensure_ascii=False)
            except (TypeError, ValueError):
                arguments = str(arguments)
        call_id = call.get("id")
        suffix = f" (id={call_id})" if call_id else ""
        parts.append(f"{name}({arguments}){suffix}")
    return " -> ".join(parts)


def _render_messages_for_model(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "?") if isinstance(message, dict) else "?"
        content = message.get("content", "") if isinstance(message, dict) else ""
        text = _content_to_text(content)
        tool_calls = _render_tool_calls(message.get("tool_calls")) if isinstance(message, dict) else ""
        if tool_calls:
            marker = f"[tool_calls: {tool_calls}]"
            text = f"{text} {marker}".strip() if text else marker
        tool_call_id = message.get("tool_call_id") if isinstance(message, dict) else None
        if tool_call_id:
            text = f"(re: {tool_call_id}) {text}".strip()
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def _chunk_messages(
    messages: list[dict[str, Any]],
    chunk_budget_tokens: int,
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for message in messages:
        candidate = [*current, message]
        if current and _estimate_tokens(candidate) > chunk_budget_tokens:
            chunks.append(current)
            current = [message]
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _chat_completions_url(base_url: str) -> str:
    """Normalize a base URL to its ``/chat/completions`` endpoint."""
    url = base_url.strip().rstrip("/")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        logger.warning("base URL %r does not look like an http(s) URL", base_url)
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    return url


def _call_chat_completions(
    prompt_messages: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    model: str,
    max_tokens: int,
) -> str:
    url = _chat_completions_url(base_url)
    payload = {
        "model": model,
        "messages": prompt_messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {"Content-Type": "application/json", **_extra_headers()}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=SUMMARY_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"summarizer endpoint returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"summarizer endpoint unreachable: {error.reason}") from error
    try:
        return str(body["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as error:
        # oMLX / some servers return the full prompt when it exceeds the output
        # limit instead of a clean error — fall back to returning what we got.
        if "choices" in body and isinstance(body["choices"], list) and len(body["choices"]) > 0:
            content = body["choices"][0].get("message", {}).get("content", "")
            if content:
                return str(content).strip()
        raise RuntimeError(f"unexpected summarizer response: {json.dumps(body)[:500]}") from error


def _summarize(
    to_summarize: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    model: str,
    max_context_tokens: int,
    summary_budget_tokens: int,
) -> str:
    # Chunk budget is based on the *summarized portion* size, not the full context
    # window. When 51 K tokens are summarised a 64 K chunk budget means one huge
    # chunk that overflows the model's output limit.  Use a fixed per-chunk cap
    # (4096 tokens) so the summariser never receives more than it can handle.
    chunk_budget = 4096
    chunks = _chunk_messages(to_summarize, chunk_budget)
    summaries: list[str] = []
    for chunk in chunks:
        prompt = [
            {"role": "system", "content": SUMMARY_INSTRUCTIONS},
            {"role": "user", "content": _render_messages_for_model(chunk)},
        ]
        summaries.append(
            _call_chat_completions(prompt, base_url, api_key, model, summary_budget_tokens)
        )
    if len(summaries) == 1:
        return summaries[0]
    merged = "\n\n".join(summaries)
    merge_prompt = [
        {
            "role": "system",
            "content": "Merge these partial summaries into one, without losing facts or repeating.",
        },
        {"role": "user", "content": merged},
    ]
    try:
        return _call_chat_completions(
            merge_prompt, base_url, api_key, model, summary_budget_tokens
        )
    except RuntimeError:
        return merged


@server.tool()
def estimate_context(
    messages: list[dict[str, Any]],
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> str:
    """Estimate the current context size in tokens before sending it to the model.

    Example call::

        estimate_context({
            "messages": [{"role": "user", "content": "hello"}],
            "max_context_tokens": 32768,
        })
    """
    max_context_tokens = _coerce_budget(max_context_tokens)
    estimated = _estimate_tokens(messages)
    _, tokenizer = _resolve_tokenizer()
    return json.dumps(
        {
            "estimated_context_tokens": estimated,
            "max_context_tokens": max_context_tokens,
            "remaining_tokens": max_context_tokens - estimated,
            "should_trim": estimated > max_context_tokens,
            "message_count": len(messages),
            "tokenizer": tokenizer,
        },
        ensure_ascii=False,
    )


@server.tool()
def trim_context(
    messages: list[dict[str, Any]],
    keep_last: int = DEFAULT_KEEP_LAST,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> str:
    """Trim the oldest messages when the estimated context exceeds the model limit.

    Example call::

        trim_context({
            "messages": [...],
            "keep_last": 8,
            "max_context_tokens": 32768,
        })
    """
    max_context_tokens = _coerce_budget(max_context_tokens)
    keep_last = max(1, int(keep_last))
    trimmed = _trim_messages(messages, keep_last=keep_last, max_context_tokens=max_context_tokens)
    return json.dumps(
        {
            "messages": trimmed,
            "original_count": len(messages),
            "trimmed_count": len(trimmed),
            "estimated_context_tokens": _estimate_capped_tokens(trimmed, max_context_tokens),
        },
        ensure_ascii=False,
    )


@server.tool()
def compact_context(
    messages: list[dict[str, Any]],
    keep_last: int = DEFAULT_KEEP_LAST,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
    threshold: float = DEFAULT_THRESHOLD,
    summary: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    summary_budget_tokens: int = DEFAULT_SUMMARY_BUDGET_TOKENS,
    summary_role: str = "system",
    force: bool = False,
) -> str:
    """Replace the oldest messages with a summary instead of dropping them.

    The summary comes from ``summary`` when given, otherwise from the local model
    via ``model``/``base_url`` (or the CONTEXT_SHRINK_MODEL / CONTEXT_SHRINK_BASE_URL
    environment variables). With neither, the tool returns a ``needs_summary``
    plan plus the exact prompt, and no message content is echoed back.

    Example call::

        compact_context({
            "messages": [...],
            "keep_last": 8,
            "threshold": 0.8,
            "summary": "…",  # omit to summarise with the model
        })
    """
    max_context_tokens = _coerce_budget(max_context_tokens)
    keep_last = max(1, int(keep_last))
    summary_budget_tokens = max(1, int(summary_budget_tokens))
    threshold = min(max(float(threshold), 0.0), 1.0)
    tokens_before = _estimate_tokens(messages)
    threshold_tokens = int(max_context_tokens * threshold)
    leading, to_summarize, keep = _split_for_compaction(messages, keep_last)
    base = {
        "estimated_context_tokens": tokens_before,
        "max_context_tokens": max_context_tokens,
        "threshold_tokens": threshold_tokens,
        "message_count": len(messages),
    }

    if not to_summarize:
        return json.dumps({**base, "compacted": False, "reason": "nothing_to_compact"}, ensure_ascii=False)

    if not force and tokens_before <= threshold_tokens:
        return json.dumps({**base, "compacted": False, "reason": "within_threshold"}, ensure_ascii=False)

    method = "provided"
    used_summary = summary
    if used_summary is None:
        # model="" forces the plan-only step even when the environment sets a model
        resolved_model = model if model is not None else DEFAULT_MODEL
        if not resolved_model:
            return json.dumps(
                {
                    **base,
                    "compacted": False,
                    "needs_summary": True,
                    "to_summarize_count": len(to_summarize),
                    "keep_count": len(keep),
                    "summary_budget_tokens": summary_budget_tokens,
                    "summary_prompt": SUMMARY_INSTRUCTIONS,
                    "retry_hint": (
                        "Summarise the oldest part of your context yourself, then call "
                        "compact_context again with summary=<that text>, the same messages, "
                        "keep_last and summary_role."
                    ),
                },
                ensure_ascii=False,
            )
        try:
            used_summary = _summarize(
                to_summarize,
                base_url or DEFAULT_BASE_URL,
                api_key if api_key is not None else DEFAULT_API_KEY,
                resolved_model,
                max_context_tokens,
                summary_budget_tokens,
            )
            method = "model"
        except RuntimeError as error:
            logger.warning("compaction summariser failed: %s", error)
            return json.dumps(
                {
                    **base,
                    "compacted": False,
                    "needs_summary": True,
                    "error": str(error),
                    "to_summarize_count": len(to_summarize),
                    "keep_count": len(keep),
                    "summary_prompt": SUMMARY_INSTRUCTIONS,
                    "retry_hint": (
                        "The summariser call failed. Summarise the oldest part of your "
                        "context yourself, then call compact_context again with "
                        "summary=<that text>."
                    ),
                },
                ensure_ascii=False,
            )

    compacted = _assemble_compaction(leading, used_summary, keep, summary_role=summary_role)
    return json.dumps(
        {
            **base,
            "compacted": True,
            "method": method,
            "messages": compacted,
            "summary": used_summary,
            "summarized_count": len(to_summarize),
            "kept_count": len(keep),
            "estimated_context_tokens_after": _estimate_tokens(compacted),
        },
        ensure_ascii=False,
    )


@server.tool()
def describe_config() -> str:
    """Report the resolved configuration without changing anything.

    Shows the context window every tool will use and where it came from:
    ``cli`` (``--max-context``), ``env`` (``*_MAX_CONTEXT_TOKENS``), or
    ``default`` (``32768``). Extra header names are listed, never their values.
    """
    _, tokenizer = _resolve_tokenizer()
    return json.dumps(
        {
            "base_url": DEFAULT_BASE_URL,
            "model": DEFAULT_MODEL,
            "max_context_tokens": MAX_CONTEXT_TOKENS,
            "max_context_source": MAX_CONTEXT_SOURCE,
            "keep_last": DEFAULT_KEEP_LAST,
            "threshold": DEFAULT_THRESHOLD,
            "summary_budget_tokens": DEFAULT_SUMMARY_BUDGET_TOKENS,
            "summary_timeout_seconds": SUMMARY_TIMEOUT_SECONDS,
            "tokenizer": tokenizer,
            "extra_header_names": sorted(_extra_headers()),
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    """Run the stdio MCP server until the client stops it.

    This is the console-script entry point (``context-shrink``) and the
    ``__main__`` guard's target: the MCP client owns the process lifetime.
    """
    try:
        asyncio.run(server.run_stdio_async())
    except (KeyboardInterrupt, BrokenPipeError):  # pragma: no cover - user interrupt
        # A clean exit on Ctrl-C / closed pipe: the MCP client decides when to stop us.
        pass


if __name__ == "__main__":
    main()
