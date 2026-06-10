"""
TDrive Encryption Engine.

Handles AES-256-GCM encryption, PBKDF2 key derivation,
and secure random generation of nonces and salts.
"""

import os
import secrets
import hmac
import hashlib
from typing import Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


# Configuration Constants
PBKDF2_ITERATIONS = 100_000
KEY_LENGTH = 32  
NONCE_LENGTH = 12  
SALT_LENGTH = 16


class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derives a 256-bit key from a password and salt using PBKDF2-HMAC-SHA256.

    Args:
        password: The user's master password.
        salt: A 16-byte random salt.

    Returns:
        The derived 32-byte key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode())


def encrypt(data: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypts data using AES-256-GCM.

    Args:
        data: Plaintext bytes to encrypt.
        key: 32-byte AES key.

    Returns:
        A tuple of (nonce, ciphertext_with_tag).
    """
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_LENGTH)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce, ciphertext


def decrypt(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypts AES-256-GCM ciphertext.

    Args:
        nonce: The 12-byte nonce used for encryption.
        ciphertext: The ciphertext with the GCM authentication tag appended.
        key: 32-byte AES key.

    Returns:
        The decrypted plaintext bytes.

    Raises:
        CryptoError: If decryption or authentication fails.
    """
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise CryptoError("Decryption failed: Invalid tag (wrong key or corrupted data)")
    except Exception as e:
        raise CryptoError(f"Decryption failed: {str(e)}")


def generate_salt() -> bytes:
    """Generates a secure random 16-byte salt."""
    return secrets.token_bytes(SALT_LENGTH)


def sign_data(data: bytes, key: bytes) -> bytes:
    """Signs data using HMAC-SHA256."""
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_signature(data: bytes, signature: bytes, key: bytes) -> bool:
    """Verifies HMAC-SHA256 signature in constant time."""
    expected = hmac.new(key, data, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)
