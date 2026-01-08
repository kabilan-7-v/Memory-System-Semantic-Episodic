#!/usr/bin/env python3
"""
Unified Memory System - Integrates Semantic and Episodic Memory
Provides common input/output interface for both memory types
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment
load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("[WARNING] Groq package not installed. Install with: pip install groq")


class UnifiedMemorySystem:
    """
    Unified Memory System combining Semantic and Episodic Memory
    
    Semantic Memory: Facts, knowledge, skills, processes, personas
    Episodic Memory: Events, interactions, experiences with temporal context
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.conn = None
        self.user_id = user_id
        self.groq_client = None
        self.connect_db()
        self.setup_groq()
    
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5435)),
                database=os.getenv('DB_NAME', 'semantic_memory'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', '2191'),
                cursor_factory=RealDictCursor
            )
            print("✓ Connected to unified memory database")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            sys.exit(1)
    
    def setup_groq(self):
        """Setup Groq API client"""
        if not GROQ_AVAILABLE:
            return
        
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
            print("✓ Groq API connected")
        else:
            print("✗ GROQ_API_KEY not found")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text"""
        if not self.groq_client:
            # Fallback: deterministic hash-based embedding
            import hashlib
            hash_val = hashlib.sha256(text.encode()).digest()
            embedding = []
            for i in range(0, len(hash_val), 2):
                int_val = int.from_bytes(hash_val[i:i+2], byteorder='big')
                normalized = (int_val / 65535.0) * 2 - 1
                embedding.append(normalized)
            
            while len(embedding) < 1536:
                embedding.extend(embedding[:1536-len(embedding)])
            return embedding[:1536]
        
        try:
            response = self.groq_client.embeddings.create(
                model="nomic-embed-text-v1.5",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return self.generate_embedding(text)  # Fallback
    
    def classify_memory_type(self, text: str) -> Dict[str, Any]:
        """
        Classify input text into memory categories
        Returns: {
            'is_semantic': bool,
            'is_episodic': bool,
            'semantic_type': str (persona/knowledge/skill/process),
            'episodic_type': str (event/interaction/observation),
            'reasoning': str
        }
        """
        if not self.groq_client:
            # Simple fallback classification
            text_lower = text.lower()
            is_event = any(word in text_lower for word in ['happened', 'did', 'went', 'saw', 'met', 'talked'])
            is_persona = any(word in text_lower for word in ["i'm", 'i am', 'my name', 'i like', 'i love'])
            
            return {
                'is_semantic': not is_event or is_persona,
                'is_episodic': is_event,
                'semantic_type': 'persona' if is_persona else 'knowledge',
                'episodic_type': 'event' if is_event else None,
                'reasoning': 'Fallback classification'
            }
        
        try:
            prompt = f"""Analyze this text and classify it for memory storage:

Text: "{text}"

Determine:
1. Is this SEMANTIC memory? (timeless facts, knowledge, skills, personal traits)
2. Is this EPISODIC memory? (time-bound events, experiences, interactions)
3. If semantic, what type: persona/knowledge/skill/process
4. If episodic, what type: event/interaction/observation

Note: Some inputs can be BOTH semantic and episodic.

