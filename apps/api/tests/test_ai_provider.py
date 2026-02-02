"""Tests for AI provider abstraction (get_provider, complete_chat, stream_chat)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ai_provider import get_provider, _get_model, stream_chat, complete_chat


class TestGetProvider:
    def test_returns_config_value(self):
        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_PROVIDER = "anthropic"
            assert get_provider() == "anthropic"

    def test_returns_openai(self):
        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_PROVIDER = "openai"
            assert get_provider() == "openai"


class TestGetModel:
    def test_default_anthropic(self):
        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_MODEL = ""
            mock_cfg.AI_PROVIDER = "anthropic"
            assert "claude" in _get_model()

    def test_default_openai(self):
        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_MODEL = ""
            mock_cfg.AI_PROVIDER = "openai"
            assert _get_model() == "gpt-4o"

    def test_explicit_model(self):
        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_MODEL = "custom-model"
            assert _get_model() == "custom-model"


class TestStreamChat:
    def test_unknown_provider_raises(self):
        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_PROVIDER = "unknown"
            mock_cfg.AI_MAX_TOKENS = 100
            with pytest.raises(ValueError, match="Unknown AI provider"):
                list(stream_chat([{"role": "user", "content": "hi"}]))

    def test_anthropic_provider_streams(self):
        # Create a mock anthropic module
        mock_anthropic = MagicMock()
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.text_stream = iter(["Hello", " world"])
        mock_anthropic.Anthropic.return_value.messages.stream.return_value = mock_stream_ctx

        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_PROVIDER = "anthropic"
            mock_cfg.AI_MAX_TOKENS = 100
            mock_cfg.AI_API_KEY = "test-key"
            mock_cfg.AI_MODEL = "test-model"

            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                result = list(stream_chat([{"role": "user", "content": "hi"}]))

        assert result == ["Hello", " world"]

    def test_openai_provider_streams(self):
        mock_openai = MagicMock()
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hi"
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " there"
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = iter([chunk1, chunk2])

        with patch("services.ai_provider.Config") as mock_cfg:
            mock_cfg.AI_PROVIDER = "openai"
            mock_cfg.AI_MAX_TOKENS = 100
            mock_cfg.AI_API_KEY = "test-key"
            mock_cfg.AI_MODEL = "test-model"

            with patch.dict("sys.modules", {"openai": mock_openai}):
                result = list(stream_chat([{"role": "user", "content": "hi"}]))

        assert result == ["Hi", " there"]


class TestCompleteChat:
    def test_joins_stream_chunks(self):
        with patch("services.ai_provider.stream_chat", return_value=iter(["a", "b", "c"])):
            assert complete_chat([]) == "abc"
