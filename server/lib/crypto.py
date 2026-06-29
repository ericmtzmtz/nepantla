import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from server.core.config import settings


def encrypt(plaintext: str) -> tuple[str, str, str]:
    """Encrypt with AES-256-GCM. Returns (ciphertext_hex, iv_hex, tag_hex)."""
    key = bytes.fromhex(settings.ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    # AESGCM returns ciphertext + tag (16 bytes) concatenated
    ct = ciphertext[:-16]
    tag = ciphertext[-16:]
    return ct.hex(), nonce.hex(), tag.hex()


def decrypt(ciphertext_hex: str, iv_hex: str, tag_hex: str) -> str:
    """Decrypt with AES-256-GCM."""
    key = bytes.fromhex(settings.ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    nonce = bytes.fromhex(iv_hex)
    ct = bytes.fromhex(ciphertext_hex) + bytes.fromhex(tag_hex)
    return aesgcm.decrypt(nonce, ct, None).decode()


def mask_key(raw: str) -> str:
    """Mask key for display: first 4 + last 4 chars."""
    if len(raw) <= 8:
        return "****" + raw[-4:]
    return raw[:4] + "..." + raw[-4:]
