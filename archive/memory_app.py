#!/usr/bin/env python3
"""
Simple Interactive Memory System
- Input text manually to store in database
- Ask questions to retrieve stored memories
"""
import os
import sys
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment
load_dotenv()


class MemoryApp:
    """Simple memory storage and retrieval app"""
    
    def __init__(self):
        self.conn = None
        self.user_id = "default_user"
        self.connect_db()
    
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
            print("[DB] Connected to database")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            sys.exit(1)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate deterministic embedding from text"""
        # Use SHA-256 hash to create deterministic 1536-dimensional vector
        embedding = []
        for i in range(1536):
            seed = text.encode('utf-8') + i.to_bytes(4, 'big')
            hash_val = hashlib.sha256(seed).digest()
            int_val = int.from_bytes(hash_val[:8], byteorder='big')
            normalized = (int_val % 2000000) / 1000000.0 - 1.0
            embedding.append(normalized)
        
        # Normalize to unit vector
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        else:
            embedding = [1.0 / (1536 ** 0.5)] * 1536
        
        return embedding
    
    def add_memory(self, content: str, title: str = None, category: str = "general", tags: List[str] = None):
        """Add a memory to the database"""
        if not content.strip():
            print("[ERROR] Content cannot be empty")
            return None
        
        try:
            # Generate title if not provided
            if not title:
                title = content[:50] + ("..." if len(content) > 50 else "")
            
            # Generate embedding
            embedding = self.generate_embedding(content)
            
            # Insert into database
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_base (
                    user_id, title, content, category, tags, embedding,
                    content_type, source, importance_score
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                self.user_id,
                title,
                content,
                category,
                tags or [],
                embedding,
                'text',
                'manual_input',
                0.8
            ))
            
            result = cursor.fetchone()
            self.conn.commit()
            
            print(f"[SUCCESS] Memory added (ID: {result['id']})")
            print(f"   Title: {title}")
            print(f"   Category: {category}")
            return result['id']
            
        except Exception as e:
            self.conn.rollback()
            print(f"[ERROR] Failed to add memory: {e}")
            return None
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search memories using hybrid approach (keyword + semantic)"""
        if not query.strip():
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            cursor = self.conn.cursor()
            
            # Hybrid search: BM25 + Vector similarity
            cursor.execute("""
                WITH bm25_search AS (
                    SELECT 
                        id,
                        title,
                        content,
                        category,
                        tags,
                        importance_score,
                        created_at,
                        ts_rank_cd(content_tsv, websearch_to_tsquery('english', %s)) as bm25_score
                    FROM knowledge_base
                    WHERE user_id = %s
                        AND content_tsv @@ websearch_to_tsquery('english', %s)
                ),
                vector_search AS (
                    SELECT 
                        id,
                        title,
                        content,
                        category,
                        tags,
                        importance_score,
                        created_at,
                        1 - (embedding <=> %s::vector) as vector_score
                    FROM knowledge_base
                    WHERE user_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                )
                SELECT DISTINCT
                    COALESCE(b.id, v.id) as id,
                    COALESCE(b.title, v.title) as title,
                    COALESCE(b.content, v.content) as content,
                    COALESCE(b.category, v.category) as category,
                    COALESCE(b.tags, v.tags) as tags,
                    COALESCE(b.importance_score, v.importance_score) as importance_score,
                    COALESCE(b.created_at, v.created_at) as created_at,
                    COALESCE(b.bm25_score, 0) as bm25_score,
                    COALESCE(v.vector_score, 0) as vector_score,
                    (COALESCE(b.bm25_score, 0) * 0.3 + COALESCE(v.vector_score, 0) * 0.7) as hybrid_score
                FROM bm25_search b
                FULL OUTER JOIN vector_search v ON b.id = v.id
                ORDER BY hybrid_score DESC
                LIMIT %s
            """, (
                query, self.user_id, query,
                query_embedding, self.user_id, query_embedding, limit * 2,
                limit
            ))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_answer(self, content: str, query: str) -> str:
        """Extract specific answer from content based on query"""
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Split content into sentences
        sentences = [s.strip() for s in content.replace('?', '.').replace('!', '.').split('.') if s.strip()]
        
        # Question patterns and what to extract
        patterns = {
            'name': ['name', 'called', 'who am i', 'who are you'],
            'age': ['age', 'old', 'years'],
            'location': ['live', 'location', 'where', 'city', 'place', 'from'],
            'work': ['work', 'job', 'profession', 'career', 'do for', 'occupation'],
            'hobby': ['hobby', 'hobbies', 'enjoy', 'like to do', 'interests'],
            'education': ['education', 'study', 'studied', 'degree', 'school', 'college', 'university'],
            'phone': ['phone', 'number', 'contact', 'mobile', 'call'],
            'email': ['email', 'mail', 'contact'],
        }
        
        # Find which pattern matches the query
        matched_keywords = []
        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in query_lower:
                    matched_keywords.extend(keywords)
                    break
        
        # Find sentences containing matched keywords or query words
        query_words = set(query_lower.split()) - {'what', 'is', 'my', 'your', 'the', 'a', 'an', 'tell', 'me', 'about', 'where', 'when', 'how', 'who', 'do', 'you', 'i', 'am', 'are'}
        
        best_sentence = None
        best_score = 0
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = 0
            
            # Score based on matched keywords
            for keyword in matched_keywords:
                if keyword in sentence_lower:
                    score += 2
            
            # Score based on query words
            for word in query_words:
                if word in sentence_lower:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        # Return best sentence or first sentence if no good match
        if best_sentence and best_score > 0:
            return best_sentence
        
        # If content is short, return it all
        if len(content) < 100:
            return content
        
        # Return first sentence as fallback
        return sentences[0] if sentences else content[:100]
    
    def display_results(self, results: List[Dict[str, Any]], query: str = "", show_answer: bool = True):
        """Display search results"""
        if not results:
            print("\n[INFO] No memories found")
            print("[TIP] Make sure you've added memories first using the 'add' command")
            return
        
        # Show direct answer for high-confidence results
        if show_answer and results[0]['hybrid_score'] > 0.3:
            answer = self.extract_answer(results[0]['content'], query)
            print(f"\n[ANSWER] {answer}")
            print(f"         (Confidence: {results[0]['hybrid_score']:.1%})")
        
        print(f"\n[RESULTS] Found {len(results)} relevant memories:\n")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result['title']}")
            print(f"    Category: {result['category']}")
            if result.get('tags'):
                print(f"    Tags: {', '.join(result['tags'])}")
            print(f"    Score: {result['hybrid_score']:.4f} (Keyword: {result['bm25_score']:.4f}, Semantic: {result['vector_score']:.4f})")
            print(f"\n    {result['content']}")
            print("-" * 80)
    
    def show_stats(self):
        """Show database statistics"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT category) as categories,
                MAX(created_at) as last_added
            FROM knowledge_base
            WHERE user_id = %s
        """, (self.user_id,))
        
        stats = cursor.fetchone()
        print(f"\n[STATS] Database Statistics:")
        print(f"   Total memories: {stats['total']}")
        print(f"   Categories: {stats['categories']}")
        if stats['last_added']:
            print(f"   Last added: {stats['last_added']}")
    
    def interactive_mode(self):
        """Run interactive mode"""
        print("\n" + "=" * 80)
        print(" " * 30 + "MEMORY SYSTEM")
        print("=" * 80)
        print("\n[INFO] Interactive Memory System")
        print("\nCommands:")
        print("   add       - Add a new memory")
        print("   search    - Search for memories")
        print("   stats     - Show statistics")
        print("   quit      - Exit")
        print("\nQuick Actions:")
        print("   Type a question (what/who/where/when/why/how) to search instantly")
        print("   Type text (>10 chars) to store it as a memory")
        print("=" * 80)
        
        self.show_stats()
        
        while True:
            try:
                print("\n")
                user_input = input(">>> ").strip()
                
                if not user_input:
                    continue
                
                # Commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n[INFO] Goodbye!\n")
                    break
                
                elif user_input.lower() == 'stats':
                    self.show_stats()
                
                elif user_input.lower() == 'add':
                    print("\n[ADD MEMORY]")
                    content = input("Content: ").strip()
                    if content:
                        title = input("Title (press Enter to auto-generate): ").strip()
                        category = input("Category (default: general): ").strip() or "general"
                        tags_input = input("Tags (comma-separated): ").strip()
                        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []
                        
                        self.add_memory(content, title or None, category, tags)
                
                elif user_input.lower() == 'search':
                    query = input("Search query: ").strip()
                    if query:
                        results = self.search_memories(query)
                        self.display_results(results)
                
                # Direct question - search immediately
                elif '?' in user_input or any(word in user_input.lower() for word in ['what', 'who', 'where', 'when', 'why', 'how', 'tell', 'show']):
                    print(f"\n[SEARCHING] {user_input}")
                    results = self.search_memories(user_input)
                    self.display_results(results)
                
                # Direct input - treat as memory to store
                elif len(user_input) > 10:  # Avoid storing very short inputs
                    response = input(f"[CONFIRM] Store this as a memory? (y/n): ").strip().lower()
                    if response == 'y':
                        self.add_memory(user_input)
                
                else:
                    print("[INFO] Type 'add' to add memory, 'search' to search, or 'stats' for statistics")
                
            except KeyboardInterrupt:
                print("\n\n[INFO] Goodbye!\n")
                break
            except EOFError:
                print("\n\n[INFO] Goodbye!\n")
                break
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[DB] Connection closed")


def main():
    """Main entry point"""
    app = MemoryApp()
    try:
        app.interactive_mode()
    finally:
        app.close()


if __name__ == "__main__":
    main()
