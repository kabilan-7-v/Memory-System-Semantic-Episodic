# redis_semantic_cache.py
"""
Redis-based Semantic Memory Cache
Caches user personas, knowledge base queries, and semantic search results
"""
import time
import json
import numpy as np
from typing import List, Dict, Optional, Any
from src.services.redis_semantic_client import get_redis_semantic
from src.services.embedding_service import EmbeddingService

embedder = EmbeddingService()
r = get_redis_semantic()

# Index names
PERSONA_INDEX = "semantic_persona_idx"
KNOWLEDGE_INDEX = "semantic_knowledge_idx"

# Cache configuration
PERSONA_TTL = 3600  # 1 hour for personas
KNOWLEDGE_TTL = 1800  # 30 minutes for knowledge
MAX_KNOWLEDGE_ITEMS = 10  # Max cached knowledge items per user
SIM_THRESHOLD = 0.85  # Similarity threshold for cache hits


def _prune_knowledge(user_id: str):
    """Keep only MAX_KNOWLEDGE_ITEMS most recent knowledge cache entries"""
    keys = sorted(r.keys(f"semantic:knowledge:{user_id}:*"))
    for k in keys[:-MAX_KNOWLEDGE_ITEMS]:
        r.delete(k)


# ========== User Persona Caching ==========

def cache_persona(user_id: str, persona_data: Dict[str, Any]) -> None:
    """
    Cache user persona in Redis
    
    Args:
        user_id: User identifier
        persona_data: Full persona dict with name, interests, expertise, etc.
    """
    try:
        # Generate embedding for semantic search
        persona_text = f"{persona_data.get('name', '')} {' '.join(persona_data.get('interests', []))} {' '.join(persona_data.get('expertise_areas', []))}"
        embedding = embedder.embed_text(persona_text)
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
        
        key = f"semantic:persona:{user_id}"
        
        # Store persona with embedding
        r.hset(key, mapping={
            "user_id": user_id,
            "data": json.dumps(persona_data),
            "embedding": embedding_bytes,
            "cached_at": time.time()
        })
        
        r.expire(key, PERSONA_TTL)
        print(f"💾 Cached persona: {user_id}")
    except Exception as e:
        print(f"⚠️  Failed to cache persona: {e}")


