#!/usr/bin/env python3
"""
Real-time Memory System
Handles live conversations and hybrid search retrieval from memory (DB).
"""
import os
import psycopg2
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

class RealtimeMemorySystem:
    """Real-time interaction and hybrid search memory system."""
    
    def __init__(self):
        self.conn = self._get_connection()
    
    def _get_connection(self):
        """Create database connection."""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5435'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres'),
            database=os.getenv('DB_NAME', 'semantic_memory')
        )
    
    def generate_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """Generate embedding vector (mock - replace with actual embedding model)."""
        vec = np.random.randn(dim)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()
    
    # =========================================================================
    # REAL-TIME INTERACTION STORAGE
    # =========================================================================
    
    def store_conversation(self, user_id: str, user_message: str, 
                          assistant_response: str, 
                          conversation_type: str = 'super_chat') -> Dict:
        """
        Store real-time conversation in memory system.
        
        Args:
            user_id: User identifier
            user_message: User's message
            assistant_response: Assistant's response
            conversation_type: 'super_chat' or 'deepdive'
        
        Returns:
            Dictionary with stored message IDs and metadata
        """
        cur = self.conn.cursor()
        
        try:
            if conversation_type == 'super_chat':
                # Get or create super chat for user
                cur.execute("""
                    SELECT id FROM super_chat WHERE user_id = %s
                """, (user_id,))
                
                result = cur.fetchone()
                if result:
                    super_chat_id = result[0]
                else:
                    cur.execute("""
                        INSERT INTO super_chat (user_id) 
                        VALUES (%s) RETURNING id
                    """, (user_id,))
                    super_chat_id = cur.fetchone()[0]
                
                # Store user message
                cur.execute("""
                    INSERT INTO super_chat_messages 
                    (super_chat_id, role, content, created_at, episodized)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (super_chat_id, 'user', user_message, datetime.now(), False))
                
                user_msg_id, user_timestamp = cur.fetchone()
                
                # Store assistant response
                cur.execute("""
                    INSERT INTO super_chat_messages 
                    (super_chat_id, role, content, created_at, episodized)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (super_chat_id, 'assistant', assistant_response, datetime.now(), False))
                
                assistant_msg_id, assistant_timestamp = cur.fetchone()
                
                self.conn.commit()
                
                return {
                    'status': 'success',
                    'conversation_type': 'super_chat',
                    'super_chat_id': super_chat_id,
                    'user_message_id': user_msg_id,
                    'assistant_message_id': assistant_msg_id,
                    'stored_at': datetime.now().isoformat(),
                    'message': '✓ Conversation stored in super_chat_messages table'
                }
            
            else:  # deepdive
                # For deepdive, you'd need conversation_id passed in
                # This is a simplified version
                return {
                    'status': 'error',
                    'message': 'Deepdive requires conversation_id parameter'
                }
        
        except Exception as e:
            self.conn.rollback()
            return {
                'status': 'error',
                'message': f'Failed to store conversation: {str(e)}'
            }
        finally:
            cur.close()
    
    def store_knowledge(self, user_id: str, content: str, 
                       category: str = 'knowledge', 
                       tags: List[str] = None,
                       importance: float = 0.5) -> Dict:
        """
        Store new knowledge in knowledge base.
        
        Args:
            user_id: User identifier
            content: Knowledge content
            category: 'knowledge', 'skill', or 'process'
            tags: List of tags
            importance: Importance score (0.0 to 1.0)
        
        Returns:
            Dictionary with stored knowledge ID and metadata
        """
        cur = self.conn.cursor()
        
        try:
            embedding = self.generate_embedding(content)
            
            cur.execute("""
                INSERT INTO knowledge_base 
                (user_id, content, category, tags, importance_score, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                user_id,
                content,
                category,
                tags or [],
                importance,
                embedding,
                '{"source": "real_time_interaction"}'
            ))
            
            knowledge_id, created_at = cur.fetchone()
            self.conn.commit()
            
            return {
                'status': 'success',
                'knowledge_id': knowledge_id,
                'stored_at': created_at.isoformat(),
                'message': '✓ Knowledge stored in knowledge_base table'
            }
        
        except Exception as e:
            self.conn.rollback()
            return {
                'status': 'error',
                'message': f'Failed to store knowledge: {str(e)}'
            }
        finally:
            cur.close()
    
    # =========================================================================
    # HYBRID SEARCH (Vector + Full-Text)
    # =========================================================================
    
    def hybrid_search(self, query: str, user_id: Optional[str] = None, 
                     limit: int = 10, search_type: str = 'all') -> Dict:
        """
        Hybrid search combining vector similarity and full-text search.
        
        Args:
            query: Search query
            user_id: Optional user filter
            limit: Maximum results
            search_type: 'episodes', 'knowledge', 'messages', or 'all'
        
        Returns:
            Dictionary with search results from different sources
        """
        query_embedding = self.generate_embedding(query)
        results = {'query': query, 'results': {}}
        
        cur = self.conn.cursor()
        
        try:
            # Search in Episodes (Episodic Memory)
            if search_type in ['episodes', 'all']:
                results['results']['episodes'] = self._search_episodes(
                    cur, query, query_embedding, user_id, limit
                )
            
            # Search in Knowledge Base (Semantic Memory)
            if search_type in ['knowledge', 'all']:
                results['results']['knowledge'] = self._search_knowledge(
                    cur, query, query_embedding, user_id, limit
                )
            
            # Search in Recent Messages (Working Memory)
            if search_type in ['messages', 'all']:
                results['results']['recent_messages'] = self._search_messages(
                    cur, query, user_id, limit
                )
            
            results['status'] = 'success'
            results['total_results'] = sum(
                len(v) for v in results['results'].values()
            )
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            results['total_results'] = 0
        finally:
            cur.close()
        
        return results
    
    def _search_episodes(self, cur, query: str, embedding: List[float], 
                        user_id: Optional[str], limit: int) -> List[Dict]:
        """Search in episodes using hybrid approach."""
        sql = """
            SELECT 
                id,
                user_id,
                source_type,
                message_count,
                date_from,
                date_to,
                messages,
                1 - (vector <=> %s::vector) AS similarity_score
            FROM episodes
            WHERE 1=1
        """
        params = [embedding]
        
        if user_id:
            sql += " AND user_id = %s"
            params.append(user_id)
        
        sql += """
            ORDER BY similarity_score DESC
            LIMIT %s
        """
        params.append(limit)
        
        cur.execute(sql, params)
        
        results = []
        for row in cur.fetchall():
            results.append({
                'id': row[0],
                'user_id': row[1],
                'source_type': row[2],
                'message_count': row[3],
                'date_from': row[4].isoformat() if row[4] else None,
                'date_to': row[5].isoformat() if row[5] else None,
                'preview': str(row[6])[:200] + '...' if len(str(row[6])) > 200 else str(row[6]),
                'similarity_score': float(row[7]),
                'source': 'episodes'
            })
        
        return results
    
    def _search_knowledge(self, cur, query: str, embedding: List[float],
                         user_id: Optional[str], limit: int) -> List[Dict]:
        """Search in knowledge base using hybrid approach."""
        sql = """
            SELECT 
                id,
                user_id,
                content,
                category,
                tags,
                importance_score,
                1 - (embedding <=> %s::vector) AS similarity_score,
                ts_rank(content_tsv, plainto_tsquery('english', %s)) AS text_rank
            FROM knowledge_base
            WHERE 1=1
        """
        params = [embedding, query]
        
        if user_id:
            sql += " AND user_id = %s"
            params.append(user_id)
        
        # Hybrid scoring: 70% vector similarity + 30% text rank
        sql += """
            ORDER BY (
                (1 - (embedding <=> %s::vector)) * 0.7 +
                ts_rank(content_tsv, plainto_tsquery('english', %s)) * 0.3
            ) DESC
            LIMIT %s
        """
        params.extend([embedding, query, limit])
        
        cur.execute(sql, params)
        
        results = []
        for row in cur.fetchall():
            results.append({
                'id': row[0],
                'user_id': row[1],
                'content': row[2],
                'category': row[3],
                'tags': row[4],
                'importance_score': float(row[5]) if row[5] else None,
                'similarity_score': float(row[6]),
                'text_rank': float(row[7]),
                'combined_score': float(row[6]) * 0.7 + float(row[7]) * 0.3,
                'source': 'knowledge_base'
            })
        
        return results
    
    def _search_messages(self, cur, query: str, user_id: Optional[str], 
                        limit: int) -> List[Dict]:
        """Search in recent messages (last 24 hours)."""
        sql = """
            SELECT 
                scm.id,
                sc.user_id,
                scm.role,
                scm.content,
                scm.created_at,
                ts_rank(to_tsvector('english', scm.content), 
                       plainto_tsquery('english', %s)) AS rank
            FROM super_chat_messages scm
            JOIN super_chat sc ON sc.id = scm.super_chat_id
            WHERE to_tsvector('english', scm.content) @@ plainto_tsquery('english', %s)
        """
        params = [query, query]
        
        if user_id:
            sql += " AND sc.user_id = %s"
            params.append(user_id)
        
        sql += """
            ORDER BY rank DESC, scm.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        cur.execute(sql, params)
        
        results = []
        for row in cur.fetchall():
            results.append({
                'id': row[0],
                'user_id': row[1],
                'role': row[2],
                'content': row[3],
                'timestamp': row[4].isoformat() if row[4] else None,
                'text_rank': float(row[5]),
                'source': 'messages'
            })
        
        return results
    
    # =========================================================================
    # CONTEXT RETRIEVAL FOR AI
    # =========================================================================
    
    def get_relevant_context(self, query: str, user_id: str, 
                            max_tokens: int = 2000) -> Dict:
        """
        Get relevant context for AI response generation.
        Combines recent conversation, relevant knowledge, and past episodes.
        
        Args:
            query: Current user query
            user_id: User identifier
            max_tokens: Maximum context length (approximate)
        
        Returns:
            Dictionary with organized context for AI
        """
        context = {
            'query': query,
            'user_id': user_id,
            'context_sections': {}
        }
        
        cur = self.conn.cursor()
        
        try:
            # 1. Recent conversation (last 10 messages)
            cur.execute("""
                SELECT role, content, created_at
                FROM super_chat_messages scm
                JOIN super_chat sc ON sc.id = scm.super_chat_id
                WHERE sc.user_id = %s
                ORDER BY scm.created_at DESC
                LIMIT 10
            """, (user_id,))
            
            recent = []
            for row in cur.fetchall():
                recent.append({
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2].isoformat() if row[2] else None
                })
            context['context_sections']['recent_conversation'] = list(reversed(recent))
            
            # 2. Relevant knowledge (top 5)
            search_results = self.hybrid_search(
                query, user_id, limit=5, search_type='knowledge'
            )
            context['context_sections']['relevant_knowledge'] = (
                search_results.get('results', {}).get('knowledge', [])
            )
            
            # 3. Related episodes (top 3)
            search_results = self.hybrid_search(
                query, user_id, limit=3, search_type='episodes'
            )
            context['context_sections']['related_episodes'] = (
                search_results.get('results', {}).get('episodes', [])
            )
            
            context['status'] = 'success'
            context['timestamp'] = datetime.now().isoformat()
            
        except Exception as e:
            context['status'] = 'error'
            context['error'] = str(e)
        finally:
            cur.close()
        
        return context
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def demo_realtime_interaction():
    """Demonstrate real-time interaction storage."""
    print("=" * 70)
    print("Real-time Interaction Demo")
    print("=" * 70)
    
    memory = RealtimeMemorySystem()
    
    # Example 1: Store a conversation
    print("\n1. Storing a real-time conversation...")
    result = memory.store_conversation(
        user_id='user_001',
        user_message='How do I optimize PostgreSQL queries?',
        assistant_response='Here are key techniques for PostgreSQL optimization: 1) Use EXPLAIN ANALYZE, 2) Create proper indexes, 3) Optimize joins...'
    )
    print(f"   {result['message']}")
    print(f"   Message IDs: {result['user_message_id']}, {result['assistant_message_id']}")
    
    # Example 2: Store knowledge
    print("\n2. Storing new knowledge...")
    result = memory.store_knowledge(
        user_id='user_001',
        content='Advanced Python decorators for caching and memoization',
        category='skill',
        tags=['python', 'performance', 'optimization'],
        importance=0.8
    )
    print(f"   {result['message']}")
    print(f"   Knowledge ID: {result['knowledge_id']}")
    
    memory.close()

