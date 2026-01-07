#!/usr/bin/env python3
"""
Unified Memory System: Semantic + Episodic
- Semantic: User persona, knowledge, skills, processes (long-term facts)
- Episodic: Chat conversations, time-based episodes (temporal events)
"""
import os
import sys
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
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
    """Unified semantic and episodic memory system"""
    
    def __init__(self):
        self.conn = None
        self.user_id = "default_user"
        self.groq_client = None
        self.current_chat_id = None
        self.connect_db()
        self.setup_groq()
        self.ensure_super_chat()
    
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
            print("[DB] Connected to unified memory database")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            sys.exit(1)
    
    def setup_groq(self):
        """Setup Groq API client"""
        if not GROQ_AVAILABLE:
            return
        
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
            print("[LLM] Groq API connected")
        else:
            print("[WARNING] GROQ_API_KEY not found")
    
    def ensure_super_chat(self):
        """Ensure user has an active super chat session"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id FROM super_chat 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (self.user_id,))
        
        result = cur.fetchone()
        if result:
            self.current_chat_id = result['id']
        else:
            cur.execute("""
                INSERT INTO super_chat (user_id) 
                VALUES (%s) 
                RETURNING id
            """, (self.user_id,))
            self.current_chat_id = cur.fetchone()['id']
            self.conn.commit()
        
        print(f"[EPISODIC] Super chat session: {self.current_chat_id}")
        cur.close()
    
    # ========================================================================
    # SEMANTIC MEMORY - Storage
    # ========================================================================
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Groq or fallback"""
        hash_val = hashlib.sha256(text.encode()).digest()
        embedding = []
        for i in range(0, len(hash_val) * 8, 12):
            byte_idx = i // 8
            if byte_idx >= len(hash_val):
                break
            int_val = int.from_bytes(hash_val[byte_idx:byte_idx+2], byteorder='big')
            norm_val = (int_val / 65535.0) * 2 - 1
            embedding.append(norm_val)
        
        while len(embedding) < 1536:
            embedding.append(0.0)
        
        return embedding[:1536]
    
    def classify_and_store(self, text: str) -> Dict[str, Any]:
        """Classify input and store in appropriate semantic layer"""
        if not self.groq_client:
            return {"error": "Groq not available"}
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{
                    "role": "system",
                    "content": """Classify the input into ONE category and extract information.
Return JSON:
{
  "category": "user_persona" | "knowledge" | "skill" | "process",
  "data": {
    // For user_persona: {"name": "...", "bio": "...", "interests": [], "expertise": []}
    // For knowledge: {"content": "...", "tags": []}
    // For skill: {"content": "...", "tags": []}
    // For process: {"content": "...", "tags": []}
  }
}"""
                }, {
                    "role": "user",
                    "content": text
                }],
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            classification = json.loads(result_text)
            category = classification.get("category", "knowledge")
            data = classification.get("data", {})
            
            # Store based on category
            if category == "user_persona":
                return self.store_persona(data)
            else:
                return self.store_knowledge(text, category, data.get("tags", []))
                
        except Exception as e:
            print(f"[ERROR] Classification failed: {e}")
            return self.store_knowledge(text, "knowledge", [])
    
    def store_persona(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store or update user persona"""
        cur = self.conn.cursor()
        
        embedding = self.generate_embedding(json.dumps(data))
        
        cur.execute("""
            INSERT INTO user_persona 
            (user_id, name, bio, interests, expertise, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET
                name = EXCLUDED.name,
                bio = EXCLUDED.bio,
                interests = EXCLUDED.interests,
                expertise = EXCLUDED.expertise,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            RETURNING id
        """, (
            self.user_id,
            data.get('name'),
            data.get('bio'),
            data.get('interests', []),
            data.get('expertise', []),
            embedding
        ))
        
        result_id = cur.fetchone()['id']
        self.conn.commit()
        cur.close()
        
        return {
            "status": "success",
            "type": "user_persona",
            "id": result_id,
            "message": "✓ User persona updated"
        }
    
    def store_knowledge(self, content: str, category: str = "knowledge", 
                       tags: List[str] = None) -> Dict[str, Any]:
        """Store knowledge, skill, or process"""
        cur = self.conn.cursor()
        
        embedding = self.generate_embedding(content)
        
        cur.execute("""
            INSERT INTO knowledge_base 
            (user_id, content, category, tags, embedding)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            self.user_id,
            content,
            category,
            tags or [],
            embedding
        ))
        
        knowledge_id = cur.fetchone()['id']
        
        # Create index entry
        cur.execute("""
            INSERT INTO semantic_memory_index 
            (user_id, knowledge_id)
            VALUES (%s, %s)
        """, (self.user_id, knowledge_id))
        
        self.conn.commit()
        cur.close()
        
        return {
            "status": "success",
            "type": category,
            "id": knowledge_id,
            "message": f"✓ {category.capitalize()} stored"
        }
    
    # ========================================================================
    # SEMANTIC MEMORY - Search
    # ========================================================================
    
    def search_semantic(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Hybrid semantic search across all knowledge"""
        cur = self.conn.cursor()
        
        query_embedding = self.generate_embedding(query)
        
        cur.execute("""
            SELECT 
                kb.id,
                kb.content,
                kb.category,
                kb.tags,
                kb.created_at,
                1 - (kb.embedding <=> %s::vector) as similarity
            FROM knowledge_base kb
            JOIN semantic_memory_index smi ON kb.id = smi.knowledge_id
            WHERE smi.user_id = %s
            ORDER BY kb.embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, self.user_id, query_embedding, limit))
        
        results = cur.fetchall()
        cur.close()
        
        return [dict(r) for r in results]
    
    def get_user_persona(self) -> Optional[Dict[str, Any]]:
        """Get user persona"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT name, bio, interests, expertise, created_at, updated_at
            FROM user_persona
            WHERE user_id = %s
        """, (self.user_id,))
        
        result = cur.fetchone()
        cur.close()
        
        return dict(result) if result else None
    
    # ========================================================================
    # EPISODIC MEMORY - Chat & Episodes
    # ========================================================================
    
    def add_chat_message(self, role: str, content: str):
        """Add message to current super chat"""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO super_chat_messages 
            (super_chat_id, role, content)
            VALUES (%s, %s, %s)
        """, (self.current_chat_id, role, content))
        self.conn.commit()
        cur.close()
    
    def get_recent_chat_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat messages"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT role, content, created_at
            FROM super_chat_messages
            WHERE super_chat_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (self.current_chat_id, limit))
        
        messages = cur.fetchall()
        cur.close()
        
        return [dict(m) for m in reversed(messages)]
    
    def search_episodes(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search episodic memory (past conversations)"""
        # This requires sentence-transformers embeddings
        # For now, return recent episodes
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                e.id,
                e.messages,
                e.message_count,
                e.date_from,
                e.date_to,
                e.source_type
            FROM episodes e
            WHERE e.user_id = %s
            ORDER BY e.date_from DESC
            LIMIT %s
        """, (self.user_id, limit))
        
        results = cur.fetchall()
        cur.close()
        
        return [dict(r) for r in results]
    
    # ========================================================================
    # UNIFIED CONTEXT
    # ========================================================================
    
    def get_full_context(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Get complete context: persona + semantic + episodic"""
        context = {
            "persona": self.get_user_persona(),
            "recent_chat": self.get_recent_chat_history(5),
            "semantic_memory": [],
            "episodic_memory": []
        }
        
        if query:
            context["semantic_memory"] = self.search_semantic(query, 5)
            context["episodic_memory"] = self.search_episodes(query, 3)
        
        return context
    
    def chat(self, user_message: str) -> str:
        """Chat with AI using full memory context"""
        # Store user message in episodic memory
        self.add_chat_message("user", user_message)
        
        # Get context
        context = self.get_full_context(user_message)
        
        # Build LLM context
        messages = [
            {"role": "system", "content": f"""You are an AI assistant with access to the user's complete memory.

USER PERSONA: {json.dumps(context['persona']) if context['persona'] else 'Not set'}

RELEVANT KNOWLEDGE:
{chr(10).join(f"- [{r['category']}] {r['content']}" for r in context['semantic_memory'])}

RECENT CONVERSATION:
{chr(10).join(f"{m['role']}: {m['content']}" for m in context['recent_chat'][-5:])}

Use this context to provide personalized, contextual responses."""}
        ]
        
        # Add recent chat history
        for msg in context['recent_chat']:
            messages.append({"role": msg['role'], "content": msg['content']})
        
        # Get AI response
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.7
                )
                reply = response.choices[0].message.content
            except Exception as e:
                reply = f"Error: {e}"
        else:
            reply = "Groq not available. Cannot generate response."
        
        # Store AI response in episodic memory
        self.add_chat_message("assistant", reply)
        
        return reply
    
    # ========================================================================
    # CLI Interface
    # ========================================================================
    
    def run(self):
        """Interactive CLI"""
        print("\n" + "="*70)
        print("🧠 UNIFIED MEMORY SYSTEM - Semantic + Episodic")
        print("="*70)
        print("\nCommands:")
        print("  <text>              → Store in semantic memory (auto-classified)")
        print("  chat <message>      → Chat with AI (uses full context)")
        print("  search <query>      → Search semantic memory")
        print("  episodes            → View recent episodes")
        print("  persona             → View user persona")
        print("  context [query]     → View full context")
        print("  user <id>           → Switch user")
        print("  quit                → Exit")
        print("="*70 + "\n")
        
        while True:
            try:
                user_input = input(f"[{self.user_id}] → ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "quit":
                    print("\n👋 Goodbye!\n")
                    break
                
                elif user_input.startswith("chat "):
                    message = user_input[5:].strip()
                    print(f"\n🤖 {self.chat(message)}\n")
                
                elif user_input.startswith("search "):
                    query = user_input[7:].strip()
                    results = self.search_semantic(query)
                    print(f"\n🔍 Found {len(results)} results:")
                    for r in results:
                        print(f"  [{r['category']}] {r['content'][:100]}... (score: {r['similarity']:.2f})")
                    print()
                
                elif user_input == "episodes":
                    episodes = self.search_episodes("", 5)
                    print(f"\n📚 Recent episodes: {len(episodes)}")
                    for ep in episodes:
                        print(f"  [{ep['source_type']}] {ep['message_count']} messages - {ep['date_from']}")
                    print()
                
                elif user_input == "persona":
                    persona = self.get_user_persona()
                    if persona:
                        print(f"\n👤 User Persona:")
                        for key, value in persona.items():
                            print(f"  {key}: {value}")
                    else:
                        print("\n❌ No persona set")
                    print()
                
                elif user_input.startswith("context"):
                    query = user_input[7:].strip() if len(user_input) > 7 else None
                    context = self.get_full_context(query)
                    print(f"\n📋 Full Context:")
                    print(f"  Persona: {'✓' if context['persona'] else '✗'}")
                    print(f"  Recent chat: {len(context['recent_chat'])} messages")
                    print(f"  Semantic results: {len(context['semantic_memory'])}")
                    print(f"  Episodic results: {len(context['episodic_memory'])}")
                    print()
                
                elif user_input.startswith("user "):
                    self.user_id = user_input[5:].strip()
                    self.ensure_super_chat()
                    print(f"✓ Switched to user: {self.user_id}\n")
                
                else:
                    # Store in semantic memory
                    result = self.classify_and_store(user_input)
                    print(f"  {result['message']}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    app = UnifiedMemorySystem()
    app.run()
