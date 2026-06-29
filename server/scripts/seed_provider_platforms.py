"""
Seed script for provider_platforms table.
Inserts known provider platforms with their IDs, names, and base URLs.
Run: python -m server.scripts.seed_provider_platforms
"""
import asyncio

from sqlalchemy.dialects.postgresql import insert as pg_insert

from server.core.database import AsyncSessionLocal
from server.modules.provisioning.models import ProviderPlatform

# Provider platforms to seed: (id, name, base_url)
PROVIDERS = [
    ("github", "GitHub Models", "https://models.github.ai/inference"),
    ("groq", "Groq", "https://api.groq.com/openai/v1"),
    ("cerebras", "Cerebras", "https://api.cerebras.ai/v1"),
    ("mistral", "Mistral", "https://api.mistral.ai/v1"),
    ("ollama", "Ollama", "https://ollama.com/v1"),
    ("pollinations", "Pollinations AI", "https://text.pollinations.ai/openai/v1"),
    ("zhipu", "Zhipu AI", "https://open.bigmodel.cn/api/paas/v4"),
    ("llm7", "LLM7", "https://api.llm7.io/v1"),
    ("deepseek", "DeepSeek", "https://api.deepseek.com/v1"),
    ("huggingface", "Hugging Face", "https://router.huggingface.co/v1"),
    ("kilo", "Kilo Gateway", "https://api.kilo.ai/api/gateway"),
    ("nvidia", "NVIDIA", "https://integrate.api.nvidia.com/v1"),
    ("openrouter", "OpenRouter", "https://openrouter.ai/api/v1"),
    ("siliconflow", "SiliconFlow", "https://api.siliconflow.com/v1"),
    ("together", "Together AI", "https://api.together.xyz/v1"),
    ("fireworks", "Fireworks AI", "https://api.fireworks.ai/inference/v1"),
    ("perplexity", "Perplexity AI", "https://api.perplexity.ai"),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for provider_id, name, base_url in PROVIDERS:
            stmt = (
                pg_insert(ProviderPlatform)
                .values(
                    id=provider_id,
                    name=name,
                    base_url=base_url,
                    timeout_ms=30000,
                    extra_headers=None,
                    is_native=False,
                    npm_package=None,
                    free_tier=False,
                    enabled=True,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_=dict(
                        name=name,
                        base_url=base_url,
                        timeout_ms=30000,
                        extra_headers=None,
                        is_native=False,
                        npm_package=None,
                        free_tier=False,
                        enabled=True,
                    ),
                )
            )
            await session.execute(stmt)
        await session.commit()
        print(f"Seeded {len(PROVIDERS)} providers.")


if __name__ == "__main__":
    asyncio.run(seed())
