#!/usr/bin/env python3
"""
Enhanced Interactive Memory System
- Shows WHERE data is stored (Semantic/Episodic layers)
- Shows WHERE data comes FROM during retrieval
- Hybrid search across all memory types
- Real-time storage indicators
- Redis-based temporary memory cache (last 15 chats) for fast access
"""
import os
import sys
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class InteractiveMemorySystem:
    """Enhanced memory system with layer visibility and Redis-based temporary memory cache"""
    
    def __init__(self):
        self.conn = None
        self.user_id = "default_user"
        self.groq_client = None
        self.current_chat_id = None
        # Redis connection for temporary memory cache
        self.redis_client = None
        self.connect_db()
        self.connect_redis()
        self.setup_groq()
        self.ensure_super_chat()
        self.load_recent_to_temp_memory()
    
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
            print("✓ Connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)
    
    def connect_redis(self):
        """Connect to Redis for temporary memory cache (Unified Redis Cloud)"""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_db = int(os.getenv('REDIS_DB', 0))
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True,  # Return strings instead of bytes
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            print("✓ Redis connected (Unified Redis Cloud)")
        except redis.ConnectionError as e:
            print(f"⚠️  Redis not available - temporary cache disabled: {e}")
            self.redis_client = None
        except Exception as e:
            print(f"⚠️  Redis connection error: {e}")
            self.redis_client = None
    
    def setup_groq(self):
        """Setup Groq API client"""
        if not GROQ_AVAILABLE:
            return
        
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
            print("✓ Groq API connected")
    
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
        
        cur.close()
    
    def get_redis_key(self, key_suffix: str) -> str:
        """Generate Redis key with user prefix"""
        return f"temp_memory:{self.user_id}:{key_suffix}"
    
    def load_recent_to_temp_memory(self):
        """Load last 15 USER messages into Redis temporary memory cache (context only)"""
        if not self.redis_client:
            return
        
        cur = self.conn.cursor()
        cur.execute("""
            SELECT scm.role, scm.content, scm.created_at
            FROM super_chat_messages scm
            JOIN super_chat sc ON scm.super_chat_id = sc.id
            WHERE sc.user_id = %s
              AND scm.role = 'user'
            ORDER BY scm.created_at DESC
            LIMIT 15
        """, (self.user_id,))
        
        messages = cur.fetchall()
        cur.close()
        
        # Clear existing cache for this user
        cache_key = self.get_redis_key("messages")
        self.redis_client.delete(cache_key)
        
        # Add to Redis list (LPUSH for most recent first, then reverse)
        for msg in reversed(messages):
            msg_data = json.dumps({
                'role': msg['role'],
                'content': msg['content'],
                'created_at': msg['created_at'].isoformat(),
                'source': 'TEMP_MEMORY'
            })
            self.redis_client.rpush(cache_key, msg_data)
        
        # Set TTL to 24 hours (optional)
        self.redis_client.expire(cache_key, 86400)
    
    def get_temp_memory(self) -> List[Dict]:
        """Retrieve temporary memory from Redis"""
        if not self.redis_client:
            return []
        
        cache_key = self.get_redis_key("messages")
        messages = self.redis_client.lrange(cache_key, 0, -1)
        
        result = []
        for msg_data in messages:
            msg = json.loads(msg_data)
            msg['created_at'] = datetime.fromisoformat(msg['created_at'])
            result.append(msg)
        
        return result
    
    def get_user_name(self):
        """Get user's name from persona"""
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM user_persona WHERE user_id = %s", (self.user_id,))
        result = cur.fetchone()
        cur.close()
        return result['name'] if result and result['name'] else self.user_id
    
    def get_entry_counts(self):
        """Get total entry counts for current user"""
        cur = self.conn.cursor()
        
        # Knowledge count
        cur.execute("SELECT COUNT(*) as count FROM knowledge_base WHERE user_id = %s", (self.user_id,))
        kb_count = cur.fetchone()['count']
        
        # Persona count
        cur.execute("SELECT COUNT(*) as count FROM user_persona WHERE user_id = %s", (self.user_id,))
        persona_count = cur.fetchone()['count']
        
        # Messages count
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM super_chat_messages scm
            JOIN super_chat sc ON scm.super_chat_id = sc.id
            WHERE sc.user_id = %s
        """, (self.user_id,))
        msg_count = cur.fetchone()['count']
        
        # Episodes count
        cur.execute("SELECT COUNT(*) as count FROM episodes WHERE user_id = %s", (self.user_id,))
        ep_count = cur.fetchone()['count']
        
        cur.close()
        
        return {
            'knowledge': kb_count,
            'persona': persona_count,
            'messages': msg_count,
            'episodes': ep_count,
            'total': kb_count + persona_count + msg_count + ep_count
        }
    
    def generate_embedding(self, text: str, dimensions: int = 1536) -> List[float]:
        """Generate deterministic embedding"""
        import numpy as np
        embedding = []
        for i in range(dimensions):
            seed = text.encode('utf-8') + i.to_bytes(4, 'big')
            hash_val = hashlib.sha256(seed).digest()
            value = int.from_bytes(hash_val[:4], 'big') / (2**32)
            value = (value * 2) - 1
            embedding.append(value)
        
        norm = np.linalg.norm(embedding)
        return [float(v / norm) for v in embedding]
    
    def is_question(self, text: str) -> bool:
        """Detect if input is a question"""
        text_lower = text.lower().strip()
        
        # Question words
        question_words = ['what', 'who', 'where', 'when', 'why', 'how', 'which', 'whose', 
                         'whom', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 
                         'does', 'did', 'will', 'shall']
        
        # Check if starts with question word
        first_word = text_lower.split()[0] if text_lower.split() else ""
        if first_word in question_words:
            return True
        
        # Check if ends with question mark
        if text.strip().endswith('?'):
            return True
        
        return False
    
    # ========================================================================
    # STORAGE WITH LAYER INDICATORS
    # ========================================================================
    
    def classify_and_store(self, text: str) -> Dict[str, Any]:
        """Classify and store with clear layer indication"""
        # Simple classification
        text_lower = text.lower()
        
        # Check if it's persona information
        persona_keywords = ['my name is', 'i am', 'i work as', 'i like', 'my interest', 
                           'i\'m a', 'call me', 'i specialize']
        
        if any(kw in text_lower for kw in persona_keywords):
            return self.store_persona_info(text)
        else:
            return self.store_knowledge(text)
    
    def store_persona_info(self, text: str) -> Dict[str, Any]:
        """Store user persona information in BOTH persona and knowledge layers"""
        cur = self.conn.cursor()
        
        # Extract basic info (simple parsing)
        name = None
        if 'my name is' in text.lower():
            name = text.lower().split('my name is')[1].strip().split()[0].title()
        elif 'i am' in text.lower() and len(text.split()) < 10:
            name = text.lower().split('i am')[1].strip().split()[0].title()
        
        embedding = self.generate_embedding(text)
        
        # 1. Store in user_persona table
        cur.execute("SELECT id FROM user_persona WHERE user_id = %s", (self.user_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE user_persona 
                SET name = COALESCE(%s, name),
                    interests = CASE WHEN interests IS NULL THEN ARRAY[%s] 
                                ELSE array_append(interests, %s) END,
                    raw_content = %s,
                    embedding = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING id
            """, (name, text[:100], text[:100], text, embedding, self.user_id))
        else:
            cur.execute("""
                INSERT INTO user_persona 
                (user_id, name, interests, raw_content, embedding)
                VALUES (%s, %s, ARRAY[%s], %s, %s)
                RETURNING id
            """, (self.user_id, name, text[:100], text, embedding))
        
        persona_id = cur.fetchone()['id']
        
        # 2. ALSO store in knowledge_base for searchability
        cur.execute("""
            INSERT INTO knowledge_base 
            (user_id, content, category, tags, embedding)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            self.user_id,
            f"User Info: {text}",
            "User Persona",
            ["personal_info", "user_data"],
            embedding
        ))
        
        kb_id = cur.fetchone()['id']
        
        # Create semantic memory index for knowledge entry
        cur.execute("""
            INSERT INTO semantic_memory_index (user_id, knowledge_id)
            VALUES (%s, %s)
        """, (self.user_id, kb_id))
        
        self.conn.commit()
        cur.close()
        
        # 3. Store in episodic memory
        self.add_chat_message("user", text)
        
        return {
            "status": "success",
            "storage": [
                {"layer": "SEMANTIC-PERSONA", "table": "user_persona", "id": persona_id},
                {"layer": "SEMANTIC-KNOWLEDGE", "table": "knowledge_base", "id": kb_id},
                {"layer": "EPISODIC", "table": "super_chat_messages", "id": self.current_chat_id}
            ],
            "message": f"✓ Stored in 3 layers:\n    📚 SEMANTIC → user_persona (ID: {persona_id})\n    📚 SEMANTIC → knowledge_base (ID: {kb_id}, Category: User Persona)\n    📅 EPISODIC → super_chat_messages (chat: {self.current_chat_id})"
        }
    
    def store_knowledge(self, content: str) -> Dict[str, Any]:
        """Store knowledge with layer indication"""
        cur = self.conn.cursor()
        
        # Determine category
        if any(kw in content.lower() for kw in ['policy', 'rule', 'procedure', 'hr']):
            category = "HR Policies"
        elif any(kw in content.lower() for kw in ['manage', 'team', 'lead']):
            category = "Management"
        else:
            category = "Knowledge"
        
        embedding = self.generate_embedding(content)
        
        cur.execute("""
            INSERT INTO knowledge_base 
            (user_id, content, category, tags, embedding)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (self.user_id, content, category, [], embedding))
        
        kb_id = cur.fetchone()['id']
        
        # Create index
        cur.execute("""
            INSERT INTO semantic_memory_index (user_id, knowledge_id)
            VALUES (%s, %s)
        """, (self.user_id, kb_id))
        
        self.conn.commit()
        cur.close()
        
        # Also store in episodic
        self.add_chat_message("user", content)
        
        return {
            "status": "success",
            "storage": [
                {"layer": "SEMANTIC", "table": "knowledge_base", "id": kb_id},
                {"layer": "EPISODIC", "table": "super_chat_messages", "id": self.current_chat_id}
            ],
            "message": f"✓ Stored in:\n    📚 SEMANTIC → knowledge_base (ID: {kb_id}, Category: {category})\n    📅 EPISODIC → super_chat_messages (chat: {self.current_chat_id})"
        }
    
    def add_chat_message(self, role: str, content: str):
        """Add message to episodic memory and Redis temporary cache (user messages only)"""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO super_chat_messages 
            (super_chat_id, role, content)
            VALUES (%s, %s, %s)
            RETURNING created_at
        """, (self.current_chat_id, role, content))
        
        created_at = cur.fetchone()['created_at']
        self.conn.commit()
        cur.close()
        
        # Add to Redis temporary memory cache - USER MESSAGES ONLY (context)
        if self.redis_client and role == 'user':
            cache_key = self.get_redis_key("messages")
            msg_data = json.dumps({
                'role': role,
                'content': content,
                'created_at': created_at.isoformat(),
                'source': 'TEMP_MEMORY'
            })
            
            # Add to end of list
            self.redis_client.rpush(cache_key, msg_data)
            
            # Keep only last 15 user messages
            self.redis_client.ltrim(cache_key, -15, -1)
            
            # Refresh TTL
            self.redis_client.expire(cache_key, 86400)
    
    # ========================================================================
    # HYBRID SEARCH WITH SOURCE INDICATORS + REDIS TEMPORARY MEMORY
    # ========================================================================
    
    def hybrid_search(self, query: str, limit: int = 5) -> Dict[str, List]:
        """Hybrid search across all memory layers including Redis temporary memory"""
        cur = self.conn.cursor()
        
        print(f"\n{'='*70}")
        print(f"🔍 HYBRID SEARCH PROCESS - FULL OBSERVABILITY")
        print(f"{'='*70}")
        print(f"Query: '{query}'")
        print(f"User ID: {self.user_id}")
        print(f"Limit per layer: {limit}")
        print(f"{'='*70}\n")
        
        # 1. Search REDIS TEMPORARY MEMORY FIRST (fastest, most recent)
        print("⚡ STEP 1/5: Searching TEMPORARY MEMORY (Redis Cache)...")
        print(f"   ├─ Storage: Redis Unified Cloud")
        print(f"   ├─ Key: temp_memory:{self.user_id}:messages")
        print(f"   └─ Strategy: Keyword matching (case-insensitive)\n")
        
        temp_results = []
        query_lower = query.lower()
        
        if self.redis_client:
            cache_key = self.get_redis_key("messages")
            messages = self.redis_client.lrange(cache_key, 0, -1)
            print(f"   ✓ Retrieved {len(messages)} messages from Redis cache")
            
            temp_messages = self.get_temp_memory()
            for msg in temp_messages:
                if query_lower in msg['content'].lower():
                    temp_results.append({
                        'source_layer': 'TEMP_MEMORY',
                        'table_name': 'redis_cache',
                        'role': msg['role'],
                        'content': msg['content'],
                        'created_at': msg['created_at']
                    })
            print(f"   ✓ Matched {len(temp_results)} results in temp memory\n")
        else:
            print(f"   ⚠️  Redis not available - skipping temp memory\n")
        
        
        # 2. Search Semantic Memory - Knowledge Base (text search)
        print("📚 STEP 2/5: Searching SEMANTIC MEMORY → knowledge_base...")
        print(f"   ├─ Table: knowledge_base")
        print(f"   ├─ Strategy: ILIKE text search on content")
        print(f"   ├─ Filter: user_id = {self.user_id}")
        print(f"   └─ Query Pattern: %{query}%\n")
        cur.execute("""
            SELECT 
                'SEMANTIC-KNOWLEDGE' as source_layer,
                'knowledge_base' as table_name,
                id,
                content,
                category,
                created_at
            FROM knowledge_base
            WHERE user_id = %s 
              AND content ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (self.user_id, f'%{query}%', limit))
        
        semantic_knowledge = cur.fetchall()
        print(f"   ✓ Found {len(semantic_knowledge)} results in knowledge_base\n")
        
        # 3. Search Semantic Memory - User Persona (text search)
        print("📚 STEP 3/5: Searching SEMANTIC MEMORY → user_persona...")
        print(f"   ├─ Table: user_persona")
        print(f"   ├─ Strategy: Fetch all persona data for user")
        print(f"   ├─ Filter: user_id = {self.user_id}")
        print(f"   └─ Fields: name, interests, expertise_areas\n")
        cur.execute("""
            SELECT 
                'SEMANTIC-PERSONA' as source_layer,
                'user_persona' as table_name,
                id,
                name,
                interests,
                expertise_areas
            FROM user_persona
            WHERE user_id = %s
        """, (self.user_id,))
        
        semantic_persona = cur.fetchall()
        print(f"   ✓ Found {len(semantic_persona)} persona record(s)\n")
        
        # 4. Search Episodic Memory - Recent Messages (text search)
        print("📅 STEP 4/5: Searching EPISODIC MEMORY → super_chat_messages...")
        print(f"   ├─ Table: super_chat_messages (JOIN super_chat)")
        print(f"   ├─ Strategy: ILIKE text search on content")
        print(f"   ├─ Filter: user_id = {self.user_id}")
        print(f"   ├─ Query Pattern: %{query}%")
        print(f"   └─ Order: created_at DESC\n")
        cur.execute("""
            SELECT 
                'EPISODIC-MESSAGES' as source_layer,
                'super_chat_messages' as table_name,
                scm.id,
                scm.role,
                scm.content,
                scm.created_at
            FROM super_chat_messages scm
            JOIN super_chat sc ON scm.super_chat_id = sc.id
            WHERE sc.user_id = %s
              AND scm.content ILIKE %s
            ORDER BY scm.created_at DESC
            LIMIT %s
        """, (self.user_id, f'%{query}%', limit))
        
        episodic_messages = cur.fetchall()
        print(f"   ✓ Found {len(episodic_messages)} message(s) in episodic memory\n")
        
        # 5. Search Episodic Memory - Episodes (text search in messages JSON)
        print("📅 STEP 5/5: Searching EPISODIC MEMORY → episodes...")
        print(f"   ├─ Table: episodes")
        print(f"   ├─ Strategy: ILIKE text search on messages JSON")
        print(f"   ├─ Filter: user_id = {self.user_id}")
        print(f"   ├─ Query Pattern: %{query}% (in messages::text)")
        print(f"   └─ Order: created_at DESC\n")
        cur.execute("""
            SELECT 
                'EPISODIC-EPISODES' as source_layer,
                'episodes' as table_name,
                id,
                messages,
                message_count,
                source_type,
                created_at
            FROM episodes
            WHERE user_id = %s
              AND messages::text ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (self.user_id, f'%{query}%', limit))
        
        episodic_episodes = cur.fetchall()
        print(f"   ✓ Found {len(episodic_episodes)} episode(s)\n")
        
        cur.close()
        
        total_results = len(temp_results) + len(semantic_knowledge) + len(semantic_persona) + len(episodic_messages) + len(episodic_episodes)
        print(f"{'='*70}")
        print(f"✅ SEARCH COMPLETE: {total_results} total results across all layers")
        print(f"   ├─ Temp Memory: {len(temp_results)}")
        print(f"   ├─ Semantic Knowledge: {len(semantic_knowledge)}")
        print(f"   ├─ Semantic Persona: {len(semantic_persona)}")
        print(f"   ├─ Episodic Messages: {len(episodic_messages)}")
        print(f"   └─ Episodic Episodes: {len(episodic_episodes)}")
        print(f"{'='*70}\n")
        
        return {
            "temp_memory": temp_results,  # Most recent, fastest access
            "semantic_knowledge": [dict(r) for r in semantic_knowledge],
            "semantic_persona": [dict(r) for r in semantic_persona],
            "episodic_messages": [dict(r) for r in episodic_messages],
            "episodic_episodes": [dict(r) for r in episodic_episodes]
        }
    
    def display_search_results(self, results: Dict[str, List]):
        """Display search results with FULL FIELD VISIBILITY for observability"""
        total = sum(len(v) for v in results.values())
        
        print(f"\n{'='*70}")
        print(f"  RETRIEVAL RESULTS: {total} items found | USER: {self.user_id}")
        print(f"{'='*70}\n")
        
        # Temporary Memory (PRIORITY - Most Recent)
        if results.get('temp_memory'):
            print(f"⚡ TEMPORARY MEMORY (Redis Cache - Last 15 chats)")
            print(f"   ├─ Source: Redis (Unified Cloud)")
            print(f"   ├─ Count: {len(results['temp_memory'])}")
            print(f"   └─ Layer: TEMPORARY/SHORT-TERM\n")
            for i, item in enumerate(results['temp_memory'], 1):
                print(f"   [{i}] 🔹 Role: {item.get('role', 'N/A')}")
                print(f"       ├─ Content: {item.get('content', 'N/A')[:200]}")
                print(f"       ├─ Created: {item.get('created_at', 'N/A')}")
                print(f"       ├─ Source Layer: {item.get('source_layer', 'TEMP_MEMORY')}")
                print(f"       ├─ Table: {item.get('table_name', 'redis_cache')}")
                print(f"       └─ Storage: Redis temp cache (TTL: 24h)")
                print()
        
        # Semantic Knowledge
        if results['semantic_knowledge']:
            print(f"📚 SEMANTIC MEMORY → knowledge_base")
            print(f"   ├─ Table: knowledge_base")
            print(f"   ├─ Count: {len(results['semantic_knowledge'])}")
            print(f"   └─ Layer: SEMANTIC (Long-term facts)\n")
            for i, item in enumerate(results['semantic_knowledge'], 1):
                print(f"   [{i}] 📘 ID: {item['id']}")
                print(f"       ├─ Content: {item['content'][:200]}")
                print(f"       ├─ Category: {item['category']}")
                print(f"       ├─ User ID: {self.user_id}")
                print(f"       ├─ Created: {item['created_at']}")
                print(f"       ├─ Source Layer: {item['source_layer']}")
                print(f"       └─ Table: {item['table_name']}")
                print()
        
        # Semantic Persona
        if results['semantic_persona']:
            print(f"📚 SEMANTIC MEMORY → user_persona")
            print(f"   ├─ Table: user_persona")
            print(f"   ├─ Count: {len(results['semantic_persona'])}")
            print(f"   └─ Layer: SEMANTIC (User identity)\n")
            for i, item in enumerate(results['semantic_persona'], 1):
                print(f"   [{i}] 👤 ID: {item['id']}")
                print(f"       ├─ Name: {item.get('name', 'N/A')}")
                print(f"       ├─ Interests: {item.get('interests', 'N/A')}")
                print(f"       ├─ Expertise: {item.get('expertise_areas', 'N/A')}")
                print(f"       ├─ User ID: {self.user_id}")
                print(f"       ├─ Source Layer: {item['source_layer']}")
                print(f"       └─ Table: {item['table_name']}")
                print()
        
        # Episodic Messages
        if results['episodic_messages']:
            print(f"📅 EPISODIC MEMORY → super_chat_messages")
            print(f"   ├─ Table: super_chat_messages")
            print(f"   ├─ Count: {len(results['episodic_messages'])}")
            print(f"   └─ Layer: EPISODIC (Temporal conversations)\n")
            for i, item in enumerate(results['episodic_messages'], 1):
                print(f"   [{i}] 💬 Message ID: {item['id']}")
                print(f"       ├─ Role: {item['role']}")
                print(f"       ├─ Content: {item['content'][:200]}")
                print(f"       ├─ Chat ID: {self.current_chat_id}")
                print(f"       ├─ User ID: {self.user_id}")
                print(f"       ├─ Created: {item['created_at']}")
                print(f"       ├─ Source Layer: {item['source_layer']}")
                print(f"       └─ Table: {item['table_name']}")
                print()
        
        # Episodic Episodes
        if results['episodic_episodes']:
            print(f"📅 EPISODIC MEMORY → episodes")
            print(f"   ├─ Table: episodes")
            print(f"   ├─ Count: {len(results['episodic_episodes'])}")
            print(f"   └─ Layer: EPISODIC (Summarized sessions)\n")
            for i, item in enumerate(results['episodic_episodes'], 1):
                print(f"   [{i}] 📖 Episode ID: {item['id']}")
                print(f"       ├─ Message Count: {item['message_count']}")
                print(f"       ├─ Source Type: {item['source_type']}")
                messages = json.loads(item['messages']) if isinstance(item['messages'], str) else item['messages']
                first_msg = messages[0]['content'][:100] if messages else 'No messages'
                print(f"       ├─ Messages Preview: {first_msg}...")
                print(f"       ├─ User ID: {self.user_id}")
                print(f"       ├─ Created: {item['created_at']}")
                print(f"       ├─ Source Layer: {item['source_layer']}")
                print(f"       └─ Table: {item['table_name']}")
                print()
        
        if total == 0:
            print("❌ No results found in any memory layer\n")
    
    # ========================================================================
    # CLI Interface
    # ========================================================================
    
    def run(self):
        """Enhanced interactive CLI with Redis temporary memory cache"""
        print("\n" + "="*70)
        print("🧠 INTERACTIVE MEMORY SYSTEM - Layer-Aware Storage & Retrieval")
        print("="*70)
        print("\n📊 Memory Architecture:")
        redis_status = "Redis connected ✓" if self.redis_client else "Redis unavailable ⚠️"
        print(f"  ⚡ TEMPORARY CACHE: Last 15 chats ({redis_status})")
        print("  📚 SEMANTIC LAYER:  user_persona, knowledge_base (long-term facts)")
        print("  📅 EPISODIC LAYER:  super_chat_messages, episodes (temporal events)")
        print("\n💡 Commands:")
        print("  <text>              → Auto-store in appropriate layer(s)")
        print("  search <query>      → Hybrid search across ALL layers + temp cache")
        print("  chat <message>      → Chat with AI (prioritizes temp cache)")
        print("  history             → View conversation history with timestamps")
        print("  status              → Show memory statistics")
        print("  user <id>           → Switch user (reloads temp cache)")
        print("  quit                → Exit")
        print("="*70 + "\n")
        
        # Show all available users with counts
        self.show_all_users()
        
        # Show current user status
        self.show_compact_status()
        
        while True:
            try:
                # Get current user name for prompt
                cur = self.conn.cursor()
                cur.execute("SELECT name FROM user_persona WHERE user_id = %s", (self.user_id,))
                result = cur.fetchone()
                cur.close()
                user_name = result['name'] if result and result['name'] else self.user_id
                
                user_input = input(f"[{user_name}] → ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "quit":
                    print("\n👋 Goodbye!\n")
                    break
                
                elif user_input.startswith("search "):
                    query = user_input[7:].strip()
                    results = self.hybrid_search(query)
                    self.display_search_results(results)
                
                elif user_input == "status":
                    self.show_status()
                
                elif user_input == "history":
                    self.show_conversation_history()
                
                elif user_input.startswith("user "):
                    self.user_id = user_input[5:].strip()
                    self.ensure_super_chat()
                    # Reload Redis temporary memory for new user
                    self.load_recent_to_temp_memory()
                    
                    cache_size = len(self.get_temp_memory()) if self.redis_client else 0
                    print(f"\n✓ Switched to user: {self.user_id}")
                    if self.redis_client:
                        print(f"⚡ Loaded {cache_size} messages into Redis cache\n")
                    self.show_compact_status()
                
                elif user_input.startswith("chat "):
                    message = user_input[5:].strip()
                    self.chat_with_context(message)
                
                else:
                    # Check if input is a question or statement
                    if self.is_question(user_input):
                        # Auto-route questions to chat
                        self.chat_with_context(user_input)
                    else:
                        # Store statements with layer indication
                        result = self.classify_and_store(user_input)
                        print(f"\n{result['message']}")
                        
                        # Now RETRIEVE and provide contextual response
                        self.retrieve_and_respond(user_input)
                        print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                # Rollback any failed transaction
                try:
                    self.conn.rollback()
                except:
                    pass
                print(f"\n❌ Error: {e}\n")
                import traceback
                traceback.print_exc()
    
    def show_compact_status(self):
        """Show compact user status with name"""
        cur = self.conn.cursor()
        
        # Get user name
        cur.execute("SELECT name FROM user_persona WHERE user_id = %s", (self.user_id,))
        result = cur.fetchone()
        user_name = result['name'] if result and result['name'] else self.user_id
        
        # Get all counts
        cur.execute("SELECT COUNT(*) as count FROM knowledge_base WHERE user_id = %s", (self.user_id,))
        kb_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM user_persona WHERE user_id = %s", (self.user_id,))
        persona_count = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM super_chat_messages scm
            JOIN super_chat sc ON scm.super_chat_id = sc.id
            WHERE sc.user_id = %s
        """, (self.user_id,))
        msg_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM episodes WHERE user_id = %s", (self.user_id,))
        ep_count = cur.fetchone()['count']
        
        cur.close()
        
        total_entries = kb_count + persona_count + msg_count + ep_count
        
        print(f"👤 CURRENT USER: {user_name} ({self.user_id}) | 💬 Chat: {self.current_chat_id}")
        print(f"📊 Entries: {total_entries} total (Knowledge: {kb_count} | Persona: {persona_count} | Messages: {msg_count} | Episodes: {ep_count})\n")
    
    def show_all_users(self):
        """Show all available users with their entry counts"""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                up.user_id,
                up.name,
                COALESCE(kb.count, 0) as kb_count,
                COALESCE(msg.count, 0) as msg_count,
                COALESCE(ep.count, 0) as ep_count,
                COALESCE(kb.count, 0) + 1 + COALESCE(msg.count, 0) + COALESCE(ep.count, 0) as total
            FROM user_persona up
            LEFT JOIN (SELECT user_id, COUNT(*) as count FROM knowledge_base GROUP BY user_id) kb 
                ON up.user_id = kb.user_id
            LEFT JOIN (SELECT sc.user_id, COUNT(*) as count FROM super_chat_messages scm 
                       JOIN super_chat sc ON scm.super_chat_id = sc.id GROUP BY sc.user_id) msg 
                ON up.user_id = msg.user_id
            LEFT JOIN (SELECT user_id, COUNT(*) as count FROM episodes GROUP BY user_id) ep 
                ON up.user_id = ep.user_id
            ORDER BY up.name
        """)
        
        users = cur.fetchall()
        cur.close()
        
        if users:
            print("📋 AVAILABLE USERS:")
            for user in users:
                print(f"   • {user['name']:20} ({user['user_id']:25}) → {user['total']} entries")
            print()
    
    def show_status(self):
        """Show detailed memory statistics"""
        cur = self.conn.cursor()
        
        # Semantic layer
        cur.execute("SELECT COUNT(*) as count FROM knowledge_base WHERE user_id = %s", (self.user_id,))
        kb_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM user_persona WHERE user_id = %s", (self.user_id,))
        persona_count = cur.fetchone()['count']
        
        # Episodic layer
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM super_chat_messages scm
            JOIN super_chat sc ON scm.super_chat_id = sc.id
            WHERE sc.user_id = %s
        """, (self.user_id,))
        msg_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM episodes WHERE user_id = %s", (self.user_id,))
        ep_count = cur.fetchone()['count']
        
        # Instances
        cur.execute("SELECT COUNT(*) as count FROM instances WHERE user_id = %s", (self.user_id,))
        inst_count = cur.fetchone()['count']
        
        cur.close()
        
        total_entries = kb_count + persona_count + msg_count + ep_count + inst_count
        
        print(f"\n{'='*70}")
        print(f"  MEMORY STATUS")
        print(f"{'='*70}")
        print(f"\n👤 USER ID: {self.user_id}")
        print(f"💬 Chat Session: {self.current_chat_id}")
        print(f"📊 TOTAL ENTRIES: {total_entries}")
        print(f"\n📚 SEMANTIC LAYER:")
        print(f"   knowledge_base:  {kb_count} entries")
        print(f"   user_persona:    {persona_count} records")
        print(f"\n📅 EPISODIC LAYER:")
        print(f"   chat_messages:   {msg_count} messages")
        print(f"   episodes:        {ep_count} episodes")
        print(f"   instances:       {inst_count} instances")
        print(f"\n{'='*70}\n")
    
    def show_conversation_history(self, limit: int = 50):
        """Show recent conversation history with timestamps"""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT scm.role, scm.content, scm.created_at
            FROM super_chat_messages scm
            JOIN super_chat sc ON scm.super_chat_id = sc.id
            WHERE sc.user_id = %s
            ORDER BY scm.created_at DESC
            LIMIT %s
        """, (self.user_id, limit))
        
        messages = cur.fetchall()
        cur.close()
        
        if not messages:
            print("\n📭 No conversation history found.\n")
            return
        
        print(f"\n{'='*70}")
        print(f"  CONVERSATION HISTORY - Last {len(messages)} messages")
        print(f"{'='*70}\n")
        
        # Reverse to show oldest first
        for msg in reversed(messages):
            timestamp = msg['created_at'].strftime('%b %d, %Y %I:%M:%S %p')
            role_icon = "👤" if msg['role'] == "user" else "🤖"
            print(f"{role_icon} [{timestamp}] {msg['role'].upper()}:")
            print(f"   {msg['content']}")
            print()
        
        print(f"{'='*70}\n")
    
    def chat_with_context(self, message: str):
        """Chat with full context retrieval and intelligent response"""
        print(f"\n💭 Processing your question...")
        
        # Store user message in episodic
        self.add_chat_message("user", message)
        print(f"   ✓ Question stored in EPISODIC → super_chat_messages")
        
        # Check if asking about specific time/conversation
        import re
        from datetime import datetime, timedelta
        
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:am|pm))',  # 7:40pm, 7:40 pm
            r'at\s+(\d{1,2}:\d{2})',  # at 19:40
            r'conversation.*?(\d{1,2}:\d{2})',  # conversation at 7:40
        ]
        
        # Check for date patterns
        date_patterns = [
            (r'(?:Jan|January)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})', 'jan_year'),  # Jan 7th 2026, January 7, 2026
            (r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:Jan|January)\s+(\d{4})', 'day_jan_year'),  # 7th Jan 2026
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'numeric'),  # 01/07/2026, 1-7-2026
            (r'(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:Jan|January)', 'day_jan'),  # 7th Jan (no year)
        ]
        
        time_match = None
        for pattern in time_patterns:
            match = re.search(pattern, message.lower())
            if match:
                time_match = match.group(1)
                break
        
        # Parse date from query
        target_date = None
        if 'yesterday' in message.lower():
            target_date = (datetime.now() - timedelta(days=1)).date()
            print(f"   📅 Detected: yesterday → {target_date}")
        else:
            for pattern, pattern_type in date_patterns:
                match = re.search(pattern, message.lower(), re.IGNORECASE)
                if match:
                    try:
                        if pattern_type == 'jan_year':
                            day = int(match.group(1))
                            year = int(match.group(2))
                            target_date = datetime(year, 1, day).date()
                            print(f"   📅 Detected date: {target_date.strftime('%B %d, %Y')} (pattern: jan_year)")
                        elif pattern_type == 'day_jan_year':
                            day = int(match.group(1))
                            year = int(match.group(2))
                            target_date = datetime(year, 1, day).date()
                            print(f"   📅 Detected date: {target_date.strftime('%B %d, %Y')} (pattern: day_jan_year)")
                        elif pattern_type == 'day_jan':
                            day = int(match.group(1))
                            year = datetime.now().year
                            target_date = datetime(year, 1, day).date()
                            print(f"   📅 Detected date: {target_date.strftime('%B %d, %Y')} (pattern: day_jan)")
                        elif pattern_type == 'numeric':
                            day = int(match.group(2))
                            month = int(match.group(1))
                            year = int(match.group(3))
                            target_date = datetime(year, month, day).date()
                            print(f"   📅 Detected date: {target_date.strftime('%B %d, %Y')} (pattern: numeric)")
                        break
                    except Exception as e:
                        print(f"   ⚠️  Date parsing error for pattern {pattern_type}: {e}")
                        continue
        
        # Get context via hybrid search
        print(f"   🔍 Searching across all memory layers...")
        results = self.hybrid_search(message, limit=10)
        
        # Build comprehensive context
        context_parts = []
        
        # PRIORITY: Add Redis temporary memory first (last 15 chats - most recent context)
        if self.redis_client:
            temp_messages = self.get_temp_memory()
            if temp_messages:
                context_parts.append("\n⚡ RECENT REDIS CACHE (Last 15 chats):")
                for msg in temp_messages:
                    timestamp = msg['created_at'].strftime('%b %d, %Y %I:%M %p') if msg.get('created_at') else 'Unknown time'
                    context_parts.append(f"- [{timestamp}] {msg['role']}: {msg['content']}")
        
        # Get user persona
        cur = self.conn.cursor()
        cur.execute("""
            SELECT name, raw_content, interests, expertise_areas 
            FROM user_persona 
            WHERE user_id = %s
        """, (self.user_id,))
        persona = cur.fetchone()
        
        if persona:
            context_parts.append(f"\nUSER INFO: {persona['name']} - {persona['raw_content']}")
            if persona['interests']:
                context_parts.append(f"Interests: {', '.join(persona['interests'])}")
            if persona['expertise_areas']:
                context_parts.append(f"Expertise: {', '.join(persona['expertise_areas'])}")
        
        # Add relevant knowledge
        if results['semantic_knowledge']:
            context_parts.append("\nRELEVANT KNOWLEDGE:")
            for item in results['semantic_knowledge'][:3]:
                context_parts.append(f"- {item['content']}")
        
        # Add relevant messages WITH TIMESTAMPS (only if not already in temp_memory)
        if results['episodic_messages']:
            context_parts.append("\nRECENT CONVERSATIONS (from history):")
            for item in results['episodic_messages'][:10]:
                timestamp = item['created_at'].strftime('%b %d, %Y %I:%M %p') if item['created_at'] else 'Unknown time'
                context_parts.append(f"- [{timestamp}] {item['role']}: {item['content'][:100]}")
        
        # If asking about specific time, get messages from that time
        if time_match or target_date:
            query_date = target_date if target_date else datetime.now().date()
            
            print(f"   🔍 Querying messages for date: {query_date}")
            
            cur.execute("""
                SELECT scm.role, scm.content, scm.created_at
                FROM super_chat_messages scm
                JOIN super_chat sc ON scm.super_chat_id = sc.id
                WHERE sc.user_id = %s
                  AND scm.created_at::date = %s
                ORDER BY scm.created_at DESC
                LIMIT 100
            """, (self.user_id, query_date))
            recent_messages = cur.fetchall()
            
            print(f"   ✅ Found {len(recent_messages)} messages for {query_date.strftime('%B %d, %Y')}")
            
            if recent_messages:
                date_str = query_date.strftime('%B %d, %Y')
                context_parts.append(f"\nFULL CONVERSATION HISTORY FOR {date_str}:")
                for msg in recent_messages:
                    timestamp = msg['created_at'].strftime('%I:%M %p') if msg['created_at'] else 'Unknown'
                    context_parts.append(f"- [{timestamp}] {msg['role']}: {msg['content']}")
            else:
                context_parts.append(f"\nNo conversations found for {query_date.strftime('%B %d, %Y')}")
        
        # Add episodes
        if results['episodic_episodes']:
            context_parts.append("\nRELATED EPISODES:")
            for item in results['episodic_episodes'][:2]:
                messages = json.loads(item['messages']) if isinstance(item['messages'], str) else item['messages']
                context_parts.append(f"- {len(messages)} messages about work topics")
        
        cur.close()
        
        print(f"   ✓ Retrieved context from {len(results['semantic_knowledge']) + len(results['episodic_messages']) + len(results['episodic_episodes'])} sources")
        
        # Generate response
        full_context = "\n".join(context_parts)
        
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"""You are a helpful assistant with access to the user's memory.
                        
