"""
Seed script for nepantla model catalog.
Inserts known models from all providers with their capabilities.
Run: python -m server.scripts.seed_catalog
"""
# ruff: noqa: E501
import asyncio

from sqlalchemy import select

from server.core.database import AsyncSessionLocal
from server.modules.providers.models import ProviderCatalog

# Model catalog data: (platform, model_id, display_name, intel_rank, speed_rank, ...)
CATALOG = [
    # Groq
    ("groq", "llama-3.3-70b-versatile", "Llama 3.3 70B", 8, 6, "heavy", 30, 1000, 6000, 6000000, "18M tokens/h", 131072, True, False, False, False, False, True),
    ("groq", "llama-3.1-70b-versatile", "Llama 3.1 70B", 7, 7, "heavy", 30, 1000, 6000, 6000000, "18M tokens/h", 131072, True, False, False, False, False, True),
    ("groq", "llama-3.1-8b-instant", "Llama 3.1 8B", 5, 9, "medium", 30, 1000, 6000, 6000000, "18M tokens/h", 131072, False, False, False, False, False, False),
    ("groq", "mixtral-8x7b-32768", "Mixtral 8x7B", 7, 5, "heavy", 30, 1000, 5000, 5000000, "15M tokens/h", 32768, False, False, False, False, False, True),
    ("groq", "gemma2-9b-it", "Gemma 2 9B", 5, 8, "medium", 30, 1000, 6000, 6000000, "15M tokens/h", 8192, False, False, False, False, False, False),
    ("groq", "deepseek-r1-distill-llama-70b", "DeepSeek R1 70B", 9, 4, "heavy", 30, 1000, 6000, 6000000, "18M tokens/h", 131072, False, False, False, False, False, True),

    # Cerebras
    ("cerebras", "llama-3.3-70b", "Llama 3.3 70B", 8, 9, "heavy", 30, 1000, 200000, 200000000, "Unlimited", 131072, False, False, False, False, False, True),
    ("cerebras", "llama-3.1-8b", "Llama 3.1 8B", 5, 10, "medium", 30, 1000, 200000, 200000000, "Unlimited", 8192, False, False, False, False, False, True),

    # OpenRouter
    ("openrouter", "openai/gpt-4o", "GPT-4o", 10, 5, "heavy", 30, 1000, 200000, 200000000, "Flexible", 128000, True, True, True, True, True, True),
    ("openrouter", "openai/gpt-4o-mini", "GPT-4o Mini", 7, 8, "medium", 30, 1000, 200000, 200000000, "Flexible", 128000, True, False, False, False, True, True),
    ("openrouter", "anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 10, 5, "heavy", 30, 1000, 200000, 200000000, "Flexible", 200000, True, False, False, False, False, True),
    ("openrouter", "google/gemini-2.0-flash-001", "Gemini 2.0 Flash", 8, 8, "medium", 30, 1000, 200000, 200000000, "Flexible", 1048576, True, False, False, True, False, True),
    ("openrouter", "meta-llama/llama-3.2-3b-instruct", "Llama 3.2 3B", 4, 9, "small", 30, 1000, 200000, 200000000, "Flexible", 8192, False, False, False, False, False, False),
    ("openrouter", "mistralai/mistral-small-24b-instruct-2501", "Mistral Small 24B", 7, 7, "medium", 30, 1000, 200000, 200000000, "Flexible", 32768, False, False, False, False, False, True),

    # Google
    ("google", "gemini-2.0-flash", "Gemini 2.0 Flash", 8, 9, "medium", 10, 1500, 1000000, 10000000, "1M tokens/h", 1048576, True, False, False, True, False, True),
    ("google", "gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite", 6, 10, "medium", 30, 1500, 1000000, 10000000, "1M tokens/h", 1048576, False, False, False, True, False, True),
    ("google", "gemini-1.5-pro", "Gemini 1.5 Pro", 9, 4, "heavy", 2, 1000, 120000, 1200000, "120K tokens/h", 2097152, True, False, False, True, False, True),
    ("google", "gemini-1.5-flash", "Gemini 1.5 Flash", 7, 7, "medium", 10, 1500, 1000000, 10000000, "1M tokens/h", 1048576, True, False, False, True, False, True),
    ("google", "gemini-2.5-pro-exp-03-25", "Gemini 2.5 Pro Exp", 10, 3, "heavy", 5, 1000, 120000, 1200000, "120K tokens/h", 1048576, True, False, False, True, False, True),

    # Cohere
    ("cohere", "command-r-plus-08-2024", "Command R+", 8, 5, "heavy", 5, 1000, 30000, 10000000, "10M tokens/h", 128000, False, False, False, False, False, True),
    ("cohere", "command-r-08-2024", "Command R", 7, 6, "heavy", 5, 1000, 30000, 10000000, "10M tokens/h", 128000, False, False, False, False, False, True),
    ("cohere", "command-r7b-12-2024", "Command R7B", 5, 8, "small", 5, 1000, 30000, 10000000, "10M tokens/h", 128000, False, False, False, False, False, True),
    ("cohere", "embed-english-v3.0", "Embed English v3.0", 7, 9, "medium", 5, 1000, 30000, 10000000, "10M tokens/h", 512, False, False, False, False, False, True),

    # Cloudflare
    ("cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "Llama 3.3 70B", 8, 6, "heavy", 30, 900, None, None, "Unlimited", 131072, False, False, False, False, False, True),
    ("cloudflare", "@cf/meta/llama-3.2-3b-instruct", "Llama 3.2 3B", 4, 9, "small", 30, 900, None, None, "Unlimited", 8192, False, False, False, False, False, True),
    ("cloudflare", "@cf/meta/llama-3.1-8b-instruct-fast", "Llama 3.1 8B", 5, 9, "medium", 30, 900, None, None, "Unlimited", 131072, False, False, False, False, False, True),
    ("cloudflare", "@cf/qwen/qwen1.5-14b-awq", "Qwen 1.5 14B", 6, 7, "medium", 30, 900, None, None, "Unlimited", 8192, False, False, False, False, False, True),

    # DeepSeek
    ("deepseek", "deepseek-chat", "DeepSeek V3", 9, 7, "heavy", 30, 1000, 200000, 200000000, "Flexible", 65536, False, False, False, False, False, True),
    ("deepseek", "deepseek-reasoner", "DeepSeek R1", 10, 4, "heavy", 30, 1000, 200000, 200000000, "Flexible", 65536, False, False, False, False, False, True),

    # GitHub Models
    ("github", "gpt-4o", "GPT-4o", 10, 6, "heavy", 30, 1000, None, None, "Flexible", 128000, True, True, True, True, True, True),
    ("github", "gpt-4o-mini", "GPT-4o Mini", 7, 9, "medium", 30, 1000, None, None, "Flexible", 128000, True, False, False, False, True, True),
    ("github", "gemini-2.0-flash-001", "Gemini 2.0 Flash", 8, 8, "medium", 10, 1500, None, None, "Flexible", 1048576, True, False, False, True, False, True),
    ("github", "claude-3.5-sonnet", "Claude 3.5 Sonnet", 10, 5, "heavy", 30, 1000, None, None, "Flexible", 200000, True, False, False, False, False, True),
    ("github", "Llama-3.3-70B-Instruct", "Llama 3.3 70B", 8, 6, "heavy", 30, 1000, None, None, "Flexible", 131072, True, False, False, False, False, True),
    ("github", "Ministral-3B-2410", "Ministral 3B", 3, 9, "small", 30, 1000, None, None, "Flexible", 32768, False, False, False, False, False, False),
    ("github", "Mistral-Small-24B-Instruct-2501", "Mistral Small 24B", 7, 7, "medium", 30, 1000, None, None, "Flexible", 32768, False, False, False, False, False, True),

    # Image Generation models
    ("openrouter", "openai/dall-e-3", "DALL-E 3", 10, 8, "heavy", 5, 200, None, None, "Flexible", None, False, True, False, False, False, False),
    ("openrouter", "openai/dall-e-2", "DALL-E 2", 7, 9, "medium", 10, 200, None, None, "Flexible", None, False, True, False, False, False, False),
    ("google", "imagen-3.0-generate-001", "Imagen 3", 9, 7, "heavy", 5, 200, None, None, "Flexible", None, False, True, False, False, False, False),
    ("stability", "stable-diffusion-3.5-large", "Stable Diffusion 3.5 Large", 8, 6, "heavy", 30, 500, None, None, "Flexible", None, False, True, False, False, False, False),
    ("stability", "stable-diffusion-3.5-medium", "Stable Diffusion 3.5 Medium", 7, 8, "medium", 30, 500, None, None, "Flexible", None, False, True, False, False, False, False),
]


async def seed():
    async with AsyncSessionLocal() as session:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # Upsert models: insert if not exists, update on conflict
        model_count = 0
        for row in CATALOG:
            stmt = pg_insert(ProviderCatalog).values(
                platform=row[0],
                model_id=row[1],
                display_name=row[2],
                intelligence_rank=row[3],
                speed_rank=row[4],
                size_label=row[5],
                rpm_limit=row[6],
                rpd_limit=row[7],
                tpm_limit=row[8],
                tpd_limit=row[9],
                monthly_token_budget=row[10],
                context_window=row[11],
                supports_vision=row[12],
                supports_image_gen=row[13],
                supports_audio_stt=row[14],
                supports_audio_tts=row[15],
                supports_embeddings=row[16],
                supports_tools=row[17],
            ).on_conflict_do_update(
                constraint="uq_models_platform_model",
                set_={
                    "display_name": row[2],
                    "intelligence_rank": row[3],
                    "speed_rank": row[4],
                    "supports_vision": row[12],
                    "supports_image_gen": row[13],
                    "supports_audio_stt": row[14],
                    "supports_audio_tts": row[15],
                    "supports_embeddings": row[16],
                    "supports_tools": row[17],
                },
            )
            await session.execute(stmt)
            model_count += 1

        await session.commit()
        print(f"Synced {model_count} models.")

        # Seed fallback_config (delete all then insert for idempotency)
        from sqlalchemy import delete

        from server.modules.router.models import FallbackConfig
        from server.modules.router.schemas import PoolType

        all_models = await session.execute(
            select(ProviderCatalog).order_by(ProviderCatalog.intelligence_rank.desc())
        )
        models = all_models.scalars().all()

        await session.execute(delete(FallbackConfig))
        fallback_entries = 0
        for model in models:
            pools = ["chat"]
            if model.supports_vision:
                pools.append("vision")
            if model.supports_image_gen:
                pools.append("image_gen")
            if model.supports_embeddings:
                pools.append("embed")
            if model.supports_tools:
                pools.append("chat_tools")

            for pool in pools:
                priority = 0 if pool in ("image_gen", "embed") else (model.intelligence_rank * -1 + 100)
                session.add(FallbackConfig(
                    model_db_id=model.id,
                    pool=pool,
                    priority=priority,
                    enabled=True,
                ))
                fallback_entries += 1

        await session.commit()
        print(f"Synced {fallback_entries} fallback config entries.")


if __name__ == "__main__":
    asyncio.run(seed())
