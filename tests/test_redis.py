"""
Redis connection tests.
"""

import pytest
from redis.asyncio import Redis


class TestRedisConnection:
    """Test Redis connectivity."""

    @pytest.mark.asyncio
    async def test_redis_connection(self, settings):
        """Test that we can connect to Redis."""
        if not settings.redis_url:
            pytest.skip("REDIS_URL not configured")

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            pong = await redis.ping()
            assert pong is True
        finally:
            await redis.close()

    @pytest.mark.asyncio
    async def test_redis_set_get(self, settings):
        """Test Redis set and get operations."""
        if not settings.redis_url:
            pytest.skip("REDIS_URL not configured")

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            # Set a test key
            await redis.set("test:key", "test_value", ex=60)

            # Get the key
            value = await redis.get("test:key")
            assert value == "test_value"

            # Clean up
            await redis.delete("test:key")
        finally:
            await redis.close()

    @pytest.mark.asyncio
    async def test_redis_json_storage(self, settings):
        """Test Redis can store JSON-like data."""
        import json

        if not settings.redis_url:
            pytest.skip("REDIS_URL not configured")

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            test_data = {"query": "test question", "response": "test answer"}

            # Store as JSON string
            await redis.set("test:json", json.dumps(test_data), ex=60)

            # Retrieve and parse
            stored = await redis.get("test:json")
            parsed = json.loads(stored)
            assert parsed["query"] == "test question"
            assert parsed["response"] == "test answer"

            # Clean up
            await redis.delete("test:json")
        finally:
            await redis.close()
