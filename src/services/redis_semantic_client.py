# redis_semantic_client.py
"""
Redis client for Semantic Memory using unified Redis instance
Data is namespaced with 'semantic:' prefix
This is now just a wrapper around the common Redis client
"""
from .redis_common_client import get_redis

def get_redis_semantic():
    """
    Get Redis connection for semantic memory
    Uses unified Redis with 'semantic:' namespace
    """
    return get_redis()
