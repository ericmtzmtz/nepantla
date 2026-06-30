"""
Seed context_window values for known models.

Run after initial seed or auto-provisioning sync to populate context_window
for models that may have been added with NULL.

Run: python -m server.scripts.seed_context_windows
"""
# ruff: noqa: E501
import asyncio

from sqlalchemy import update

from server.core.database import AsyncSessionLocal
from server.modules.providers.models import ProviderCatalog

# (platform, model_id, context_window)
CONTEXT_WINDOWS = [
    # OpenAI / github / openrouter
    ("openai",      "gpt-4o",               128000),
    ("openai",      "gpt-4o-mini",          128000),
    ("openai",      "gpt-4-turbo",          128000),
    ("openai",      "gpt-3.5-turbo",        16384),
    ("github",      "gpt-4o",               128000),
    ("github",      "gpt-4o-mini",          128000),
    ("openrouter",  "openai/gpt-4o",        128000),
    ("openrouter",  "openai/gpt-4o-mini",   128000),

    # Anthropic / openrouter
    ("anthropic",   "claude-3.5-sonnet",    200000),
    ("anthropic",   "claude-3-haiku",       48000),
    ("anthropic",   "claude-3-opus",        200000),
    ("anthropic",   "claude-2",             100000),
    ("openrouter",  "anthropic/claude-3.5-sonnet", 200000),

    # Groq (free tier context limits – approximate)
    ("groq",        "llama-3.3-70b-versatile",       8192),
    ("groq",        "llama-3.1-8b-instant",          8192),
    ("groq",        "mixtral-8x7b-32768",            32768),
    ("groq",        "gemma2-9b-it",                  8192),
    ("groq",        "deepseek-r1-distill-llama-70b",  8192),

    # Cerebras (free tier context limits – approximate)
    ("cerebras",    "llama-3.3-70b",                 8192),
    ("cerebras",    "llama-3.1-8b",                  8192),

    # Google
    ("google",      "gemini-2.0-flash",      1048576),
    ("google",      "gemini-2.0-flash-lite", 1048576),
    ("google",      "gemini-1.5-pro",        2097152),
    ("google",      "gemini-1.5-flash",      1048576),
    ("google",      "gemini-2.5-pro-exp-03-25", 1048576),

    # DeepSeek
    ("deepseek",    "deepseek-chat",         65536),
    ("deepseek",    "deepseek-reasoner",      65536),

    # Mistral
    ("mistral",     "mistral-large",         128000),
    ("mistral",     "mistral-medium",        32000),
    ("mistral",     "mistral-small",         32000),

    # Cohere
    ("cohere",      "command-r-plus-08-2024", 128000),
    ("cohere",      "command-r-08-2024",      128000),

    # Cloudflare
    ("cloudflare",  "@cf/meta/llama-3.3-70b-instruct-fp8-fast", 131072),
    ("cloudflare",  "@cf/meta/llama-3.1-8b-instruct-fast",      131072),

    # Image generation models (prompt-only, set minimal context)
    ("google",      "imagen-3.0-generate-001",   4096),
    ("openrouter",  "openai/dall-e-3",            4096),
    ("openrouter",  "openai/dall-e-2",            4096),
    ("stability",   "sd3.5-large",                4096),
    ("stability",   "stable-diffusion-3.5-large", 4096),
    ("stability",   "stable-diffusion-3.5-medium", 4096),
]


async def main():
    async with AsyncSessionLocal() as session:
        count = 0
        for platform, model_id, ctx in CONTEXT_WINDOWS:
            stmt = (
                update(ProviderCatalog)
                .where(ProviderCatalog.platform == platform)
                .where(ProviderCatalog.model_id == model_id)
                .values(context_window=ctx)
            )
            result = await session.execute(stmt)
            if result.rowcount:
                count += result.rowcount

        await session.commit()
        print(f"Updated {count} model(s) with context_window.")


if __name__ == "__main__":
    asyncio.run(main())