def get_cached_persona(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached user persona
    
    Returns:
        Persona dict if cached and valid, None otherwise
    """
    try:
        key = f"semantic:persona:{user_id}"
        
        if not r.exists(key):
            return None
        
        data = r.hget(key, "data")
        if data:
            # Refresh TTL on access
            r.expire(key, PERSONA_TTL)
            print(f"⚡ Persona cache HIT: {user_id}")
            return json.loads(data.decode('utf-8'))
        
        return None
    except Exception as e:
        print(f"⚠️  Failed to retrieve cached persona: {e}")
        return None


def invalidate_persona_cache(user_id: str) -> None:
    """Invalidate persona cache when updated"""
    try:
        key = f"semantic:persona:{user_id}"
        r.delete(key)
        print(f"🗑️  Invalidated persona cache: {user_id}")
    except Exception as e:
        print(f"⚠️  Failed to invalidate persona cache: {e}")


# ========== Knowledge Base Caching ==========

def cache_knowledge_search(user_id: str, query: str, results: List[Dict[str, Any]]) -> None:
    """
    Cache knowledge search results with semantic matching
    
    Args:
        user_id: User identifier
        query: Search query text
        results: List of knowledge items found
    """
    try:
        # Generate query embedding
        query_embedding = embedder.embed_text(query)
        query_vec_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
        
        key = f"semantic:knowledge:{user_id}:{int(time.time())}"
        
        # Store query and results
        r.hset(key, mapping={
            "query": query,
            "query_vector": query_vec_bytes,
            "results": json.dumps(results),
            "cached_at": time.time()
        })
        
        r.expire(key, KNOWLEDGE_TTL)
        _prune_knowledge(user_id)
        print(f"💾 Cached knowledge search: {user_id} - {query[:50]}...")
    except Exception as e:
        print(f"⚠️  Failed to cache knowledge search: {e}")


def search_knowledge_cache(user_id: str, query: str, k: int = 3) -> Optional[List[Dict[str, Any]]]:
    """
    Search for similar cached knowledge queries
    
    Args:
        user_id: User identifier
        query: Search query text
        k: Number of results to consider
        
    Returns:
        Cached results if similar query found, None otherwise
    """
    try:
        # Generate query embedding
        query_embedding = embedder.embed_text(query)
        query_vec = np.array(query_embedding, dtype=np.float32)
        
        # Get all cached knowledge for this user
        keys = r.keys(f"semantic:knowledge:{user_id}:*")
        
        if not keys:
            return None
        
        best_similarity = 0.0
        best_results = None
        
        # Compare with cached queries
        for key in keys:
            cached_vec_bytes = r.hget(key, "query_vector")
            if not cached_vec_bytes:
                continue
            
            # Calculate cosine similarity
            cached_vec = np.frombuffer(cached_vec_bytes, dtype=np.float32)
            similarity = np.dot(query_vec, cached_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(cached_vec)
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                results_data = r.hget(key, "results")
                if results_data:
                    best_results = json.loads(results_data.decode('utf-8'))
                    # Refresh TTL on hit
                    r.expire(key, KNOWLEDGE_TTL)
        
        # Return if above threshold
        if best_similarity >= SIM_THRESHOLD and best_results:
            print(f"⚡ Knowledge cache HIT: similarity={round(best_similarity, 3)}")
            return best_results
        
        return None
    except Exception as e:
        print(f"⚠️  Failed to search knowledge cache: {e}")
        return None


def invalidate_knowledge_cache(user_id: str) -> None:
    """Invalidate all knowledge cache for a user"""
    try:
        keys = r.keys(f"semantic:knowledge:{user_id}:*")
        if keys:
            r.delete(*keys)
            print(f"🗑️  Invalidated knowledge cache: {user_id} ({len(keys)} entries)")
    except Exception as e:
        print(f"⚠️  Failed to invalidate knowledge cache: {e}")


# ========== Cache Statistics ==========

def get_cache_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get cache statistics"""
    try:
        stats = {
            "total_personas": 0,
            "total_knowledge": 0,
            "user_stats": {}
        }
        
        if user_id:
            # User-specific stats
            persona_key = f"semantic:persona:{user_id}"
            knowledge_keys = r.keys(f"semantic:knowledge:{user_id}:*")
            
            stats["user_stats"][user_id] = {
                "persona_cached": r.exists(persona_key),
                "knowledge_entries": len(knowledge_keys),
                "persona_ttl": r.ttl(persona_key) if r.exists(persona_key) else 0
            }
        else:
            # Global stats
            all_personas = r.keys("semantic:persona:*")
            all_knowledge = r.keys("semantic:knowledge:*")
            
            stats["total_personas"] = len(all_personas)
            stats["total_knowledge"] = len(all_knowledge)
        
        return stats
    except Exception as e:
        print(f"⚠️  Failed to get cache stats: {e}")
        return {"error": str(e)}


# ========== Cache Management ==========

def clear_all_semantic_cache() -> None:
    """Clear all semantic memory cache (use with caution!)"""
    try:
        persona_keys = r.keys("semantic:persona:*")
        knowledge_keys = r.keys("semantic:knowledge:*")
        
        total = len(persona_keys) + len(knowledge_keys)
        
        if persona_keys:
            r.delete(*persona_keys)
        if knowledge_keys:
            r.delete(*knowledge_keys)
        
        print(f"🗑️  Cleared all semantic cache: {total} entries")
    except Exception as e:
        print(f"⚠️  Failed to clear cache: {e}")
