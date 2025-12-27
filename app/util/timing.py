"""Timing utilities for monitoring."""
import time
from contextlib import asynccontextmanager


@asynccontextmanager
async def timer(label: str):
    """
    Context manager for timing async operations.
    
    Args:
        label: Description of the operation
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        print(f"[TIMING] {label}: {elapsed:.3f}s")
