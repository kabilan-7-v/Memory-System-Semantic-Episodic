# redis_stm.py
import time
import numpy as np
from .embeddings import EmbeddingModel
from .redis_client import get_redis

embedder = EmbeddingModel()
r = get_redis()

INDEX = "episodic_stm_idx"
TTL = 300  # 5 minutes
MAX_ITEMS = 5
SIM_THRESHOLD = 0.90


def _prune(user_id):
    """Keep only MAX_ITEMS most recent entries"""
    keys = sorted(r.keys(f"episodic:stm:{user_id}:*"))
    for k in keys[:-MAX_ITEMS]:
        r.delete(k)


def store_stm(user_id, query, context):
    """Store query and context in Redis STM cache with episodic namespace"""
    qvec = embedder.encode(query).astype(np.float32).tobytes()

    key = f"episodic:stm:{user_id}:{int(time.time())}"

    r.hset(key, mapping={
        "query": query,
        "query_vector": qvec,
        "context": "\n".join(c["content"] for c in context),
        "created_at": time.time()
    })

    r.expire(key, TTL)
    _prune(user_id)
    print(f"💾 Stored Episodic STM: {key}")


def search_stm(user_id, query, k=3):
    """
    Search for similar queries in STM cache.
    Note: Falls back to simple matching if Redis Search not available.
    """
    try:
        # Try vector search with RediSearch
        qvec = embedder.encode(query).astype(np.float32).tobytes()
        
        result = r.execute_command(
            "FT.SEARCH", INDEX,
            f"*=>[KNN {k} @query_vector $vec AS score]",
            "PARAMS", "2", "vec", qvec,
            "SORTBY", "score",
            "RETURN", "2", "context", "score",
            "DIALECT", "2"
        )
        
        if not result or result[0] == 0:
            return None

        # Parse result (format: [count, key1, fields1, key2, fields2, ...])
        best_fields = result[2]
        best_context = None
        best_score = None
        
        for i in range(0, len(best_fields), 2):
            if best_fields[i] == b'context':
                best_context = best_fields[i+1].decode('utf-8')
            elif best_fields[i] == b'score':
                best_score = float(best_fields[i+1])
        
        if best_score is None:
            return None
            
        similarity = 1 - best_score

        if similarity < SIM_THRESHOLD:
            return None

        print(f"⚡ Episodic STM HIT similarity={round(similarity, 3)}")

        return [{
            "role": "system",
            "content": best_context
        }]
        
    except Exception as e:
        # Fallback: simple key-based lookup
        print(f"⚠️  Vector search unavailable, using fallback: {e}")
        keys = r.keys(f"episodic:stm:{user_id}:*")
        if keys:
            # Get most recent entry
            latest = sorted(keys)[-1]
            stored_query = r.hget(latest, "query")
            if stored_query and query.lower() in stored_query.decode('utf-8').lower():
                context = r.hget(latest, "context")
                if context:
                    print("⚡ Episodic STM HIT (fallback match)")
                    return [{
                        "role": "system",
                        "content": context.decode('utf-8')
                    }]
        return None

