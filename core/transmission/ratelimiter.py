"""
TDrive Rate Limiter.

Handles throttling, jitter, and safety limits for Telegram interactions.
"""

import asyncio
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Manages concurrency and timing for Telegram operations.
    """
    
    def __init__(self, max_concurrent: int = 2, min_jitter: float = 1.0, max_jitter: float = 2.5):
        """
        Initializes the RateLimiter.

        Args:
            max_concurrent: Maximum number of concurrent Telegram operations.
            min_jitter: Minimum delay in seconds between operations.
            max_jitter: Maximum delay in seconds between operations.
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.min_jitter = min_jitter
        self.max_jitter = max_jitter

    async def wait(self):
        """Introduces a randomized delay (jitter)."""
        delay = random.uniform(self.min_jitter, self.max_jitter)
        await asyncio.sleep(delay)

    async def acquire(self):
        """Acquires the concurrency semaphore."""
        await self.semaphore.acquire()

    def release(self):
        """Releases the concurrency semaphore."""
        self.semaphore.release()
