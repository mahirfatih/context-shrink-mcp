"""Unit tests for the Context Shrink MCP server.

These cover the pure helpers (token estimation, trimming, compaction splitting,
chunking) and the optional-tokenizer resolution logic. No network access and no
MCP transport are involved.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "context-shrink.py"


def _load_module() -> ModuleType:
    """Import the single-file server by path (its name is not a module id)."""
    spec = importlib.util.spec_from_file_location("context_shrink", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def shrink() -> ModuleType:
    """A freshly imported server module, so the tokenizer cache is empty."""
    return _load_module()


@pytest.fixture(autouse=True)
def _force_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to the deterministic, dependency-free token counter."""
    monkeypatch.setenv("CONTEXT_SHRINK_TOKENIZER", "heuristic")


# --- _content_to_text ---------------------------------------------------------


def test_content_to_text_handles_string_none_and_parts(shrink: ModuleType) -> None:
    assert shrink._content_to_text(None) == ""
    assert shrink._content_to_text("hello") == "hello"
    assert shrink._content_to_text([{"text": "a"}, "b", {"no": "text"}]) == "a\nb"


# --- token estimation ------------------------------------------------------


def test_estimate_tokens_heuristic_uses_chars_over_four(shrink: ModuleType) -> None:
    messages = [{"role": "user", "content": "x" * 40}]
    assert shrink._estimate_tokens(messages) == 10


def test_estimate_tokens_never_returns_zero(shrink: ModuleType) -> None:
    assert shrink._estimate_tokens([]) == 1
    assert shrink._estimate_tokens([{"role": "user", "content": ""}]) == 1


def test_estimate_tokens_ignores_non_dict_messages(shrink: ModuleType) -> None:
    messages = [{"role": "user", "content": "x" * 8}, "not a dict"]
    assert shrink._estimate_tokens(messages) == 2


def test_estimate_context_reports_tokenizer_and_budget(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.estimate_context([{"role": "user", "content": "x" * 40}], max_context_tokens=4)
    )
    assert payload["estimated_context_tokens"] == 10
    assert payload["remaining_tokens"] == -6
    assert payload["should_trim"] is True
    assert payload["tokenizer"] == shrink._HEURISTIC_LABEL


def test_estimate_context_within_budget_is_not_trimmed(shrink: ModuleType) -> None:
    payload = json.loads(shrink.estimate_context([{"role": "user", "content": "x" * 40}]))
    assert payload["should_trim"] is False


# --- trimming --------------------------------------------------------------


def test_trim_keeps_the_last_messages_when_over_budget(shrink: ModuleType) -> None:
    messages = [{"role": "user", "content": str(i) + "x" * 400} for i in range(20)]
    payload = json.loads(
        shrink.trim_context(messages, keep_last=5, max_context_tokens=250)
    )
    assert payload["original_count"] == 20
    assert payload["trimmed_count"] == 5
    assert payload["messages"][-1]["content"] == messages[-1]["content"]


def test_trim_leaves_short_lists_untouched(shrink: ModuleType) -> None:
    messages = [{"role": "user", "content": "hi"}]
    payload = json.loads(shrink.trim_context(messages, keep_last=8))
    assert payload["messages"] == messages


# --- compaction splitting --------------------------------------------------


def test_split_keeps_leading_system_messages_and_tail(shrink: ModuleType) -> None:
    messages = [{"role": "system", "content": "s1"}, {"role": "system", "content": "s2"}]
    messages += [{"role": "user", "content": str(i)} for i in range(5)]
    leading, to_summarize, keep = shrink._split_for_compaction(messages, keep_last=2)
    assert [m["content"] for m in leading] == ["s1", "s2"]
    assert [m["content"] for m in keep] == ["3", "4"]
    assert [m["content"] for m in to_summarize] == ["0", "1", "2"]


def test_split_with_short_rest_summarizes_nothing(shrink: ModuleType) -> None:
    leading, to_summarize, keep = shrink._split_for_compaction(
        [{"role": "user", "content": "only"}], keep_last=8
    )
    assert leading == []
    assert to_summarize == []
    assert len(keep) == 1


# --- compaction behaviour --------------------------------------------------


def _long_history(count: int = 20) -> list[dict[str, str]]:
    return [{"role": "user", "content": str(i) + "y" * 4000} for i in range(count)]


def test_compact_reports_nothing_to_compact_for_short_history(shrink: ModuleType) -> None:
    payload = json.loads(shrink.compact_context([{"role": "user", "content": "hi"}]))
    assert payload["compacted"] is False
    assert payload["reason"] == "nothing_to_compact"


