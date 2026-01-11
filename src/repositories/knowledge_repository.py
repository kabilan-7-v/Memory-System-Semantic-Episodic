"""
Knowledge Base Repository - Database operations for knowledge items
NOW WITH METADATA FILTERING SUPPORT
"""
from typing import List, Optional, Dict, Any, Union
import json
from datetime import datetime
from src.config.database import db_config
from src.models.semantic_memory import KnowledgeItem, SearchResult
from src.services.metadata_filter import (
    MetadataFilterEngine,
    MetadataFilter,
    FilterGroup
)


class KnowledgeRepository:
    """Repository for knowledge base CRUD operations"""
    
    def __init__(self):
        """Initialize repository with metadata filter engine"""
        self.filter_engine = MetadataFilterEngine()
    
    def create(self, knowledge: KnowledgeItem) -> KnowledgeItem:
        """Create a new knowledge item"""
        with db_config.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO knowledge_base (
                    user_id, title, content, content_type, category,
                    tags, embedding, source, confidence_score,
                    importance_score, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, updated_at
            """, (
                knowledge.user_id,
                knowledge.title,
                knowledge.content,
                knowledge.content_type,
                knowledge.category,
                knowledge.tags,
                knowledge.embedding,
                knowledge.source,
                knowledge.confidence_score,
                knowledge.importance_score,
                json.dumps(knowledge.metadata)
            ))
            
            result = cursor.fetchone()
            knowledge.id = str(result['id'])
            knowledge.created_at = result['created_at']
            knowledge.updated_at = result['updated_at']
            
            return knowledge
    
    def get_by_id(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """Get knowledge item by ID"""
        with db_config.get_cursor() as cursor:
            cursor.execute("""
                UPDATE knowledge_base
                SET last_accessed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (knowledge_id,))
            
            cursor.execute("""
                SELECT * FROM knowledge_base WHERE id = %s
            """, (knowledge_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_knowledge(row)
    
    def update(self, knowledge: KnowledgeItem) -> KnowledgeItem:
        """Update an existing knowledge item"""
        with db_config.get_cursor() as cursor:
            cursor.execute("""
                UPDATE knowledge_base
                SET title = %s, content = %s, content_type = %s,
                    category = %s, tags = %s, embedding = %s,
                    source = %s, confidence_score = %s,
                    importance_score = %s, metadata = %s
                WHERE id = %s
                RETURNING updated_at
            """, (
                knowledge.title,
                knowledge.content,
                knowledge.content_type,
                knowledge.category,
                knowledge.tags,
                knowledge.embedding,
                knowledge.source,
                knowledge.confidence_score,
                knowledge.importance_score,
                json.dumps(knowledge.metadata),
                knowledge.id
            ))
            
            result = cursor.fetchone()
            if result:
                knowledge.updated_at = result['updated_at']
            
            return knowledge
    
    def delete(self, knowledge_id: str) -> bool:
        """Delete a knowledge item"""
        with db_config.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM knowledge_base WHERE id = %s
            """, (knowledge_id,))
            
            return cursor.rowcount > 0
    
    def search_by_vector(
        self,
        embedding: List[float],
        user_id: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.7,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search knowledge items by vector similarity using HNSW index"""
        conditions = ["1 - (embedding <=> %s::vector) >= %s"]
        params = [embedding, min_similarity]
        
        if user_id is not None:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            params.append(user_id)
        
        if category:
            conditions.append("category = %s")
            params.append(category)
        
        if tags:
            conditions.append("tags && %s")
            params.append(tags)
        
        where_clause = " AND ".join(conditions)
        
        with db_config.get_cursor() as cursor:
            # Set ef_search for HNSW index quality/speed tradeoff
            cursor.execute("SET LOCAL hnsw.ef_search = 100")
            
            cursor.execute(f"""
                SELECT *,
                    1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_base
                WHERE {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, [embedding] + params + [embedding, limit])
            
            results = []
            for row in cursor.fetchall():
                result = SearchResult(
                    item=self._row_to_knowledge(row),
                    score=float(row['similarity']),
                    rank=len(results) + 1
                )
                results.append(result)
            
            return results
    
    def search_by_bm25(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge items using BM25-style full-text search
        Uses PostgreSQL's ts_rank_cd for BM25-like ranking
        """
        conditions = ["content_tsv @@ plainto_tsquery('english', %s)"]
        params = [query]
        
        if user_id is not None:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            params.append(user_id)
        
        if category:
            conditions.append("category = %s")
            params.append(category)
        
        if tags:
            conditions.append("tags && %s")
            params.append(tags)
        
        where_clause = " AND ".join(conditions)
        
        with db_config.get_cursor() as cursor:
            cursor.execute(f"""
                SELECT *,
                    ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) AS bm25_score
                FROM knowledge_base
                WHERE {where_clause}
                ORDER BY bm25_score DESC
                LIMIT %s
            """, [query] + params + [limit])
            
            return [dict(row) for row in cursor.fetchall()]
    
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        limit: int = 10,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 and vector similarity
        Returns results with combined scores
        """
        conditions = []
        vector_params = [query_embedding]
        bm25_params = [query]
        
        if user_id is not None:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            vector_params.append(user_id)
            bm25_params.append(user_id)
        
        if category:
            conditions.append("category = %s")
            vector_params.append(category)
            bm25_params.append(category)
        
        if tags:
            conditions.append("tags && %s")
            vector_params.append(tags)
            bm25_params.append(tags)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        with db_config.get_cursor() as cursor:
            # Set HNSW search parameters
            cursor.execute("SET LOCAL hnsw.ef_search = 100")
            
            # Combined query with both BM25 and vector scores
            cursor.execute(f"""
                WITH vector_scores AS (
                    SELECT 
                        id,
                        1 - (embedding <=> %s::vector) AS vector_score
                    FROM knowledge_base
                    WHERE {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                ),
                bm25_scores AS (
                    SELECT 
                        id,
                        ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) AS bm25_score
                    FROM knowledge_base
                    WHERE content_tsv @@ plainto_tsquery('english', %s)
                        AND {where_clause}
                    ORDER BY bm25_score DESC
                    LIMIT %s
                )
                SELECT 
                    k.*,
                    COALESCE(v.vector_score, 0) AS vector_score,
                    COALESCE(b.bm25_score, 0) AS bm25_score,
                    (%s * COALESCE(b.bm25_score, 0) + %s * COALESCE(v.vector_score, 0)) AS hybrid_score
                FROM knowledge_base k
                LEFT JOIN vector_scores v ON k.id = v.id
                LEFT JOIN bm25_scores b ON k.id = b.id
                WHERE (v.id IS NOT NULL OR b.id IS NOT NULL)
                ORDER BY hybrid_score DESC
                LIMIT %s
            """, (
                query_embedding, query_embedding, limit * 2,
                query, query, limit * 2,
                bm25_weight, vector_weight,
                limit
            ))
            
            return [dict(row) for row in cursor.fetchall()]
    def search_by_text(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeItem]:
        """Search knowledge items by text content"""
        conditions = ["(content ILIKE %s OR title ILIKE %s)"]
        search_term = f"%{query}%"
        params = [search_term, search_term]
        
        if user_id is not None:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            params.append(user_id)
        
        where_clause = " AND ".join(conditions)
        
        with db_config.get_cursor() as cursor:
            cursor.execute(f"""
                SELECT * FROM knowledge_base
                WHERE {where_clause}
                ORDER BY importance_score DESC, created_at DESC
                LIMIT %s
            """, params + [limit])
            
            return [self._row_to_knowledge(row) for row in cursor.fetchall()]
    
    def get_by_category(
        self,
        category: str,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[KnowledgeItem]:
        """Get knowledge items by category"""
        with db_config.get_cursor() as cursor:
            if user_id:
                cursor.execute("""
                    SELECT * FROM knowledge_base
                    WHERE category = %s AND (user_id = %s OR user_id IS NULL)
                    ORDER BY importance_score DESC
                    LIMIT %s
                """, (category, user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM knowledge_base
                    WHERE category = %s
                    ORDER BY importance_score DESC
                    LIMIT %s
                """, (category, limit))
            
            return [self._row_to_knowledge(row) for row in cursor.fetchall()]
    
    def get_by_tags(
        self,
        tags: List[str],
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[KnowledgeItem]:
        """Get knowledge items by tags"""
        with db_config.get_cursor() as cursor:
            if user_id:
                cursor.execute("""
                    SELECT * FROM knowledge_base
                    WHERE tags && %s AND (user_id = %s OR user_id IS NULL)
                    ORDER BY importance_score DESC
                    LIMIT %s
                """, (tags, user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM knowledge_base
                    WHERE tags && %s
                    ORDER BY importance_score DESC
                    LIMIT %s
                """, (tags, limit))
            
            return [self._row_to_knowledge(row) for row in cursor.fetchall()]
    
    def list_all(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[KnowledgeItem]:
        """List all knowledge items with pagination"""
        with db_config.get_cursor() as cursor:
            if user_id:
                cursor.execute("""
                    SELECT * FROM knowledge_base
                    WHERE user_id = %s OR user_id IS NULL
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM knowledge_base
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
            
            return [self._row_to_knowledge(row) for row in cursor.fetchall()]
    
    def _row_to_knowledge(self, row: Dict[str, Any]) -> KnowledgeItem:
        """Convert database row to KnowledgeItem object"""
        return KnowledgeItem(
            id=str(row['id']),
            user_id=row['user_id'],
            title=row['title'],
            content=row['content'],
            content_type=row['content_type'],
            category=row['category'],
            tags=row['tags'] or [],
            embedding=row['embedding'],
            source=row['source'],
            confidence_score=float(row['confidence_score']),
            importance_score=float(row['importance_score']),
            metadata=row['metadata'] or {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_accessed_at=row['last_accessed_at']
        )
    
    # ========== METADATA FILTERING METHODS ==========
    
    def search_with_filters(
        self,
        query: str,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        filters: Optional[Union[MetadataFilter, FilterGroup]] = None,
        limit: int = 10,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Enhanced hybrid search with metadata filtering
        
        Args:
            query: Search query text
            query_embedding: Query vector embedding
            user_id: Optional user ID filter
            filters: Metadata filters to apply
            limit: Maximum results to return
            vector_weight: Weight for vector similarity (0-1)
            bm25_weight: Weight for BM25 score (0-1)
            
        Returns:
            List of knowledge items matching filters and query
        """
        # Build base query
        base_sql = """
            SELECT *,
                1 - (embedding <=> %s::vector) as vector_similarity,
                ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) AS bm25_score,
                (%s * (1 - (embedding <=> %s::vector)) + 
                 %s * ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32)) AS hybrid_score
            FROM knowledge_base
            WHERE 1=1
        """
        
        params = [
            query_embedding, query,
            vector_weight, query_embedding,
            bm25_weight, query
        ]
        
        # Add user filter
        if user_id is not None:
            base_sql += " AND (user_id = %s OR user_id IS NULL)"
            params.append(user_id)
        
        # Add metadata filters
        if filters:
            where_clause, filter_params = self.filter_engine.to_sql_where(filters)
            base_sql += f" AND ({where_clause})"
            params.extend(filter_params.values())
        
        # Order and limit
        base_sql += " ORDER BY hybrid_score DESC LIMIT %s"
        params.append(limit)
        
        with db_config.get_cursor() as cursor:
            cursor.execute(base_sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def find_by_metadata(
        self,
        filters: Union[MetadataFilter, FilterGroup],
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[KnowledgeItem]:
        """
        Find knowledge items purely by metadata (no semantic search)
        
        Example:
            # Find high-importance engineering docs created in last 7 days
            from src.services.metadata_filter import FilterBuilder
            
            filter_group = FilterBuilder.create()
            filter_group.add_filter(FilterBuilder.equals("category", "knowledge"))
            filter_group.add_filter(FilterBuilder.greater_than("importance_score", 0.8))
            filter_group.add_filter(FilterBuilder.recent("created_at", days=7))
            filter_group.add_filter(FilterBuilder.equals("metadata.department", "engineering"))
            
            results = repo.find_by_metadata(filter_group, user_id="user_001")
        """
        base_sql = "SELECT * FROM knowledge_base WHERE 1=1"
        params = []
        
        # Add user filter
        if user_id is not None:
            base_sql += " AND (user_id = %s OR user_id IS NULL)"
            params.append(user_id)
        
        # Add metadata filters
        where_clause, filter_params = self.filter_engine.to_sql_where(filters)
        base_sql += f" AND ({where_clause})"
        params.extend(filter_params.values())
        
        # Order and limit
        base_sql += " ORDER BY importance_score DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        with db_config.get_cursor() as cursor:
            cursor.execute(base_sql, params)
            return [self._row_to_knowledge(row) for row in cursor.fetchall()]
    
    def get_filtered_stats(
        self,
        user_id: str,
        filters: Optional[Union[MetadataFilter, FilterGroup]] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for filtered knowledge items
        
        Returns count, avg importance, categories breakdown, etc.
        """
        base_sql = """
            SELECT 
                COUNT(*) as total_count,
                AVG(importance_score) as avg_importance,
                COUNT(DISTINCT category) as category_count,
                array_agg(DISTINCT category) as categories,
                MIN(created_at) as oldest_date,
                MAX(created_at) as newest_date
            FROM knowledge_base
            WHERE (user_id = %s OR user_id IS NULL)
        """
        
        params = [user_id]
        
        # Add metadata filters
        if filters:
            where_clause, filter_params = self.filter_engine.to_sql_where(filters)
            base_sql += f" AND ({where_clause})"
            params.extend(filter_params.values())
        
        with db_config.get_cursor() as cursor:
            cursor.execute(base_sql, params)
            row = cursor.fetchone()
            return dict(row) if row else {}

