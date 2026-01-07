# Unified Memory System: Semantic + Episodic

AI-powered memory system combining **semantic memory** (long-term facts) and **episodic memory** (time-based conversations) using PostgreSQL 17, pgvector, and Groq LLM.

## 🧠 Memory Architecture

### Semantic Memory (What You Know)
Long-term factual knowledge automatically classified into layers:

1. **User Persona** - Personal information, preferences, traits
   - *Example: "I'm a software engineer who loves Python"*
   - *Stored in: `user_persona` table*

2. **Knowledge** - Facts, concepts, general information
   - *Example: "Python is great for AI development"*
   - *Stored in: `knowledge_base` table with category='knowledge'*

3. **Skills** - Abilities, competencies, expertise
   - *Example: "I can build REST APIs with FastAPI"*
   - *Stored in: `knowledge_base` table with category='skill'*

4. **Process** - Procedures, workflows, how-to knowledge
   - *Example: "To deploy, run docker build then docker push"*
   - *Stored in: `knowledge_base` table with category='process'*

### Episodic Memory (What Happened)
Time-based conversation episodes:

1. **Super Chat** - Ongoing conversations with episodization
   - Messages stored in real-time
   - Auto-converts to episodes after 2 minutes of inactivity
   
2. **Episodes** - Consolidated conversation chunks
   - Vector embeddings for semantic episode search
   - Enables "Remember when we talked about...?" queries
   
3. **Deep Dive** - Focused discussion threads
   - Separate conversation contexts
   - Useful for project-specific discussions

## Search Algorithms

### Semantic Search (Hybrid)
Searches long-term knowledge using combined approaches:

```
Query: "What programming languages do I know?"
    ↓
1. Generate Query Embedding (1536-dim vector via Groq)
    ↓
2. Parallel Search:
   ├─ Vector Search: Cosine similarity with stored embeddings
   └─ Text Search: PostgreSQL full-text search (ts_vector)
    ↓
3. Score Fusion:
   - Vector similarity score (0-1)
   - Text relevance score (0-1)
   - Weighted combination: 0.6*vector + 0.4*text
    ↓
4. Filter & Rank:
   - Apply minimum similarity threshold (default: 0.6)
   - Sort by combined score
   - Return top results with context
```

### Episodic Search
Searches past conversations using:

- **Vector similarity** on episode embeddings (384-dim via sentence-transformers)
- **BM25 keyword matching** for precise term retrieval
- **Temporal context** (when did it happen)

**Key Features:**
- ✅ Automatic semantic classification
- ✅ Time-based episodic memory
- ✅ Hybrid search (vector + keyword + text)
- ✅ Conversation episodization
- ✅ Full context retrieval (persona + knowledge + episodes)
- ✅ Groq LLM for intelligent chat responses

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Create database
psql -U postgres -c "CREATE DATABASE semantic_memory TEMPLATE template0;"

# Run unified schema (semantic + episodic)
psql -U postgres -d semantic_memory -f database/unified_schema.sql
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials:
# DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, GROQ_API_KEY
```

### 4. Run Unified Application
```bash
python3 unified_memory_app.py
```

**Available Commands:**
- `<text>` - Auto-classify and store in semantic memory
- `chat <message>` - Chat with AI (uses full context)
- `search <query>` - Search semantic knowledge
- `episodes` - View conversation episodes
- `persona` - View user profile
- `context [query]` - View complete memory context
- `user <id>` - Switch user

## Database Schema

### Semantic Memory Tables

**`user_persona`** - Personal information layer
- Stores: name, bio, interests, expertise, preferences
- Vector embedding (1536-dim) for profile matching

**`knowledge_base`** - Multi-purpose knowledge storage
- Stores: content, category (knowledge/skill/process), tags
- Vector embedding (1536-dim) + full-text search
- Importance scoring

**`semantic_memory_index`** - User-knowledge relationships
- Links users to knowledge items
- Tracks access patterns

### Episodic Memory Tables

**`super_chat`** & **`super_chat_messages`** - Active conversations
- Real-time message storage
- Auto-episodization triggers

**`episodes`** - Consolidated conversation chunks
- JSONB message storage
- Vector embedding (384-dim) for episode search
- Temporal metadata (date_from, date_to)

**`deepdive_conversations`** & **`deepdive_messages`** - Focused threads
- Separate discussion contexts
- Full message history

**`instances`** - Archived episodes
- Long-term episode storage
- Historical reference

## Usage Example

```python
from unified_memory_app import UnifiedMemorySystem

