from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import openai
from openai import AsyncOpenAI
import json
import os

from .models import GenerateRequest, GenerateResponse


class ProviderError(Exception):
    pass


class RateLimitError(ProviderError):
    pass


class Provider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.request_count = 0
        self.token_count = 0
        self.cost_estimate = 0.0

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        pass

    def record_usage(self, tokens: int):
        self.request_count += 1
        self.token_count += tokens
        self.cost_estimate += self.estimate_cost(tokens)


class OpenAIProvider(Provider):
    """OpenAI provider implementation"""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str, **kwargs) -> str:
        max_retries = kwargs.get('max_retries', 3)
        retry_delay = kwargs.get('retry_delay', 1.0)

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=kwargs.get('max_tokens', 1000),
                    temperature=kwargs.get('temperature', 0.7)
                )

                content = response.choices[0].message.content
                # Record usage
                tokens_used = response.usage.total_tokens if response.usage else 0
                self.record_usage(tokens_used)

                return content

            except openai.RateLimitError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                raise RateLimitError(f"Rate limit exceeded: {e}")

            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise ProviderError(f"OpenAI API error: {e}")

        raise ProviderError("Max retries exceeded")

    def estimate_cost(self, tokens: int) -> float:
        # Rough cost estimates per 1K tokens (as of 2024)
        costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        }

        model_costs = costs.get(self.model, costs["gpt-4"])
        # Assume 70% of tokens are output tokens for estimation
        input_tokens = tokens * 0.3
        output_tokens = tokens * 0.7

        return (input_tokens * model_costs["input"] + output_tokens * model_costs["output"]) / 1000


class ProviderManager:
    """Manages multiple LLM providers with failover and load balancing"""

    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self.default_provider = None
        self.failover_enabled = True

    def add_provider(self, name: str, provider: Provider):
        self.providers[name] = provider
        if self.default_provider is None:
            self.default_provider = name

    def set_default_provider(self, name: str):
        if name in self.providers:
            self.default_provider = name
        else:
            raise ValueError(f"Provider {name} not found")

    async def generate(self, prompt: str, provider_name: Optional[str] = None, **kwargs) -> str:
        provider_name = provider_name or self.default_provider
        if not provider_name or provider_name not in self.providers:
            raise ProviderError(f"Provider {provider_name} not available")

        provider = self.providers[provider_name]

        try:
            return await provider.generate(prompt, **kwargs)
        except RateLimitError as e:
            if self.failover_enabled:
                # Try other providers
                for name, fallback_provider in self.providers.items():
                    if name != provider_name:
                        try:
                            print(f"Failing over to provider {name}")
                            return await fallback_provider.generate(prompt, **kwargs)
                        except Exception:
                            continue
            raise e
        except Exception as e:
            raise e

    def get_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = {
                "requests": provider.request_count,
                "tokens": provider.token_count,
                "estimated_cost": provider.cost_estimate,
                "model": provider.model
            }
        return stats

    def reset_usage_stats(self):
        for provider in self.providers.values():
            provider.request_count = 0
            provider.token_count = 0
            provider.cost_estimate = 0.0


# Global provider manager instance
provider_manager = ProviderManager()

# Initialize with OpenAI if API key is available
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    openai_provider = OpenAIProvider(openai_key, "gpt-4")
    provider_manager.add_provider("openai", openai_provider)
else:
    print("Warning: OPENAI_API_KEY not found, LLM functionality will be limited")


async def generate_with_provider(prompt: str, **kwargs) -> str:
    """Convenience function to generate with the default provider"""
    return await provider_manager.generate(prompt, **kwargs)


def get_provider_stats() -> Dict[str, Dict[str, Any]]:
    """Get usage statistics for all providers"""
    return provider_manager.get_usage_stats()