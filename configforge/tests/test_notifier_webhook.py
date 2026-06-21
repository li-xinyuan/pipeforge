"""Additional tests for WebhookNotifier not covered in test_notifier.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.webhook import WebhookNotifier


def _make_context(**overrides) -> NotifyContext:
    defaults = dict(
        execution_id="exec-100",
        config_name="测试配置",
        status="success",
        summary="测试摘要",
        output_files=["out.csv"],
        started_at="2026-06-21T10:00:00",
        finished_at="2026-06-21T10:01:00",
    )
    defaults.update(overrides)
    return NotifyContext(**defaults)


def _mock_async_client(post_return=None, post_side_effect=None):
    """Build a mock httpx.AsyncClient that can be used as a context manager."""
    mock_client = AsyncMock()
    if post_side_effect is not None:
        mock_client.post.side_effect = post_side_effect
    elif post_return is not None:
        mock_client.post.return_value = post_return
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# ─── TestWebhookNotifierInit ───


class TestWebhookNotifierInit:
    def test_default_values(self):
        notifier = WebhookNotifier(url="https://example.com/hook")
        assert notifier.url == "https://example.com/hook"
        assert notifier.provider == "generic"
        assert notifier.timeout == 10.0
        assert notifier.max_retries == 1
        assert notifier.headers == {}

    def test_custom_values(self):
        notifier = WebhookNotifier(
            url="https://example.com/hook",
            provider="dingtalk",
            headers={"Authorization": "Bearer token123"},
            timeout=30.0,
            max_retries=3,
        )
        assert notifier.provider == "dingtalk"
        assert notifier.headers == {"Authorization": "Bearer token123"}
        assert notifier.timeout == 30.0
        assert notifier.max_retries == 3

    def test_headers_none_becomes_empty_dict(self):
        notifier = WebhookNotifier(url="https://example.com/hook", headers=None)
        assert notifier.headers == {}

    def test_max_retries_zero(self):
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=0)
        assert notifier.max_retries == 0


# ─── TestWebhookRetryBehavior ───


class TestWebhookRetryBehavior:
    @pytest.mark.asyncio
    async def test_retry_on_timeout_up_to_max_retries(self):
        """Timeout errors should trigger retries up to max_retries times."""
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=2)
        ctx = _make_context()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(
                post_side_effect=httpx.TimeoutException("timeout")
            )
            mock_cls.return_value = mock_client

            result = await notifier.send(ctx)
            assert result.success is False
            assert "timed out" in result.message.lower()
            # 1 initial + 2 retries = 3 attempts
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self):
        """Network errors (httpx.RequestError) should trigger retries."""
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=1)
        ctx = _make_context()

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(
                post_side_effect=httpx.RequestError("connection reset")
            )
            mock_cls.return_value = mock_client

            result = await notifier.send(ctx)
            assert result.success is False
            assert "network error" in result.message.lower()
            # 1 initial + 1 retry = 2 attempts
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_http_4xx(self):
        """HTTP 4xx errors should NOT trigger retries."""
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=2)
        ctx = _make_context()

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(post_return=mock_response)
            mock_cls.return_value = mock_client

            result = await notifier.send(ctx)
            assert result.success is False
            assert "400" in result.message
            # Should NOT retry: only 1 call
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_http_5xx(self):
        """HTTP 5xx errors should NOT trigger retries (only timeout/network retry)."""
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=2)
        ctx = _make_context()

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(post_return=mock_response)
            mock_cls.return_value = mock_client

            result = await notifier.send(ctx)
            assert result.success is False
            assert "503" in result.message
            # Should NOT retry: only 1 call
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """If the first attempt times out but the second succeeds, return success."""
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=1)
        ctx = _make_context()

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(
                post_side_effect=[
                    httpx.TimeoutException("timeout"),
                    mock_response_ok,
                ]
            )
            mock_cls.return_value = mock_client

            result = await notifier.send(ctx)
            assert result.success is True
            assert mock_client.post.call_count == 2


# ─── TestWebhookBuildPayload ───


class TestWebhookBuildPayload:
    def test_dingtalk_payload_structure(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="dingtalk")
        payload = notifier._build_payload(_make_context())
        assert "msgtype" in payload
        assert payload["msgtype"] == "markdown"
        assert "markdown" in payload
        assert "title" in payload["markdown"]
        assert "text" in payload["markdown"]

    def test_wecom_payload_structure(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="wecom")
        payload = notifier._build_payload(_make_context())
        assert "msgtype" in payload
        assert payload["msgtype"] == "markdown"
        assert "markdown" in payload
        assert "content" in payload["markdown"]

    def test_feishu_payload_structure(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="feishu")
        payload = notifier._build_payload(_make_context())
        assert "msg_type" in payload
        assert payload["msg_type"] == "interactive"
        assert "card" in payload
        assert "header" in payload["card"]
        assert "elements" in payload["card"]

    def test_generic_payload_structure(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="generic")
        payload = notifier._build_payload(_make_context())
        assert "execution_id" in payload
        assert "config_name" in payload
        assert "status" in payload
        assert "summary" in payload
        assert "started_at" in payload
        assert "finished_at" in payload

    def test_failed_context_generic_includes_error_message(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="generic")
        payload = notifier._build_payload(
            _make_context(status="failed", error_message="boom", output_files=[])
        )
        assert payload["error_message"] == "boom"
        assert "output_files" not in payload

    def test_success_context_generic_includes_output_files(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="generic")
        payload = notifier._build_payload(_make_context(status="success"))
        assert payload["output_files"] == ["out.csv"]
        assert "error_message" not in payload


# ─── TestWebhookTimeout ───


class TestWebhookTimeout:
    @pytest.mark.asyncio
    async def test_custom_timeout_passed_to_async_client(self):
        """The timeout value should be forwarded to httpx.AsyncClient."""
        notifier = WebhookNotifier(
            url="https://example.com/hook", timeout=25.0
        )
        ctx = _make_context()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(post_return=mock_response)
            mock_cls.return_value = mock_client

            await notifier.send(ctx)
            mock_cls.assert_called_once_with(timeout=25.0)

    @pytest.mark.asyncio
    async def test_default_timeout_passed_to_async_client(self):
        """Default timeout (10.0) should be used when not explicitly set."""
        notifier = WebhookNotifier(url="https://example.com/hook")
        ctx = _make_context()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = _mock_async_client(post_return=mock_response)
            mock_cls.return_value = mock_client

            await notifier.send(ctx)
            mock_cls.assert_called_once_with(timeout=10.0)


# ─── TestWebhookMultipleProviders ───


class TestWebhookMultipleProviders:
    def test_dingtalk_has_msgtype_markdown(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="dingtalk")
        payload = notifier._build_payload(_make_context())
        assert payload["msgtype"] == "markdown"
        assert "markdown" in payload

    def test_wecom_has_msgtype_markdown(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="wecom")
        payload = notifier._build_payload(_make_context())
        assert payload["msgtype"] == "markdown"
        assert "markdown" in payload

    def test_feishu_has_msg_type_interactive(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="feishu")
        payload = notifier._build_payload(_make_context())
        assert payload["msg_type"] == "interactive"
        assert "card" in payload

    def test_generic_has_execution_id(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="generic")
        payload = notifier._build_payload(_make_context())
        assert payload["execution_id"] == "exec-100"

    def test_feishu_success_header_is_green(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="feishu")
        payload = notifier._build_payload(_make_context(status="success"))
        assert payload["card"]["header"]["template"] == "green"

    def test_feishu_failed_header_is_red(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="feishu")
        payload = notifier._build_payload(_make_context(status="failed", error_message="err"))
        assert payload["card"]["header"]["template"] == "red"

    def test_feishu_anomaly_header_is_orange(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="feishu")
        payload = notifier._build_payload(_make_context(status="anomaly"))
        assert payload["card"]["header"]["template"] == "orange"
