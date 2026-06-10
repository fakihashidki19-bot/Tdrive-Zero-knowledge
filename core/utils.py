"""
TDrive Utility Module.

Provides helper functions for file I/O, hashing, and path management.
Designed to handle large files efficiently using streaming.
"""

import hashlib
import os
from pathlib import Path
from typing import Generator


def get_file_sha256(file_path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Calculates the SHA256 hash of a file using a streaming approach.

    Args:
        file_path: Path to the file.
        chunk_size: Buffer size for reading (default 1MB).

    Returns:
        The hex-encoded SHA256 hash.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_bytes_sha256(data: bytes) -> str:
    """
    Calculates the SHA256 hash of a byte string.

    Args:
        data: The bytes to hash.

    Returns:
        The hex-encoded SHA256 hash.
    """
    return hashlib.sha256(data).hexdigest()


def chunk_file_iterator(
    file_path: str | Path, chunk_size: int
) -> Generator[bytes, None, None]:
    """
    Iterates over a file and yields chunks of a specific size.

    Args:
        file_path: Path to the file.
        chunk_size: The size of each chunk in bytes.

    Yields:
        Chunks of bytes from the file.
    """
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            yield chunk


def get_file_size(file_path: str | Path) -> int:
    """
    Returns the size of a file in bytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in bytes.
    """
    return os.path.getsize(file_path)


def ensure_dir(dir_path: str | Path) -> Path:
    """
    Ensures a directory exists, creating it if necessary.

    Args:
        dir_path: Path to the directory.

    Returns:
        Path object of the directory.
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_path_join(base_dir: str | Path, *parts: str) -> Path:
    """
    Joins path parts securely.

    Args:
        base_dir: The base directory.
        parts: Path components to join.

    Returns:
        The resulting Path object.
    """
    return Path(base_dir).joinpath(*parts).resolve()
