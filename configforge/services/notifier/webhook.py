from __future__ import annotations

from .base import NotifierBase, NotifyContext, NotifyResult
from .formatters import format_dingtalk, format_wecom, format_feishu, format_generic

import httpx

# Map provider name → formatter function
FORMATTERS = {
    "dingtalk": format_dingtalk,
    "wecom": format_wecom,
    "feishu": format_feishu,
    "generic": format_generic,
}


class WebhookNotifier(NotifierBase):
    """Sends notifications via HTTP POST webhook."""

    def __init__(
        self,
        url: str,
        provider: str = "generic",
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
        max_retries: int = 1,
    ) -> None:
        self.url = url
        self.provider = provider
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries

    def _build_payload(self, context: NotifyContext) -> dict:
        formatter = FORMATTERS.get(self.provider, format_generic)
        return formatter(context)

    async def send(self, context: NotifyContext) -> NotifyResult:
        payload = self._build_payload(context)
        headers = {"Content-Type": "application/json", **self.headers}

        last_error: str | None = None
        for attempt in range(1 + self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(self.url, json=payload, headers=headers)
                    if 200 <= resp.status_code < 300:
                        return NotifyResult(
                            success=True,
                            message=f"Webhook delivered ({resp.status_code})",
                            provider=self.provider,
                        )
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except httpx.TimeoutException:
                last_error = "Request timed out"
            except httpx.RequestError as exc:
                last_error = f"Network error: {exc}"
            # Only retry on network/timeout errors, not HTTP errors
            if last_error and ("timed out" in last_error.lower() or "network error" in last_error.lower()):
                continue
            break

        return NotifyResult(
            success=False,
            message=last_error or "Unknown error",
            provider=self.provider,
        )