def test_compact_uses_provided_summary(shrink: ModuleType) -> None:
    messages = _long_history()
    payload = json.loads(
        shrink.compact_context(messages, keep_last=2, max_context_tokens=1000, summary="SUM")
    )
    assert payload["compacted"] is True
    assert payload["method"] == "provided"
    assert payload["summary"] == "SUM"
    assert payload["messages"][-1]["content"] == messages[-1]["content"]
    assert payload["messages"][0]["content"].startswith("[summary of earlier conversation]")


def test_compact_returns_plan_when_no_model(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.compact_context(_long_history(), keep_last=2, max_context_tokens=1000, model="")
    )
    assert payload["compacted"] is False
    assert payload["needs_summary"] is True
    assert payload["summary_prompt"] == shrink.SUMMARY_INSTRUCTIONS
    assert "messages" not in payload  # no message content is echoed back


def test_compact_respects_threshold_unless_forced(shrink: ModuleType) -> None:
    messages = [{"role": "user", "content": str(i) + "z" * 400} for i in range(5)]
    skipped = json.loads(shrink.compact_context(messages, keep_last=1))
    assert skipped["reason"] == "within_threshold"
    forced = json.loads(
        shrink.compact_context(messages, keep_last=1, summary="S", force=True)
    )
    assert forced["compacted"] is True


# --- chunking --------------------------------------------------------------


def test_chunk_messages_stays_within_budget(shrink: ModuleType) -> None:
    messages = [{"role": "user", "content": "w" * 400} for _ in range(10)]
    chunks = shrink._chunk_messages(messages, chunk_budget_tokens=250)
    assert sum(len(chunk) for chunk in chunks) == 10
    assert all(shrink._estimate_tokens(chunk) <= 250 for chunk in chunks)


# --- optional tokenizer ----------------------------------------------------


class _FakeEncoding:
    def encode(self, text: str) -> list[str]:
        return text.split()


class _FakeTiktoken:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_encoding(self, name: str) -> _FakeEncoding:
        self.calls.append(name)
        return _FakeEncoding()


class _BrokenTiktoken:
    def get_encoding(self, name: str) -> _FakeEncoding:
        raise ValueError("no such encoding")


