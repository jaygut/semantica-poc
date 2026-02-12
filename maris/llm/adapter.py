"""Model-agnostic LLM interface using OpenAI-compatible API.

Supports DeepSeek, OpenAI, Anthropic (via proxy), and Ollama. Non-Ollama
providers require a valid ``MARIS_LLM_API_KEY``. Calls are retried twice
on transient HTTP errors (429, 500, 502, 503) with exponential backoff.
"""

import functools
import logging
import time

from openai import APITimeoutError, OpenAI, APIStatusError

from maris.config import MARISConfig, get_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retry decorator for LLM calls (T2-13)
# ---------------------------------------------------------------------------

_LLM_RETRYABLE_STATUS = (429, 500, 502, 503)

def _llm_retry(max_attempts: int = 3, backoff_seconds: tuple[float, ...] = (2.0, 5.0)):
    """Retry decorator for LLM API calls on timeout or transient HTTP errors."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except APITimeoutError as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        wait = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
                        logger.warning(
                            "LLM retry %d/%d for %s after timeout: sleeping %.1fs",
                            attempt, max_attempts, fn.__name__, wait,
                        )
                        time.sleep(wait)
                except APIStatusError as exc:
                    last_exc = exc
                    if exc.status_code in _LLM_RETRYABLE_STATUS and attempt < max_attempts:
                        wait = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
                        logger.warning(
                            "LLM retry %d/%d for %s after HTTP %d: sleeping %.1fs",
                            attempt, max_attempts, fn.__name__, exc.status_code, wait,
                        )
                        time.sleep(wait)
                    else:
                        raise
            if last_exc is not None:
                logger.error("All %d LLM attempts failed for %s", max_attempts, fn.__name__)
                raise last_exc
        return wrapper
    return decorator


class LLMAdapter:
    """Unified LLM interface supporting DeepSeek, OpenAI, Anthropic, and Ollama."""

    PROVIDER_CONFIGS = {
        "deepseek": {"base_url": "https://api.deepseek.com/v1", "default_model": "deepseek-chat"},
        "openai": {"base_url": "https://api.openai.com/v1", "default_model": "gpt-4o"},
        "anthropic": {"base_url": "https://api.anthropic.com/v1", "default_model": "claude-sonnet-4-5-20250929"},
        "ollama": {"base_url": "http://localhost:11434/v1", "default_model": "llama3.1:8b"},
    }

    def __init__(self, config: MARISConfig | None = None):
        self.config = config or get_config()
        provider = self.config.llm_provider.lower()
        provider_cfg = self.PROVIDER_CONFIGS.get(provider, {})

        base_url = self.config.llm_base_url or provider_cfg.get("base_url", "")
        api_key = self.config.llm_api_key

        if not api_key and provider != "ollama":
            raise ValueError(
                f"MARIS_LLM_API_KEY is required for provider '{provider}'. "
                "Set it in .env or as an environment variable."
            )
        if not api_key:
            api_key = "ollama"

        self.default_model = self.config.llm_model or provider_cfg.get("default_model", "")
        self.reasoning_model = self.config.llm_reasoning_model

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=self.config.llm_timeout,
        )
        logger.info("LLMAdapter initialized: provider=%s, model=%s", provider, self.default_model)

    @_llm_retry(max_attempts=3, backoff_seconds=(2.0, 5.0))
    def complete(self, messages: list[dict], model: str | None = None, temperature: float = 0.1) -> str:
        """Send messages to the LLM and return the text response."""
        model = model or self.default_model
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=self.config.llm_max_tokens,
        )
        return response.choices[0].message.content or ""

    def complete_json(self, messages: list[dict], model: str | None = None) -> dict:
        """Send messages and parse a JSON object from the response.

        Uses robust JSON extraction that handles code fences, truncated
        responses, multiple code blocks, and non-JSON output.
        """
        text = self.complete(messages, model=model, temperature=0.0)
        # Lazy import to avoid circular dependency (query -> llm -> query)
        from maris.query.validators import extract_json_robust
        return extract_json_robust(text)
