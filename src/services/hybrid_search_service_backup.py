"""
Hybrid Search Service - Combines BM25 lexical search with HNSW vector search
Optimized for 10GB+ memory datasets with PostgreSQL full-text search
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from src.config.database import db_config
from src.services.embedding_service import EmbeddingService


class HybridSearchService:
    """
    Hybrid search combining:
    - BM25-style full-text search (PostgreSQL ts_rank_cd)
    - HNSW vector similarity search (pgvector)
    - Weighted combination for optimal results
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7
    ):
        """
        Initialize hybrid search service
        
        Args:
            embedding_service: Service for generating embeddings
            bm25_weight: Weight for BM25 lexical score (0-1)
            vector_weight: Weight for vector similarity score (0-1)
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        
        # Ensure weights sum to 1
        total = bm25_weight + vector_weight
        self.bm25_weight = bm25_weight / total
        self.vector_weight = vector_weight / total
 def hybrid_search(
 self,
 query: str,
 user_id: Optional[str] = None,
 limit: int = 10,
 min_score: float = 0.0,
 category: Optional[str] = None,
 tags: Optional[List[str]] = None
 ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and vector search
        
        Args:
            query: Search query text
            user_id: Optional user ID to filter results
            limit: Maximum number of results
            min_score: Minimum combined score threshold
            category: Optional category filter
            tags: Optional tags filter
        
        Returns:
            List of search results with combined scores
        """
        # Get both BM25 and vector results
        bm25_results = self._bm25_search(query, user_id, limit * 2, category, tags)
        vector_results = self._vector_search(query, user_id, limit * 2, category, tags)
        
        # Combine and rank results
        combined = self._combine_results(bm25_results, vector_results)
        
        # Filter by minimum score and limit
        filtered = [r for r in combined if r['hybrid_score'] >= min_score]
        return sorted(filtered, key=lambda x: x['hybrid_score'], reverse=True)[:limit]
 def _bm25_search(
 self,
 query: str,
 user_id: Optional[str] = None,
 limit: int = 20,
 category: Optional[str] = None,
 tags: Optional[List[str]] = None
 ) -> List[Dict[str, Any]]:
        """
        BM25-style full-text search using PostgreSQL ts_rank_cd
        
        This uses PostgreSQL's built-in text search with:
        - Weighted ranking (title: weight A, content: weight B)
        - ts_rank_cd for BM25-like ranking
        """
        with db_config.get_cursor() as cursor:
            # Build query conditions
            conditions = []
            params = []
            
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
            
            # Prepare the tsquery
            params.insert(0, query)
            
            sql = f"""
                SELECT 
                    id,
                    user_id,
                    title,
                    content,
                    category,
                    tags,
                    content_type,
                    confidence_score,
                    importance_score,
                    metadata,
                    created_at,
                    ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) AS bm25_score
                FROM knowledge_base
                WHERE content_tsv @@ plainto_tsquery('english', %s)
                    AND {where_clause}
                ORDER BY bm25_score DESC
                LIMIT %s
            """
            
            params.append(query)
            params.extend(params[1:-1]) # Add condition params again
            params.append(limit)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
 def _vector_search(
 self,
 query: str,
 user_id: Optional[str] = None,
 limit: int = 20,
 category: Optional[str] = None,
 tags: Optional[List[str]] = None
 ) -> List[Dict[str, Any]]:
        """
        Vector similarity search using HNSW index
        
        Uses pgvector's HNSW index for efficient nearest neighbor search
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        with db_config.get_cursor() as cursor:
            # Build query conditions
            conditions = []
            params = []
            
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
            
            # Use cosine similarity with HNSW index
            # Set ef_search parameter for search-time quality/speed tradeoff
            cursor.execute("SET LOCAL hnsw.ef_search = 100")
            
            sql = f"""
                SELECT 
                    id,
                    user_id,
                    title,
                    content,
                    category,
                    tags,
                    content_type,
                    confidence_score,
                    importance_score,
                    metadata,
                    created_at,
                    1 - (embedding <=> %s::vector) AS vector_score
                FROM knowledge_base
                WHERE {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            
            all_params = [query_embedding] + params + [query_embedding, limit]
            cursor.execute(sql, all_params)
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
 def _combine_results(
 self,
 bm25_results: List[Dict[str, Any]],
 vector_results: List[Dict[str, Any]]
 ) -> List[Dict[str, Any]]:
        """
        Combine BM25 and vector search results using weighted scoring
        
        Uses Reciprocal Rank Fusion (RRF) combined with weighted scores
        """
        # Normalize scores for BM25 results
        if bm25_results:
            max_bm25 = max(r['bm25_score'] for r in bm25_results)
            if max_bm25 > 0:
                for r in bm25_results:
                    r['normalized_bm25'] = float(r['bm25_score']) / max_bm25
            else:
                for r in bm25_results:
                    r['normalized_bm25'] = 0.0
        
        # Create a dictionary to merge results by ID
        merged: Dict[str, Dict[str, Any]] = {}
        
        # Add BM25 results
        for rank, result in enumerate(bm25_results, 1):
            doc_id = str(result['id'])
            merged[doc_id] = {
                **result,
                'bm25_rank': rank,
                'bm25_rrf': 1.0 / (rank + 60), # RRF with k=60
                'vector_score': 0.0,
                'vector_rank': None,
                'vector_rrf': 0.0
            }
 # Add/merge vector results
 for rank, result in enumerate(vector_results, 1):
 doc_id = str(result['id'])
 vector_rrf = 1.0 / (rank + 60)
 
 if doc_id in merged:
 merged[doc_id]['vector_score'] = float(result['vector_score'])
 merged[doc_id]['vector_rank'] = rank
 merged[doc_id]['vector_rrf'] = vector_rrf
 else:
 merged[doc_id] = {
 **result,
 'bm25_score': 0.0,
 'normalized_bm25': 0.0,
 'bm25_rank': None,
 'bm25_rrf': 0.0,
 'vector_rank': rank,
 'vector_rrf': vector_rrf
 }
 
 # Calculate hybrid scores
 for doc in merged.values():
 # Weighted combination of normalized scores
 weighted_score = (
 self.bm25_weight * doc['normalized_bm25'] +
 self.vector_weight * doc['vector_score']
 )
 
 # RRF combination
 rrf_score = doc['bm25_rrf'] + doc['vector_rrf']
 
 # Final hybrid score combines both
 doc['hybrid_score'] = 0.7 * weighted_score + 0.3 * rrf_score
 
 return list(merged.values())
    
    def search_knowledge(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        search_type: str = 'hybrid',
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Flexible search interface
        
        Args:
            query: Search query
            user_id: Optional user filter
            limit: Max results
            search_type: 'hybrid', 'bm25', or 'vector'
            **kwargs: Additional filters (category, tags, min_score)
        """
        if search_type == 'bm25':
            return self._bm25_search(
                query, user_id, limit,
                kwargs.get('category'), kwargs.get('tags')
            )
        elif search_type == 'vector':
            return self._vector_search(
                query, user_id, limit,
                kwargs.get('category'), kwargs.get('tags')
            )
        else: # hybrid
            return self.hybrid_search(
                query, user_id, limit,
                kwargs.get('min_score', 0.0),
                kwargs.get('category'), kwargs.get('tags')
            )