CONTEXT:
{full_context}

Answer the user's question based on this context. If the information is not available in the context, say so clearly."""},
                        {"role": "user", "content": message}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                reply = response.choices[0].message.content
            except Exception as e:
                reply = f"Based on your stored data:\n{full_context[:500]}...\n\nNote: Unable to generate AI response. Error: {str(e)}"
        else:
            # Fallback response without Groq
            reply = f"Based on your stored information:\n\n{full_context}\n\nTo get AI-powered responses, configure GROQ_API_KEY in your .env file."
        
        # Store AI response in episodic
        self.add_chat_message("assistant", reply)
        
        print(f"\n🤖 {reply}")
        print(f"\n   ✓ Response stored in EPISODIC → super_chat_messages\n")
    
    def retrieve_and_respond(self, stored_text: str):
        """Retrieve relevant context from storage layers and provide intelligent response"""
        print(f"\n   🔍 Retrieving from storage layers...")
        
        try:
            # Perform hybrid search on what was just stored (suppress hybrid_search print)
            cur = self.conn.cursor()
            
            # Quick search in knowledge_base
            cur.execute("""
                SELECT id, content, category
                FROM knowledge_base
                WHERE user_id = %s 
                  AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT 3
            """, (self.user_id, f'%{stored_text[:50]}%'))
            
            knowledge_results = cur.fetchall()
            
            # Get user persona
            cur.execute("""
                SELECT name, raw_content, interests, expertise_areas 
                FROM user_persona 
                WHERE user_id = %s
            """, (self.user_id,))
            persona = cur.fetchone()
            
            cur.close()
            
            total_retrieved = len(knowledge_results)
            
            if total_retrieved > 0 or persona:
                print(f"   ✓ Retrieved {total_retrieved} related items from storage")
                
                # Build contextual response
                context_parts = []
                
                if persona and persona['name']:
                    context_parts.append(f"User: {persona['name']}")
                    if persona['interests']:
                        context_parts.append(f"Interests: {', '.join(persona['interests'][:3])}")
                
                # Add knowledge context
                if knowledge_results:
                    context_parts.append(f"\nRelated knowledge:")
                    for item in knowledge_results[:2]:
                        context_parts.append(f"  • [{item['category']}] {item['content'][:60]}...")
                
                # Generate AI response if available
                if self.groq_client and context_parts:
                    try:
                        full_context = "\n".join(context_parts)
                        response = self.groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"""You are a helpful memory assistant. The user just stored: "{stored_text}"

Based on their memory context, provide a brief, relevant acknowledgment or insight (1-2 sentences).

MEMORY CONTEXT:
{full_context}"""},
                                {"role": "user", "content": f"I just stored: {stored_text}"}
                            ],
                            temperature=0.7,
                            max_tokens=150
                        )
                        reply = response.choices[0].message.content
                        print(f"\n   💡 {reply}")
                    except Exception as e:
                        # Silently fail - already showed storage confirmation
                        pass
            else:
                print(f"   ℹ️  This is your first entry")
        except Exception as e:
            # Don't break the flow if retrieval fails
            print(f"   ℹ️  Storage confirmed")


if __name__ == "__main__":
    app = InteractiveMemorySystem()
    app.run()
