"""Model-agnostic LLM interface using OpenAI-compatible API."""

import json
import logging
import re

from openai import OpenAI

from maris.config import MARISConfig, get_config

logger = logging.getLogger(__name__)


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
        api_key = self.config.llm_api_key or "not-needed"

        self.default_model = self.config.llm_model or provider_cfg.get("default_model", "")
        self.reasoning_model = self.config.llm_reasoning_model

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=self.config.llm_timeout,
        )
        logger.info("LLMAdapter initialized: provider=%s, model=%s", provider, self.default_model)

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

        Extracts JSON from markdown code fences if present, then falls back
        to parsing the raw response text.
        """
        text = self.complete(messages, model=model, temperature=0.0)

        # Try to extract from ```json ... ``` fences first
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        json_str = fence_match.group(1) if fence_match else text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response, returning raw text wrapper")
            return {"raw": text}
