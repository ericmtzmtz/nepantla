# nepantla

**Multi-pool LLM proxy. One OpenAI-compatible endpoint, many providers.**

Route requests across 17+ LLM providers from a single `/v1/chat/completions` endpoint. Auto-fallback, per-key rate limits, analytics, and a React dashboard.

## Features

- **OpenAI-compatible** — `POST /v1/chat/completions` and `GET /v1/models` work with any OpenAI SDK. Just change `base_url`.
- **Multi-pool router** — Automatic fallback across providers with priority chains, cooldowns, and sticky sessions.
- **Tool calling** — OpenAI-style `tools`/`tool_choice` passed through to providers. Google Gemini and Cohere formats translated automatically.
- **Image generation** — `POST /v1/images/generations` with auto-routing.
- **Vision** — Image URLs in messages routed to vision pool.
- **Audio** — Speech-to-text (`/v1/audio/transcriptions`) and text-to-speech (`/v1/audio/speech`).
- **Embeddings** — `/v1/embeddings` for providers that support it.
- **Streaming** — SSE for `stream: true`, JSON otherwise.
- **Per-key rate tracking** — RPM, RPD, TPM, TPD counters per (platform, model, key).
- **Encrypted key storage** — Your API keys are encrypted with AES-256-GCM before being stored in the database, never in the repo.
- **Health checks** — Periodic probes mark keys as healthy/invalid/error.
- **Analytics** — Request volume, success rate, latency, token counts, per-provider breakdowns.
- **Dashboard** — React + Vite UI for keys, fallback chain, analytics, playground, model catalog.
- **Dark mode** — Included.

## Quick start

**Prerequisites:** Python 3.12+, PostgreSQL 16, Poetry.

```bash
git clone https://github.com/ericmtzmtz/nepantla.git
cd nepantla

cp .env.example .env
# Edit .env with your DB credentials and generate an encryption key:
# python -c "import secrets; print(secrets.token_hex(32))"

poetry install
poetry run alembic upgrade head
poetry run uvicorn server.main:app --reload
```

Open http://localhost:8000 (dashboard) or http://localhost:8000/docs (API docs).

Add your provider API keys in the dashboard **Keys** page, then use any OpenAI client:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="playground")
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello"}],
)
print(resp.choices[0].message.content)
```

## Architecture

```
                    ┌──────────────────────────┐
                    │  POST /v1/chat/completions │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  proxy/api.py             │
                    │  → Parse body             │
                    │  → Classify pool           │
                    │    (chat/vision/image/     │
                    │     audio/chat_tools)      │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  RouterService            │
                    │  select_fallback(pool)    │
                    │                           │
                    │  1. Sticky session check  │
                    │  2. Fallback chain        │
                    │  3. Cooldown check        │
                    │  4. Healthy key?          │
                    │  5. Rate limit check      │
                    │  6. Return provider+key   │
                    └──────────┬───────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    ┌─────▼─────┐       ┌─────▼─────┐       ┌─────▼─────┐
    │ OpenAI    │       │ Google    │       │ Cohere    │
    │ Compat    │       │ Gemini    │       │           │
    │ (generic) │       │ (native)  │       │ (native)  │
    └───────────┘       └───────────┘       └───────────┘
```

## Supported providers

17+ providers supported — add your own API keys in the dashboard **Keys** page. See `GET /api/models` for the full catalog.

## Project structure

```
server/
├── main.py              ← FastAPI app entry point
├── core/                ← Config, DB, auth deps
├── modules/             ← Feature modules
│   ├── proxy/           ← /v1/chat/completions, images, audio
│   ├── providers/       ← Provider layer (base, openai_compat, google, cohere, cloudflare, stability)
│   ├── router/          ← Fallback chain, rate limits, cooldowns
│   ├── keys/            ← CRUD API keys + AES-256-GCM
│   ├── analytics/       ← Request log, hourly agg, dashboard endpoints
│   ├── provisioning/    ← Auto-sync from catalog
│   ├── models_view/     ← GET /api/models, GET /v1/models
│   ├── embeddings/      ← /v1/embeddings
│   └── settings/        ← Key-value settings
├── migrations/          ← Alembic versions
└── tests/               ← pytest integration + unit tests

dashboard/               ← React + Vite + Tailwind v4
```

## Tech stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.14 |
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 async |
| HTTP | httpx |
| Encryption | AES-256-GCM (cryptography) |
| Validation | Pydantic v2 |
| Frontend | React + Vite + Tailwind v4 |
| Tests | pytest + Starlette TestClient |

## License

[GNU Affero General Public License v3.0](./LICENSE)


