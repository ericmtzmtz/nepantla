# ruff: noqa: E501
"""Catalog sync engine: fetch, parse, and apply overrides for models.dev catalog."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import yaml

CATALOG_URL = "https://models.dev/catalog.json"
CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "catalog_cache.json"
CACHE_TTL_HOURS = 24
DEFAULT_OVERRIDES_PATH = Path("config/providers.yaml")


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=CACHE_TTL_HOURS)


def _read_cache() -> dict | None:
    if not _cache_valid():
        return None
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(data: dict):
    _ensure_cache_dir()
    CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


async def fetch_catalog(force: bool = False) -> dict:
    """Fetch catalog.json from models.dev or local cache."""
    if not force:
        cached = _read_cache()
        if cached is not None:
            return cached

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(CATALOG_URL)
        resp.raise_for_status()
        data = resp.json()

    _write_cache(data)
    return data


def invalidate_cache():
    """Delete the local catalog cache."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()


def parse_providers(catalog: dict) -> list[dict]:
    """Extract provider entries from catalog.json."""
    providers_raw = catalog.get("providers", catalog.get("data", catalog))
    if isinstance(providers_raw, dict):
        providers_raw = list(providers_raw.values())

    result = []
    for p in providers_raw:
        if not isinstance(p, dict):
            continue
        pid = p.get("id", "")
        if not pid:
            continue

        npm = p.get("npm", "")
        base_url = p.get("api")
        is_native = base_url is None

        entry = {
            "id": pid,
            "name": p.get("name", pid),
            "base_url": base_url,
            "timeout_ms": 30000,
            "extra_headers": None,
            "is_native": is_native,
            "npm_package": npm,
            "free_tier": False,
        }

        models_raw = p.get("models", {})
        if isinstance(models_raw, dict):
            for m in models_raw.values():
                if isinstance(m, dict):
                    cost = m.get("cost", {})
                    if isinstance(cost, dict) and cost.get("input", 1) == 0 and cost.get("output", 1) == 0:
                        entry["free_tier"] = True
                        break

        result.append(entry)

    return result


def parse_models(catalog: dict) -> list[dict]:
    """Extract model entries from catalog.json."""
    providers_raw = catalog.get("providers", catalog.get("data", catalog))
    if isinstance(providers_raw, dict):
        providers_raw = list(providers_raw.values())

    result = []
    for p in providers_raw:
        if not isinstance(p, dict):
            continue
        pid = p.get("id", "")
        if not pid:
            continue

        models_raw = p.get("models", {})
        if not isinstance(models_raw, dict):
            continue

        for mid, m in models_raw.items():
            if not isinstance(m, dict):
                continue

            name = m.get("name", mid)
            modalities = m.get("modalities", {})
            inputs = modalities.get("input", []) if isinstance(modalities, dict) else []
            cost = m.get("cost", {})
            free = isinstance(cost, dict) and cost.get("input", 1) == 0 and cost.get("output", 1) == 0

            entry = {
                "platform": pid,
                "model_id": mid,
                "display_name": name,
                "context_window": m.get("limit", {}).get("context") if isinstance(m.get("limit"), dict) else None,
                "supports_vision": "image" in inputs or "pdf" in inputs,
                "supports_embeddings": "embed" in mid.lower() or m.get("family") == "text-embedding",
                "free_tier": free,
                "intelligence_rank": 0,
                "speed_rank": 0,
                "size_label": "",
                "supports_image_gen": False,
                "supports_audio_stt": False,
                "supports_audio_tts": False,
                "enabled": True,
            }
            result.append(entry)

    return result


def load_overrides(path: Path | None = None) -> dict:
    """Load local provider overrides from YAML file."""
    path = path or DEFAULT_OVERRIDES_PATH
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        overrides = (data or {}).get("overrides", {})
        return overrides if isinstance(overrides, dict) else {}
    except (yaml.YAMLError, OSError):
        return {}


def apply_overrides(providers: list[dict], overrides: dict) -> list[dict]:
    """Merge local overrides into parsed provider entries."""
    result = []
    for p in providers:
        pid = p["id"]
        if pid in overrides:
            p.update(overrides[pid])
        result.append(p)
    return result