Return JSON:
{{
    "is_semantic": true/false,
    "is_episodic": true/false,
    "semantic_type": "persona/knowledge/skill/process or null",
    "episodic_type": "event/interaction/observation or null",
    "reasoning": "brief explanation"
}}"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            import json
            result_text = response.choices[0].message.content
            # Extract JSON from response
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(result_text[start:end])
            
        except Exception as e:
            print(f"Classification failed: {e}")
        
        # Fallback
        return {
            'is_semantic': True,
            'is_episodic': False,
            'semantic_type': 'knowledge',
            'episodic_type': None,
            'reasoning': 'Default classification'
        }
    
    def store_memory(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Universal memory storage - automatically routes to semantic/episodic
        
        Args:
            text: The content to store
            context: Optional metadata (location, emotion, people, etc.)
        
        Returns:
            Dictionary with storage results
        """
        classification = self.classify_memory_type(text)
        embedding = self.generate_embedding(text)
        results = {
            'input': text,
            'classification': classification,
            'stored_in': []
        }
        
        # Store in Semantic Memory
        if classification['is_semantic']:
            semantic_type = classification.get('semantic_type', 'knowledge')
            
            if semantic_type == 'persona':
                persona_id = self._store_persona(text, embedding)
                results['stored_in'].append(f"semantic:persona:{persona_id}")
            else:
                knowledge_id = self._store_knowledge(text, semantic_type, embedding)
                results['stored_in'].append(f"semantic:{semantic_type}:{knowledge_id}")
        
        # Store in Episodic Memory
        if classification['is_episodic']:
            episodic_type = classification.get('episodic_type', 'event')
            episode_id = self._store_episode(text, episodic_type, embedding, context)
            results['stored_in'].append(f"episodic:{episodic_type}:{episode_id}")
        
        return results
    
    def _store_persona(self, text: str, embedding: List[float]) -> str:
        """Store in semantic memory - user_persona table"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_persona (user_id, bio, embedding)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        bio = user_persona.bio || E'\n' || EXCLUDED.bio,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                    RETURNING id
                """, (self.user_id, text, embedding))
                self.conn.commit()
                return str(cur.fetchone()['id'])
        except Exception as e:
            self.conn.rollback()
            print(f"Error storing persona: {e}")
            return "error"
    
    def _store_knowledge(self, text: str, category: str, embedding: List[float]) -> str:
        """Store in semantic memory - knowledge_base table"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_base (content, category, embedding, created_by)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (text, category, embedding, self.user_id))
                
                knowledge_id = cur.fetchone()['id']
                
                # Link to user in semantic_memory_index
                cur.execute("""
                    INSERT INTO semantic_memory_index (user_id, knowledge_id, importance_score)
                    VALUES (%s, %s, 0.8)
                """, (self.user_id, knowledge_id))
                
                self.conn.commit()
                return str(knowledge_id)
        except Exception as e:
            self.conn.rollback()
            print(f"Error storing knowledge: {e}")
            return "error"
    
    def _store_episode(self, text: str, episode_type: str, embedding: List[float], 
                      context: Optional[Dict] = None) -> str:
        """Store in episodic memory - episodes table"""
        try:
            context = context or {}
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO episodes (
                        user_id, content, episode_type, embedding,
                        location, emotion, people_involved
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.user_id, 
                    text, 
                    episode_type, 
                    embedding,
                    context.get('location'),
                    context.get('emotion'),
                    context.get('people', [])
                ))
                self.conn.commit()
                return str(cur.fetchone()['id'])
        except Exception as e:
            self.conn.rollback()
            print(f"Error storing episode: {e}")
            return "error"
    
    def search_memory(self, query: str, limit: int = 10, 
                     memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Universal memory search across both semantic and episodic
        
        Args:
            query: Search query
            limit: Maximum results
            memory_type: Optional filter ('semantic', 'episodic', or None for both)
        
        Returns:
            Unified results with scores and metadata
        """
        query_embedding = self.generate_embedding(query)
        results = []
        
        # Search Semantic Memory
        if memory_type in [None, 'semantic']:
            results.extend(self._search_semantic(query, query_embedding, limit))
        
        # Search Episodic Memory
        if memory_type in [None, 'episodic']:
            results.extend(self._search_episodic(query, query_embedding, limit))
        
        # Sort by relevance score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def _search_semantic(self, query: str, embedding: List[float], limit: int) -> List[Dict]:
        """Search semantic memory (persona + knowledge)"""
        results = []
        
        try:
            with self.conn.cursor() as cur:
                # Search knowledge_base
                cur.execute("""
                    SELECT 
                        'semantic' as memory_type,
                        category as semantic_category,
                        content,
                        1 - (embedding <=> %s::vector) as score,
                        created_at as timestamp
                    FROM knowledge_base
                    WHERE created_by = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, self.user_id, embedding, limit))
                
                for row in cur.fetchall():
                    results.append(dict(row))
                
                # Search user_persona
                cur.execute("""
                    SELECT 
                        'semantic' as memory_type,
                        'persona' as semantic_category,
                        bio as content,
                        1 - (embedding <=> %s::vector) as score,
                        updated_at as timestamp
                    FROM user_persona
                    WHERE user_id = %s
                """, (embedding, self.user_id))
                
                row = cur.fetchone()
                if row:
                    results.append(dict(row))
        
        except Exception as e:
            print(f"Semantic search error: {e}")
        
        return results
    
    def _search_episodic(self, query: str, embedding: List[float], limit: int) -> List[Dict]:
        """Search episodic memory (episodes)"""
        results = []
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        'episodic' as memory_type,
                        episode_type,
                        content,
                        1 - (embedding <=> %s::vector) as score,
                        timestamp,
                        location,
                        emotion,
                        people_involved
                    FROM episodes
                    WHERE user_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, self.user_id, embedding, limit))
                
                for row in cur.fetchall():
                    results.append(dict(row))
        
        except Exception as e:
            print(f"Episodic search error: {e}")
        
        return results
    
    def get_context(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive user context (semantic + episodic)
        """
        if query:
            results = self.search_memory(query, limit=15)
        else:
            results = self.search_memory("tell me about the user", limit=15)
        
        # Separate by type
        semantic = [r for r in results if r['memory_type'] == 'semantic']
        episodic = [r for r in results if r['memory_type'] == 'episodic']
        
        return {
            'user_id': self.user_id,
            'semantic_memories': semantic[:8],
            'episodic_memories': episodic[:7],
            'total_results': len(results)
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Interactive unified memory system"""
    print("=" * 70)
    print("🧠 UNIFIED MEMORY SYSTEM")
    print("Semantic Memory (Facts) + Episodic Memory (Events)")
    print("=" * 70)
    
    memory = UnifiedMemorySystem()
    
    print("\nCommands:")
    print("  <text>           - Store memory (auto-classified)")
    print("  search <query>   - Search all memories")
    print("  context [query]  - Get user context")
    print("  user <id>        - Switch user")
    print("  quit             - Exit")
    print("=" * 70)
    
    while True:
        try:
            user_input = input(f"\n[{memory.user_id}] > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                break
            
            elif user_input.startswith('search '):
                query = user_input[7:]
                results = memory.search_memory(query, limit=5)
                
                print(f"\n🔍 Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    mem_type = result['memory_type']
                    score = result['score'] * 100
                    content = result['content'][:100]
                    timestamp = result.get('timestamp', 'N/A')
                    
                    print(f"\n{i}. [{mem_type.upper()}] {score:.1f}% relevance")
                    print(f"   {content}...")
                    print(f"   Time: {timestamp}")
            
            elif user_input.startswith('context'):
                query = user_input[7:].strip() if len(user_input) > 7 else None
                context = memory.get_context(query)
                
                print(f"\n📊 Context for {context['user_id']}:")
                print(f"\n  Semantic Memories ({len(context['semantic_memories'])}):")
                for mem in context['semantic_memories'][:3]:
                    print(f"    • [{mem.get('semantic_category', 'N/A')}] {mem['content'][:80]}")
                
                print(f"\n  Episodic Memories ({len(context['episodic_memories'])}):")
                for mem in context['episodic_memories'][:3]:
                    print(f"    • [{mem.get('episode_type', 'N/A')}] {mem['content'][:80]}")
            
            elif user_input.startswith('user '):
                memory.user_id = user_input[5:]
                print(f"✓ Switched to user: {memory.user_id}")
            
            else:
                # Store memory
                result = memory.store_memory(user_input)
                
                print(f"\n✓ Stored in: {', '.join(result['stored_in'])}")
                print(f"  Classification: {result['classification']['reasoning']}")
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    memory.close()


if __name__ == "__main__":
    main()