def demo_hybrid_search():
    """Demonstrate hybrid search retrieval."""
    print("\n" + "=" * 70)
    print("Hybrid Search Demo")
    print("=" * 70)
    
    memory = RealtimeMemorySystem()
    
    # Search across all memory types
    print("\n1. Searching for 'API design best practices'...")
    results = memory.hybrid_search(
        query='API design best practices',
        user_id='user_001',
        limit=5,
        search_type='all'
    )
    
    print(f"   Status: {results['status']}")
    print(f"   Total results: {results['total_results']}")
    
    if results['results'].get('knowledge'):
        print(f"\n   Knowledge results: {len(results['results']['knowledge'])}")
        for i, item in enumerate(results['results']['knowledge'][:3], 1):
            print(f"   {i}. {item['content'][:80]}...")
            print(f"      Score: {item['combined_score']:.3f} (sim: {item['similarity_score']:.3f}, text: {item['text_rank']:.3f})")
    
    if results['results'].get('episodes'):
        print(f"\n   Episode results: {len(results['results']['episodes'])}")
        for i, item in enumerate(results['results']['episodes'][:2], 1):
            print(f"   {i}. {item['source_type']} - {item['message_count']} messages")
            print(f"      Score: {item['similarity_score']:.3f}")
    
    memory.close()

def demo_context_retrieval():
    """Demonstrate context retrieval for AI."""
    print("\n" + "=" * 70)
    print("Context Retrieval Demo")
    print("=" * 70)
    
    memory = RealtimeMemorySystem()
    
    print("\n1. Getting relevant context for AI response...")
    context = memory.get_relevant_context(
        query='How do I implement caching in my application?',
        user_id='user_001'
    )
    
    print(f"   Status: {context['status']}")
    print(f"   Recent conversation: {len(context['context_sections']['recent_conversation'])} messages")
    print(f"   Relevant knowledge: {len(context['context_sections']['relevant_knowledge'])} items")
    print(f"   Related episodes: {len(context['context_sections']['related_episodes'])} episodes")
    
    memory.close()


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("REALTIME MEMORY SYSTEM - Interactive Demo")
    print("=" * 70)
    
    demo_realtime_interaction()
    demo_hybrid_search()
    demo_context_retrieval()
    
    print("\n" + "=" * 70)
    print("✓ Demo completed!")
    print("=" * 70)