def test_tokenizer_falls_back_when_tiktoken_missing(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTEXT_SHRINK_TOKENIZER", "auto")
    monkeypatch.setattr(shrink, "tiktoken", None)
    monkeypatch.setattr(shrink, "_tokenizer_cache", None)
    encode, label = shrink._resolve_tokenizer()
    assert encode is None
    assert label == shrink._HEURISTIC_LABEL


def test_tokenizer_uses_tiktoken_when_available(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeTiktoken()
    monkeypatch.setenv("CONTEXT_SHRINK_TOKENIZER", "auto")
    monkeypatch.setattr(shrink, "tiktoken", fake)
    monkeypatch.setattr(shrink, "_tokenizer_cache", None)
    encode, label = shrink._resolve_tokenizer()
    assert label == "tiktoken:cl100k_base"
    assert fake.calls == ["cl100k_base"]
    assert encode("a b c") == ["a", "b", "c"]


def test_tokenizer_honours_explicit_encoding(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeTiktoken()
    monkeypatch.setenv("CONTEXT_SHRINK_TOKENIZER", "o200k_base")
    monkeypatch.setattr(shrink, "tiktoken", fake)
    monkeypatch.setattr(shrink, "_tokenizer_cache", None)
    _, label = shrink._resolve_tokenizer()
    assert label == "tiktoken:o200k_base"
    assert fake.calls == ["o200k_base"]


def test_tokenizer_falls_back_on_unknown_encoding(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTEXT_SHRINK_TOKENIZER", "does-not-exist")
    monkeypatch.setattr(shrink, "tiktoken", _BrokenTiktoken())
    monkeypatch.setattr(shrink, "_tokenizer_cache", None)
    encode, label = shrink._resolve_tokenizer()
    assert encode is None
    assert label == shrink._HEURISTIC_LABEL


def test_tokenizer_disabled_by_heuristic_setting(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTEXT_SHRINK_TOKENIZER", "off")
    monkeypatch.setattr(shrink, "tiktoken", _FakeTiktoken())
    monkeypatch.setattr(shrink, "_tokenizer_cache", None)
    encode, label = shrink._resolve_tokenizer()
    assert encode is None
    assert label == shrink._HEURISTIC_LABEL


# --- _env_float -------------------------------------------------------------
def test_env_float_parses_valid_value(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMLX_SHRINK_TIMEOUT", "60.5")
    assert shrink._env_float("OMLX_SHRINK_TIMEOUT", default=180.0) == 60.5


def test_env_float_defaults_on_missing_and_garbage(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OMLX_SHRINK_TIMEOUT", raising=False)
    assert shrink._env_float("OMLX_SHRINK_TIMEOUT", default=180.0) == 180.0
    monkeypatch.setenv("OMLX_SHRINK_TIMEOUT", "not-a-number")
    assert shrink._env_float("OMLX_SHRINK_TIMEOUT", default=180.0) == 180.0


def test_env_float_never_returns_zero_or_negative(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMLX_SHRINK_TIMEOUT", "0")
    assert shrink._env_float("OMLX_SHRINK_TIMEOUT", default=180.0) == 1.0
    monkeypatch.setenv("OMLX_SHRINK_TIMEOUT", "-5")
    assert shrink._env_float("OMLX_SHRINK_TIMEOUT", default=180.0) == 1.0


def test_openai_shrink_alias_is_used_when_legacy_name_is_absent(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OMLX_SHRINK_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_SHRINK_BASE_URL", "http://localhost:1234/v1")
    assert (
        shrink._env_value("OMLX_SHRINK_BASE_URL", "OPENAI_SHRINK_BASE_URL", default="d")
        == "http://localhost:1234/v1"
    )


def test_legacy_name_wins_over_generic_alias(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMLX_SHRINK_MODEL", "legacy-model")
    monkeypatch.setenv("OPENAI_SHRINK_MODEL", "generic-model")
    assert (
        shrink._env_value("OMLX_SHRINK_MODEL", "OPENAI_SHRINK_MODEL", default="")
        == "legacy-model"
    )


def test_context_shrink_name_wins_over_legacy_and_generic(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTEXT_SHRINK_MODEL", "canonical-model")
    monkeypatch.setenv("OMLX_SHRINK_MODEL", "legacy-model")
    monkeypatch.setenv("OPENAI_SHRINK_MODEL", "generic-model")
    assert (
        shrink._env_value(
            "CONTEXT_SHRINK_MODEL",
            "OMLX_SHRINK_MODEL",
            "OPENAI_SHRINK_MODEL",
            default="",
        )
        == "canonical-model"
    )


def test_context_shrink_falls_back_to_legacy_then_generic(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CONTEXT_SHRINK_MODEL", raising=False)
    monkeypatch.setenv("OMLX_SHRINK_MODEL", "legacy-model")
    monkeypatch.setenv("OPENAI_SHRINK_MODEL", "generic-model")
    names = ("CONTEXT_SHRINK_MODEL", "OMLX_SHRINK_MODEL", "OPENAI_SHRINK_MODEL")
    assert shrink._env_value(*names, default="") == "legacy-model"
    monkeypatch.delenv("OMLX_SHRINK_MODEL", raising=False)
    assert shrink._env_value(*names, default="") == "generic-model"


def test_extra_headers_context_name_wins_over_aliases(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTEXT_SHRINK_EXTRA_HEADERS", '{"x-canonical": "1"}')
    monkeypatch.setenv("OMLX_SHRINK_EXTRA_HEADERS", '{"x-legacy": "2"}')
    monkeypatch.setenv("OPENAI_SHRINK_EXTRA_HEADERS", '{"x-generic": "3"}')
    assert shrink._extra_headers() == {"x-canonical": "1"}
    monkeypatch.delenv("CONTEXT_SHRINK_EXTRA_HEADERS", raising=False)
    assert shrink._extra_headers() == {"x-legacy": "2"}
    monkeypatch.delenv("OMLX_SHRINK_EXTRA_HEADERS", raising=False)
    assert shrink._extra_headers() == {"x-generic": "3"}


# --- _chat_completions_url --------------------------------------------------
@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://127.0.0.1:8000/v1", "http://127.0.0.1:8000/v1/chat/completions"),
        ("http://127.0.0.1:8000/v1/", "http://127.0.0.1:8000/v1/chat/completions"),
        ("http://127.0.0.1:8000/v1/chat/completions", "http://127.0.0.1:8000/v1/chat/completions"),
        ("  http://api.example.com/openai  ", "http://api.example.com/openai/chat/completions"),
        ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
    ],
)
def test_chat_completions_url_normalizes_base_url(
    shrink: ModuleType, base_url: str, expected: str
) -> None:
    assert shrink._chat_completions_url(base_url) == expected


def test_tokenizer_honours_generic_alias(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CONTEXT_SHRINK_TOKENIZER", raising=False)
    monkeypatch.delenv("OMLX_SHRINK_TOKENIZER", raising=False)
    monkeypatch.setenv("OPENAI_SHRINK_TOKENIZER", "heuristic")
    monkeypatch.setattr(shrink, "tiktoken", _FakeTiktoken())
    monkeypatch.setattr(shrink, "_tokenizer_cache", None)
    encode, label = shrink._resolve_tokenizer()
    assert encode is None
    assert label == shrink._HEURISTIC_LABEL


# --- _extra_headers ----------------------------------------------------------
def test_extra_headers_parses_json_object(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_SHRINK_EXTRA_HEADERS", '{"api-key": "secret", "x-org": 42}')
    assert shrink._extra_headers() == {"api-key": "secret", "x-org": "42"}


def test_extra_headers_ignore_invalid_input(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_SHRINK_EXTRA_HEADERS", raising=False)
    assert shrink._extra_headers() == {}
    monkeypatch.setenv("OPENAI_SHRINK_EXTRA_HEADERS", "not-json")
    assert shrink._extra_headers() == {}
    monkeypatch.setenv("OPENAI_SHRINK_EXTRA_HEADERS", '["a", "b"]')
    assert shrink._extra_headers() == {}


def test_call_chat_completions_sends_extra_headers(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"summarized"}}]}'

    def fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.headers)
        return _FakeResponse()

    monkeypatch.setattr(shrink.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("OPENAI_SHRINK_EXTRA_HEADERS", '{"api-key": "secret"}')
    result = shrink._call_chat_completions(
        [{"role": "user", "content": "hi"}], "http://example.test/v1/", "tok", "m", 8
    )
    assert result == "summarized"
    assert captured["url"] == "http://example.test/v1/chat/completions"
    headers = captured["headers"]
    assert headers.get("Api-key") == "secret"
    assert headers.get("Authorization") == "Bearer tok"


# --- server identity ---------------------------------------------------------
def test_server_display_name_is_context_shrink(shrink: ModuleType) -> None:
    assert shrink.server.name == "Context Shrink MCP"


# --- input hardening: log level and budget ---------------------------------


def test_resolve_log_level_reads_env(
    shrink: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTEXT_SHRINK_LOG_LEVEL", "debug")
    assert shrink._resolve_log_level() == (logging.DEBUG, "")
    monkeypatch.setenv("CONTEXT_SHRINK_LOG_LEVEL", "not-a-level")
    assert shrink._resolve_log_level() == (logging.INFO, "not-a-level")


def test_coerce_budget_clamps_to_sane_range(shrink: ModuleType) -> None:
    assert shrink._coerce_budget(500) == 500
    assert shrink._coerce_budget(0) == 1
    assert shrink._coerce_budget(-10) == 1
    assert shrink._coerce_budget(10_000_000) == shrink.MAX_CONTEXT_TOKENS_CEILING
    assert shrink._coerce_budget("not-an-int") == shrink.MAX_CONTEXT_TOKENS


def test_estimate_context_clamps_out_of_range_budget(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.estimate_context([{"role": "user", "content": "x" * 40}], max_context_tokens=-5)
    )
    assert payload["max_context_tokens"] == 1


def test_compact_clamps_non_positive_keep_last(shrink: ModuleType) -> None:
    payload = json.loads(
        shrink.compact_context(
            _long_history(), keep_last=-3, max_context_tokens=1000, summary="S"
        )
    )
    assert payload["compacted"] is True
    assert payload["kept_count"] == 1


def test_chat_completions_url_warns_on_missing_scheme(
    shrink: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="context-shrink"):
        result = shrink._chat_completions_url("example.com/v1")
    assert result == "example.com/v1/chat/completions"
    assert "does not look like" in caplog.text


# --- context-window resolution -----------------------------------------------


def test_default_context_window_is_32768(shrink: ModuleType) -> None:
    assert shrink.DEFAULT_MAX_CONTEXT_TOKENS == 32768


def test_cli_max_context_parses_the_flag(shrink: ModuleType) -> None:
    assert shrink._cli_max_context([]) is None
    assert shrink._cli_max_context(["--max-context", "65536"]) == 65536


def test_cli_max_context_ignores_unrelated_client_arguments(shrink: ModuleType) -> None:
    argv = ["some-other-flag", "--lang", "tr", "--max-context", "1234", "--extra"]
    assert shrink._cli_max_context(argv) == 1234
    assert shrink._cli_max_context(["--unrelated", "value"]) is None


def test_cli_max_context_disables_abbreviations(shrink: ModuleType) -> None:
    # ``--max`` must not be treated as a prefix of ``--max-context``; it is
    # simply ignored as an unrelated client argument.
    assert shrink._cli_max_context(["--max", "5"]) is None


def test_describe_config_reports_resolved_window(shrink: ModuleType) -> None:
    payload = json.loads(shrink.describe_config())
    assert payload["max_context_tokens"] == shrink.MAX_CONTEXT_TOKENS
    assert payload["max_context_source"] == shrink.MAX_CONTEXT_SOURCE
    assert payload["max_context_source"] in {"cli", "env", "default"}
    assert payload["keep_last"] == shrink.DEFAULT_KEEP_LAST
    assert payload["threshold"] == shrink.DEFAULT_THRESHOLD
    assert "extra_header_names" in payload
