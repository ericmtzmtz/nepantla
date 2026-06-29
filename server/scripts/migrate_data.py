"""
Migrate data from old Node.js/SQLite → new PostgreSQL.

Place your .sqlite/.db file in the project root (or set OLD_DB_PATH env var),
then run:

    poetry run python -m server.scripts.migrate_data

Skips rows already present (idempotent).
"""

import asyncio
import os
import sqlite3

from sqlalchemy import select

from server.core.database import AsyncSessionLocal
from server.lib.crypto import encrypt as py_encrypt
from server.modules.analytics.models import Request as AnalyticsRequest
from server.modules.keys.models import ApiKey
from server.modules.providers.models import ProviderCatalog
from server.modules.settings.models import Setting

OLD_DB_PATH = os.getenv("OLD_DB_PATH", "nepantla.db")
OLD_ENCRYPTION_KEY = os.getenv("OLD_ENCRYPTION_KEY", "")


def legacy_decrypt(encrypted_hex: str, iv_hex: str, tag_hex: str) -> str:
    """Decrypt a key encrypted by the old Node.js crypto (aes-256-gcm, 16-byte IV)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    key_hex = OLD_ENCRYPTION_KEY or os.getenv("OLD_ENCRYPTION_KEY", "")
    if not key_hex:
        raise ValueError("OLD_ENCRYPTION_KEY env var required to decrypt legacy keys")
    key = bytes.fromhex(key_hex)
    iv = bytes.fromhex(iv_hex)
    ct = bytes.fromhex(encrypted_hex)
    tag = bytes.fromhex(tag_hex)
    decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag)).decryptor()
    return (decryptor.update(ct) + decryptor.finalize()).decode()


def connect(db_path: str) -> sqlite3.Connection | None:
    if not os.path.exists(db_path):
        print(f"  DB not found at {db_path}, skipping.")
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_api_keys():
    conn = connect(OLD_DB_PATH)
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
    if not cursor.fetchone():
        print("  No api_keys table, skipping.")
        conn.close()
        return
    cursor.execute("SELECT * FROM api_keys")
    rows = cursor.fetchall()
    if not rows:
        print("  No API keys.")
        conn.close()
        return

    async with AsyncSessionLocal() as db:
        count = 0
        for row in rows:
            stmt = select(ApiKey).where(ApiKey.platform == row["platform"]).limit(1)
            exists = await db.execute(stmt)
            if exists.scalar_one_or_none():
                continue
            # Re-encrypt with new format
            try:
                plain = legacy_decrypt(row["encrypted_key"], row["iv"], row["auth_tag"])
            except Exception:
                print(f"  Skipping key #{row['id']} ({row['platform']}): decrypt failed")
                continue
            ct, iv, tag = py_encrypt(plain)
            key = ApiKey(
                platform=row["platform"],
                label=row["label"] if row["label"] else "",
                encrypted_key=ct,
                iv=iv,
                auth_tag=tag,
                status=row["status"] if row["status"] else "unknown",
                enabled=bool(row["enabled"]),
            )
            db.add(key)
            count += 1
        await db.commit()
        print(f"  Migrated {count} API keys (re-encrypted).")
    conn.close()


async def migrate_settings():
    conn = connect(OLD_DB_PATH)
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
    if not cursor.fetchone():
        conn.close()
        return
    cursor.execute("SELECT * FROM settings")
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return

    async with AsyncSessionLocal() as db:
        count = 0
        for row in rows:
            exists = await db.execute(select(Setting).where(Setting.key == row["key"]))
            if exists.scalar_one_or_none():
                continue
            db.add(Setting(key=row["key"], value=row["value"]))
            count += 1
        await db.commit()
        print(f"  Migrated {count} settings.")
    conn.close()


async def migrate_models():
    conn = connect(OLD_DB_PATH)
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='models'")
    if not cursor.fetchone():
        conn.close()
        return
    cursor.execute("SELECT * FROM models ORDER BY intelligence_rank ASC")
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return

    async with AsyncSessionLocal() as db:
        count = 0
        for row in rows:
            exists = await db.execute(
                select(ProviderCatalog).where(
                    ProviderCatalog.platform == row["platform"],
                    ProviderCatalog.model_id == row["model_id"],
                )
            )
            if exists.scalar_one_or_none():
                continue
            model = ProviderCatalog(
                platform=row["platform"],
                model_id=row["model_id"],
                display_name=row["display_name"],
                intelligence_rank=row["intelligence_rank"],
                speed_rank=row["speed_rank"],
                size_label=row["size_label"] if row["size_label"] else "",
                rpm_limit=row["rpm_limit"],
                rpd_limit=row["rpd_limit"],
                tpm_limit=row["tpm_limit"],
                tpd_limit=row["tpd_limit"],
                monthly_token_budget=(
                    row["monthly_token_budget"] or ""
                ),
                context_window=row["context_window"],
                enabled=bool(row["enabled"]),
            )
            db.add(model)
            count += 1
        await db.commit()
        print(f"  Migrated {count} models.")
    conn.close()


async def migrate_requests():
    conn = connect(OLD_DB_PATH)
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
    if not cursor.fetchone():
        conn.close()
        return
    cursor.execute("SELECT * FROM requests ORDER BY created_at ASC")
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return

    async with AsyncSessionLocal() as db:
        count = 0
        for row in rows:
            req = AnalyticsRequest(
                type="chat",
                platform=row["platform"],
                model_id=row["model_id"],
                status=row["status"],
                input_tokens=row["input_tokens"] if row["input_tokens"] else 0,
                output_tokens=row["output_tokens"] if row["output_tokens"] else 0,
                latency_ms=row["latency_ms"] if row["latency_ms"] else 0,
                error=row["error"] if row["error"] else None,
            )
            db.add(req)
            count += 1
            # commit every 500 to avoid memory pressure
            if count % 500 == 0:
                await db.commit()
                print(f"    {count} requests committed...")
        await db.commit()
        print(f"  Migrated {count} requests.")
    conn.close()


async def main():
    print(f"Migrating from: {OLD_DB_PATH}")
    await migrate_api_keys()
    await migrate_settings()
    await migrate_models()
    await migrate_requests()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(main())