app = UnifiedMemorySystem()

# 1. SEMANTIC MEMORY - Store different types of information
# Auto-classified into appropriate layers

app.classify_and_store("I'm Alice, a Python developer who loves AI")
# → Classified as: user_persona

app.classify_and_store("Python uses dynamic typing")
# → Classified as: knowledge

app.classify_and_store("I can build REST APIs with FastAPI")
# → Classified as: skill

app.classify_and_store("To deploy: git push, then run docker build")
# → Classified as: process


# 2. EPISODIC MEMORY - Chat conversations (auto-stored)

response = app.chat("What programming languages do I know?")
# → AI uses full context (persona + knowledge + past conversations)
print(response)


# 3. UNIFIED SEARCH

# Search semantic memory
results = app.search_semantic("Python", limit=5)
for r in results:
    print(f"[{r['category']}] {r['content']} (score: {r['similarity']:.2%})")

# Search episodic memory (past conversations)
episodes = app.search_episodes("deployment", limit=3)
for ep in episodes:
    print(f"Episode: {ep['message_count']} messages from {ep['date_from']}")


# 4. FULL CONTEXT RETRIEVAL

context = app.get_full_context("What can I do?")
# Returns:
# {
#   "persona": {...},
#   "recent_chat": [...],
#   "semantic_memory": [...],
#   "episodic_memory": [...]
# }
```

## API Reference

### Semantic Memory
- `classify_and_store(text)` - Auto-classify and store
- `store_persona(data)` - Manual persona update
- `store_knowledge(content, category, tags)` - Manual storage
- `search_semantic(query, limit)` - Search knowledge base
- `get_user_persona()` - Get user profile

### Episodic Memory
- `chat(message)` - Chat with AI (auto-stores in episodic)
- `add_chat_message(role, content)` - Manual message storage
- `get_recent_chat_history(limit)` - Get recent messages
- `search_episodes(query, limit)` - Search past conversations

### Unified Context
- `get_full_context(query)` - Get complete memory snapshot
## Tech Stack

- **Database**: PostgreSQL 17 with pgvector extension
- **LLM**: Groq API (Llama 3.3 70B) for classification & chat
- **Embeddings**: 
  - Semantic: Deterministic hash-based (1536-dim)
  - Episodic: sentence-transformers (384-dim)
- **Vector Search**: IVFFlat indexes for similarity search
- **Text Search**: PostgreSQL full-text search (ts_vector) + BM25
- **Backend**: Python with psycopg2
- **Optional API**: Flask for REST endpoints

## Project Structure

```
├── unified_memory_app.py          # Main unified application
├── enhanced_memory_app.py         # Semantic-only version
├── database/
│   ├── unified_schema.sql         # Complete schema (semantic + episodic)
│   ├── schema.sql                 # Original semantic schema
│   └── enhanced_schema.sql        # Enhanced semantic schema
├── src/
│   ├── episodic/                  # Episodic memory modules
│   │   ├── episodization.py       # Episode creation logic
│   │   ├── hybrid_retriever.py    # Episode search
│   │   ├── chat_service.py        # Chat management
│   │   └── context_builder.py     # Context assembly
│   ├── models/                    # Data models
│   ├── services/                  # Business logic
│   └── repositories/              # Data access layer
└── requirements.txt
```

## License

MIT
