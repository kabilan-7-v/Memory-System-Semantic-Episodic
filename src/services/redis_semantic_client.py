# redis_semantic_client.py
"""
Redis client for Semantic Memory caching
Uses Redis Cloud for distributed semantic memory cache
"""
import os
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

def get_redis_semantic():
    """Get Redis connection for semantic memory (Redis Cloud)"""
    host = os.getenv("REDIS_SEMANTIC_HOST", "localhost")
    port = os.getenv("REDIS_SEMANTIC_PORT", "6379")
    password = os.getenv("REDIS_SEMANTIC_PASSWORD", "")
    db = os.getenv("REDIS_SEMANTIC_DB", "0")

    if not host or not port:
        raise RuntimeError("❌ Missing Redis Semantic env vars (REDIS_SEMANTIC_HOST, REDIS_SEMANTIC_PORT)")

    # Configure Redis connection
    kwargs = {
        "host": host,
        "port": int(port),
        "db": int(db),
        "decode_responses": False,  # REQUIRED for binary vectors
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "retry_on_timeout": True
    }
    
    # Add password if provided
    if password:
        kwargs["password"] = password

    return Redis(**kwargs)
