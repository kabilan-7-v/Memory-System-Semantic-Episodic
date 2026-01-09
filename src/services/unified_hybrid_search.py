"""
Unified Hybrid Search with RRF (Reciprocal Rank Fusion)
Combines Vector Search + BM25 + Redis Cache for both Semantic and Episodic memory
Stores unified user context (persona + knowledge + process) in single Redis index
"""
from typing import List, Dict, Any, Optional, Tuple
import json
import time
from datetime import datetime
from collections import defaultdict
import numpy as np

# Import dependencies
REDIS_AVAILABLE = False
EmbeddingService = None

try:
    from src.services.redis_common_client import get_redis
    REDIS_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Redis unavailable: {e}")
    get_redis = lambda: None

try:
    from src.services.embedding_service import EmbeddingService as ES
    EmbeddingService = ES
except Exception as e:
    print(f"⚠️  EmbeddingService unavailable: {e}")
    # Fallback dummy class
    class EmbeddingService:
        def embed_text(self, text: str):
            return np.random.rand(384)

try:
    from src.config.database import db_config
except Exception as e:
    print(f"⚠️  Database config unavailable: {e}")
    db_config = None


class UnifiedHybridSearch:
    """
    Unified hybrid search with RRF algorithm for both semantic and episodic memory
    - Stores user context in single Redis index: user_context:{user_id}
    - Combines persona, knowledge, and conversation process
    - Uses RRF (Reciprocal Rank Fusion) for ranking
    - Provides search percentage metrics
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        k_rrf: int = 60  # RRF constant (typically 60)
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.k_rrf = k_rrf  # RRF parameter
        self.redis_client = get_redis() if REDIS_AVAILABLE else None
        
    # ========== Redis Unified User Context ==========
    
    def cache_user_context(
        self,
        user_id: str,
        persona: Optional[Dict[str, Any]] = None,
        knowledge: Optional[List[Dict[str, Any]]] = None,
        recent_queries: Optional[List[str]] = None
    ) -> bool:
        """
        Store unified user context in single Redis index
        Format: user_context:{user_id}
        Contains: persona + knowledge + process in single string
        """
        if not self.redis_client:
            return False
        
        try:
            # Build unified context string
            context_parts = []
            
            # 1. Persona information
            if persona:
                persona_str = f"USER_PROFILE: {persona.get('name', 'Unknown')}"
                if persona.get('interests'):
                    persona_str += f" | Interests: {', '.join(persona['interests'][:5])}"
                if persona.get('expertise_areas'):
                    persona_str += f" | Expertise: {', '.join(persona['expertise_areas'][:5])}"
                context_parts.append(persona_str)
            
            # 2. Knowledge snippets
            if knowledge:
                knowledge_texts = []
                for k in knowledge[:10]:  # Top 10 knowledge items
                    if isinstance(k, dict):
                        title = k.get('title', '')
                        content = k.get('content', '')
                        knowledge_texts.append(f"{title}: {content[:100]}")
                if knowledge_texts:
                    context_parts.append("KNOWLEDGE: " + " | ".join(knowledge_texts))
            
            # 3. Recent query process
            if recent_queries:
                queries_str = "RECENT_QUERIES: " + " | ".join(recent_queries[-5:])
                context_parts.append(queries_str)
            
            # Combine into single indexed string
            unified_context = " || ".join(context_parts)
            
            # Generate embedding
            embedding = self.embedding_service.embed_text(unified_context)
            if isinstance(embedding, list):
                embedding_list = embedding
            elif isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            
            # Store in Redis with metadata
            context_key = f"user_context:{user_id}"
            context_data = {
                "unified_text": unified_context,
                "persona": json.dumps(persona) if persona else "{}",
                "knowledge_count": len(knowledge) if knowledge else 0,
                "queries_count": len(recent_queries) if recent_queries else 0,
                "cached_at": datetime.now().isoformat(),
                "embedding": json.dumps(embedding_list)
            }
            
            self.redis_client.hset(context_key, mapping=context_data)
            self.redis_client.expire(context_key, 3600)  # 1 hour TTL
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to cache user context: {e}")
            return False
    
    def get_cached_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve unified user context from Redis"""
        if not self.redis_client:
            return None
        
        try:
            context_key = f"user_context:{user_id}"
            data = self.redis_client.hgetall(context_key)
            
            if not data:
                return None
            
            return {
                "unified_text": data.get('unified_text', ''),
                "persona": json.loads(data.get('persona', '{}')),
                "knowledge_count": int(data.get('knowledge_count', 0)),
                "queries_count": int(data.get('queries_count', 0)),
                "cached_at": data.get('cached_at', ''),
                "embedding": np.array(json.loads(data.get('embedding', '[]')))
            }
        except Exception as e:
            print(f"❌ Failed to get user context: {e}")
            return None
    
    def cache_user_input(
        self,
        user_id: str,
        query: str,
        input_type: str = "query"  # query, command, chat
    ) -> bool:
        """
        Cache user input in single Redis index
        Format: user_input:{user_id}:{timestamp}
        """
        if not self.redis_client:
            return False
        
        try:
            timestamp = int(time.time())
            input_key = f"user_input:{user_id}:{timestamp}"
            
            # Generate embedding for the input
            embedding = self.embedding_service.embed_text(query)
            if isinstance(embedding, list):
                embedding_list = embedding
            elif isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            
            input_data = {
                "query": query,
                "type": input_type,
                "created_at": datetime.now().isoformat(),
                "embedding": json.dumps(embedding_list)
            }
            
            self.redis_client.hset(input_key, mapping=input_data)
            self.redis_client.expire(input_key, 1800)  # 30 min TTL
            
            # Add to user's recent queries list
            queries_key = f"user_queries:{user_id}"
            self.redis_client.rpush(queries_key, query)
            self.redis_client.ltrim(queries_key, -20, -1)  # Keep last 20
            self.redis_client.expire(queries_key, 3600)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to cache user input: {e}")
            return False
    
    # ========== RRF (Reciprocal Rank Fusion) Algorithm ==========
    
    def rrf_score(self, rank: int) -> float:
        """
        Calculate RRF score for a given rank
        RRF formula: 1 / (k + rank)
        where k is typically 60
        """
        return 1.0 / (self.k_rrf + rank)
    
    def reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[int, float]],
        bm25_results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """
        Combine vector and BM25 results using Reciprocal Rank Fusion
        
        Args:
            vector_results: List of (id, score) from vector search
            bm25_results: List of (id, score) from BM25 search
        
        Returns:
            List of (id, rrf_score) sorted by RRF score descending
        """
        rrf_scores = defaultdict(float)
        
        # Add RRF scores from vector search
        for rank, (item_id, _) in enumerate(vector_results, start=1):
            rrf_scores[item_id] += self.vector_weight * self.rrf_score(rank)
        
        # Add RRF scores from BM25 search
        for rank, (item_id, _) in enumerate(bm25_results, start=1):
            rrf_scores[item_id] += self.bm25_weight * self.rrf_score(rank)
        
        # Sort by RRF score descending
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results
    
    # ========== Hybrid Search with Metrics ==========
    
    def hybrid_search_semantic(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.0,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Hybrid search for semantic memory (knowledge base)
        Returns results with search percentage metrics
        """
        start_time = time.time()
        
        # 1. Check Redis cache first
        cache_hit = False
        cached_context = None
        if user_id and self.redis_client:
            cached_context = self.get_cached_user_context(user_id)
            if cached_context:
                cache_hit = True
        
        # 2. Vector search
        query_embedding = self.embedding_service.embed_text(query)
        vector_results = self._vector_search_knowledge(
            query_embedding, user_id, limit * 2, category, tags
        )
        
        # 3. BM25 search
        bm25_results = self._bm25_search_knowledge(
            query, user_id, limit * 2, category, tags
        )
        
        # 4. Apply RRF
        rrf_results = self.reciprocal_rank_fusion(vector_results, bm25_results)
        
        # 5. Fetch full records and add scores
        final_results = []
        for item_id, rrf_score in rrf_results[:limit]:
            if rrf_score < min_score:
                continue
            
            record = self._get_knowledge_record(item_id)
            if record:
                # Find original scores
                vector_score = next((s for id, s in vector_results if id == item_id), 0.0)
                bm25_score = next((s for id, s in bm25_results if id == item_id), 0.0)
                
                final_results.append({
                    **record,
                    "rrf_score": round(rrf_score, 4),
                    "vector_score": round(vector_score, 4),
                    "bm25_score": round(bm25_score, 4),
                    "vector_percentage": round(vector_score * 100, 2),
                    "bm25_percentage": round(bm25_score * 100, 2),
                    "combined_percentage": round(rrf_score * 100, 2)
                })
        
        search_time = time.time() - start_time
        
        return {
            "results": final_results,
            "metrics": {
                "cache_hit": cache_hit,
                "total_results": len(final_results),
                "vector_candidates": len(vector_results),
                "bm25_candidates": len(bm25_results),
                "rrf_k": self.k_rrf,
                "vector_weight": self.vector_weight,
                "bm25_weight": self.bm25_weight,
                "search_time_ms": round(search_time * 1000, 2)
            }
        }
    
    def hybrid_search_episodic(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Hybrid search for episodic memory (chat messages)
        Returns results with search percentage metrics
        """
        start_time = time.time()
        
        # 1. Check Redis STM cache
        cache_results = self._check_episodic_cache(user_id, query)
        
        # 2. Vector search on episodes
        query_embedding = self.embedding_service.embed_text(query)
        vector_results = self._vector_search_episodes(
            query_embedding, user_id, limit * 2
        )
        
        # 3. BM25 search on messages
        bm25_results = self._bm25_search_episodes(query, user_id, limit * 2)
        
        # 4. Apply RRF
        rrf_results = self.reciprocal_rank_fusion(vector_results, bm25_results)
        
        # 5. Fetch full records
        final_results = []
        for item_id, rrf_score in rrf_results[:limit]:
            if rrf_score < min_score:
                continue
            
            record = self._get_episode_record(item_id)
            if record:
                vector_score = next((s for id, s in vector_results if id == item_id), 0.0)
                bm25_score = next((s for id, s in bm25_results if id == item_id), 0.0)
                
                final_results.append({
                    **record,
                    "rrf_score": round(rrf_score, 4),
                    "vector_score": round(vector_score, 4),
                    "bm25_score": round(bm25_score, 4),
                    "vector_percentage": round(vector_score * 100, 2),
                    "bm25_percentage": round(bm25_score * 100, 2),
                    "combined_percentage": round(rrf_score * 100, 2)
                })
        
        search_time = time.time() - start_time
        
        return {
            "results": final_results,
            "cache_results": cache_results,
            "metrics": {
                "cache_hits": len(cache_results) if cache_results else 0,
                "total_results": len(final_results),
                "vector_candidates": len(vector_results),
                "bm25_candidates": len(bm25_results),
                "rrf_k": self.k_rrf,
                "search_time_ms": round(search_time * 1000, 2)
            }
        }
    
    # ========== Internal Search Methods ==========
    
    def _vector_search_knowledge(
        self,
        embedding: np.ndarray,
        user_id: Optional[str],
        limit: int,
        category: Optional[str],
        tags: Optional[List[str]]
    ) -> List[Tuple[int, float]]:
        """Vector search in knowledge base"""
        try:
            with db_config.get_cursor() as cursor:
                conditions = []
                params = [embedding.tolist()]
                
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                if category:
                    conditions.append("category = %s")
                    params.append(category)
                if tags:
                    conditions.append("tags && %s")
                    params.append(tags)
                
                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                
                sql = f"""
                    SELECT id, 1 - (embedding <=> %s::vector) AS similarity
                    FROM knowledge_base
                    WHERE embedding IS NOT NULL AND {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                
                params.append(embedding.tolist())
                params.append(limit)
                
                cursor.execute(sql, params)
                return [(row['id'], float(row['similarity'])) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return []
    
    def _bm25_search_knowledge(
        self,
        query: str,
        user_id: Optional[str],
        limit: int,
        category: Optional[str],
        tags: Optional[List[str]]
    ) -> List[Tuple[int, float]]:
        """BM25 full-text search in knowledge base"""
        try:
            with db_config.get_cursor() as cursor:
                conditions = []
                params = [query, query]
                
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                if category:
                    conditions.append("category = %s")
                    params.append(category)
                if tags:
                    conditions.append("tags && %s")
                    params.append(tags)
                
                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                
                sql = f"""
                    SELECT id, ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) AS rank
                    FROM knowledge_base
                    WHERE content_tsv @@ plainto_tsquery('english', %s) AND {where_clause}
                    ORDER BY rank DESC
                    LIMIT %s
                """
                
                params.append(limit)
                
                cursor.execute(sql, params)
                return [(row['id'], float(row['rank'])) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ BM25 search error: {e}")
            return []
    
    def _vector_search_episodes(
        self,
        embedding: np.ndarray,
        user_id: str,
        limit: int
    ) -> List[Tuple[int, float]]:
        """Vector search in episodic memory"""
        try:
            with db_config.get_cursor() as cursor:
                sql = """
                    SELECT id, 1 - (vector <=> %s::vector) AS similarity
                    FROM episodes
                    WHERE user_id = %s AND vector IS NOT NULL
                    ORDER BY vector <=> %s::vector
                    LIMIT %s
                """
                cursor.execute(sql, (embedding.tolist(), user_id, embedding.tolist(), limit))
                return [(row['id'], float(row['similarity'])) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ Episode vector search error: {e}")
            return []
    
    def _bm25_search_episodes(
        self,
        query: str,
        user_id: str,
        limit: int
    ) -> List[Tuple[int, float]]:
        """BM25 search in chat messages"""
        try:
            with db_config.get_cursor() as cursor:
                sql = """
                    SELECT DISTINCT scm.super_chat_id AS id,
                           ts_rank_cd(to_tsvector('english', scm.content), 
                                     plainto_tsquery('english', %s), 32) AS rank
                    FROM super_chat_messages scm
                    JOIN super_chat sc ON scm.super_chat_id = sc.id
                    WHERE sc.user_id = %s
                      AND to_tsvector('english', scm.content) @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                """
                cursor.execute(sql, (query, user_id, query, limit))
                return [(row['id'], float(row['rank'])) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ Episode BM25 search error: {e}")
            return []
    
    def _get_knowledge_record(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full knowledge record by ID"""
        try:
            with db_config.get_cursor() as cursor:
                cursor.execute("SELECT * FROM knowledge_base WHERE id = %s", (item_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except:
            return None
    
    def _get_episode_record(self, episode_id: int) -> Optional[Dict[str, Any]]:
        """Fetch episode record by ID"""
        try:
            with db_config.get_cursor() as cursor:
                cursor.execute("SELECT * FROM episodes WHERE id = %s", (episode_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except:
            return None
    
    def _check_episodic_cache(self, user_id: str, query: str) -> Optional[List[Dict[str, Any]]]:
        """Check episodic STM cache in Redis"""
        if not self.redis_client:
            return None
        
        try:
            # Look for recent STM entries
            keys = self.redis_client.keys(f"episodic:stm:{user_id}:*")
            if not keys:
                return None
            
            results = []
            for key in keys[:5]:  # Check last 5
                data = self.redis_client.hgetall(key)
                if data:
                    results.append({
                        "content": data.get('context', ''),
                        "query": data.get('query', ''),
                        "source": "redis_cache"
                    })
            return results if results else None
        except:
            return None
