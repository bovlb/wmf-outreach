"""Isolated cache for API tests; no running Redis server is required."""
from unittest.mock import AsyncMock

import pytest

from app.cache.redis import cache


@pytest.fixture
def memory_cache(monkeypatch):
    entries = {}

    async def get(key, max_age):
        return entries.get(key), False

    async def set_value(key, data, ttl):
        entries[key] = data

    monkeypatch.setattr(cache, "get", get)
    monkeypatch.setattr(cache, "set", set_value)
    monkeypatch.setattr(cache, "connect", AsyncMock())
    monkeypatch.setattr(cache, "disconnect", AsyncMock())
    return entries
