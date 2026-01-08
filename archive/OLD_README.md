# 🧠 Unified Memory System: Semantic + Episodic

Complete AI memory system with **unified input/output** combining:
- **Semantic Memory** (long-term facts, knowledge, skills, persona)
- **Episodic Memory** (time-based events, conversations, experiences)

Built with PostgreSQL 17, pgvector, and Groq LLM.

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

### 4. Run Unified System
```bash
# New unified interface (recommended)
python3 unified_memory_system.py

# Individual components
python3 enhanced_memory_app.py    # Semantic only
python3 unified_memory_app.py     # Full system with chat
```

**Commands (unified_memory_system.py):**
- `<text>` - Store memory (auto-routed to semantic/episodic)
- `search <query>` - Search both memory types
- `context [query]` - Get complete user context
- `user <id>` - Switch user
- `quit` - Exit

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

## Usage Examples

### Unified Interface (Recommended)

```python
from unified_memory_system import UnifiedMemorySystem

# Initialize system
memory = UnifiedMemorySystem(user_id="alice")

# AUTOMATIC MEMORY ROUTING
# Input is automatically classified and stored in semantic/episodic

# Example 1: Semantic + Episodic
result = memory.store_memory("Today I learned Python decorators at the workshop")
# → Stored in:
#    - Episodic: event (time-bound experience)
#    - Semantic: knowledge (general fact about decorators)

# Example 2: Pure Semantic
result = memory.store_memory("I'm a software engineer who loves Python")
# → Stored in: Semantic - user_persona

# Example 3: Pure Episodic
result = memory.store_memory("Had coffee with Sarah at 3pm, discussed the new API")
# → Stored in: Episodic - interaction

# UNIFIED SEARCH
# Searches both semantic and episodic memories
results = memory.search_memory("What did I learn about Python?")
for result in results:
    print(f"[{result['memory_type']}] {result['content']}")
    print(f"Relevance: {result['score']:.2%}")
    print(f"Time: {result['timestamp']}\n")

# GET COMPLETE CONTEXT
# Retrieves semantic facts + episodic experiences
context = memory.get_context("Tell me about my Python knowledge")
print(f"Semantic memories: {len(context['semantic_memories'])}")
print(f"Episodic memories: {len(context['episodic_memories'])}")
```

### Separate Components

```python
# SEMANTIC ONLY
from enhanced_memory_app import EnhancedMemoryApp

app = EnhancedMemoryApp()
app.classify_and_store("Python uses dynamic typing")
results = app.search_all("What can I do with Python?")

# EPISODIC ONLY (with chat)
from unified_memory_app import UnifiedMemorySystem

app = UnifiedMemorySystem()
app.add_message("Had a great meeting today about the AI project")
episodes = app.get_recent_episodes(limit=5)
```

## Key Features

### 🎯 Unified Input/Output
- **Single interface** for all memory operations
- **Automatic classification** - input routed to semantic/episodic/both
- **Combined search** - results from all memory types ranked by relevance

### 🧠 Memory Types

| Type | Storage | Use Case | Example |
|------|---------|----------|---------|
| **Semantic** | Timeless facts | "Python is object-oriented" | Knowledge base |
| **Episodic** | Time-bound events | "Met Sarah at 3pm about API" | Life logging |
| **Hybrid** | Both | "Today I learned Python decorators" | Learning experiences |

### 🔍 Search Features
- **Vector similarity** (cosine distance on embeddings)
- **Full-text search** (PostgreSQL ts_vector)
- **Temporal filtering** (date ranges for episodes)
- **Score fusion** (weighted combination of multiple signals)
- **Context-aware** (personalized to user)

## API Reference

### UnifiedMemorySystem

**Storage**
- `store_memory(text, context=None)` → Auto-routes to semantic/episodic
- `classify_memory_type(text)` → Returns classification info

**Search**
- `search_memory(query, limit=10, memory_type=None)` → Unified search
- `get_context(query=None)` → Complete user profile + relevant memories

**Utility**
- `user_id` - Current user identifier
- `close()` - Close database connection

## Architecture

### Data Flow

```
User Input
    ↓
[Classification Layer]
    ├─ Semantic? (timeless fact)
    ├─ Episodic? (time-bound event)
    └─ Both? (learning experience)
    ↓
[Storage Layer]
    ├─ Semantic DB (user_persona, knowledge_base)
    └─ Episodic DB (episodes, super_chat)
    ↓
[Embedding Layer]
    └─ Groq API (nomic-embed-text-v1.5)
    ↓
[Vector Index]
    └─ pgvector (IVFFlat cosine similarity)

Search Query
    ↓
[Query Embedding]
    ↓
[Parallel Search]
    ├─ Semantic: Vector + Text
    └─ Episodic: Vector + Temporal
    ↓
[Score Fusion & Ranking]
    ↓
[Unified Results]
```

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
