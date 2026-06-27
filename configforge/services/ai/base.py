import logging
from abc import ABC, abstractmethod

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# 编程错误重试无意义，直接排除
_NON_RETRYABLE = (TypeError, ValueError, KeyError, AttributeError)


class LlmBackend(ABC):
    """LLM 后端抽象基类。"""

    @abstractmethod
    async def generate(self, prompt: str) -> str: ...


def _is_retryable(exc: BaseException) -> bool:
    """网络抖动 / 429 限流 / 5xx / 超时等瞬态故障重试；编程错误不重试。"""
    return not isinstance(exc, _NON_RETRYABLE)


# 共享重试策略：最多 3 次，指数退避 1s→2s→4s
retry_generate = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
