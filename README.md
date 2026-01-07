# Semantic Memory System

AI-powered memory system with automatic classification and semantic search using PostgreSQL 17, pgvector, and Groq LLM.

## 🧠 How It Works

### Input Processing & Classification
When you provide text, the system uses Groq LLM to automatically classify and store it in one of four semantic layers:

1. **User Persona** - Personal information, preferences, traits
   - *Example: "I'm a software engineer who loves Python"*
   - *Stored in: `user_persona` table*

2. **Knowledge** - Facts, concepts, general information
   - *Example: "Python is great for AI development"*
   - *Stored in: `knowledge_base` table with category tags*

3. **Skills** - Abilities, competencies, expertise
   - *Example: "I can build REST APIs with FastAPI"*
   - *Stored in: `knowledge_base` table with category='skill'*

4. **Process** - Procedures, workflows, how-to knowledge
   - *Example: "To deploy, run docker build then docker push"*
   - *Stored in: `knowledge_base` table with category='process'*

### Search Algorithm

**Hybrid Search System** combining semantic and keyword matching:

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

**Key Features:**
- ✅ Automatic classification into semantic layers
- ✅ Vector embeddings for semantic understanding
- ✅ Hybrid search (semantic + keyword)
- ✅ User-specific context retrieval
- ✅ Groq LLM integration for intelligent responses

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Create database
psql -U postgres -c "CREATE DATABASE semantic_memory TEMPLATE template0;"

# Run schema
psql -U postgres -d semantic_memory -f database/schema.sql
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials:
# DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, GROQ_API_KEY
```

### 4. Run Application
```bash
python3 enhanced_memory_app.py
```

## Database Schema

### Core Tables

**`user_persona`** - Personal information layer
- Stores: name, bio, interests, expertise, preferences
- Vector embedding for semantic profile matching

**`knowledge_base`** - Multi-purpose knowledge storage
- Stores: content, category (knowledge/skill/process), tags
- Vector embedding for semantic search
- Full-text search support

**`semantic_memory_index`** - User-knowledge relationships
- Links users to their knowledge items
- Tracks access patterns and importance scores

## Usage Example

```python
from enhanced_memory_app import EnhancedMemoryApp

app = EnhancedMemoryApp()

# Store different types of information
# The system automatically classifies and routes to the correct layer

# 1. User Persona (automatically detected)
app.store_memory("I'm Alice, a Python developer who loves AI")
# → Stored in: user_persona table

# 2. Knowledge (automatically detected)
app.store_memory("Python uses dynamic typing")
# → Stored in: knowledge_base (category: knowledge)

# 3. Skill (automatically detected)
app.store_memory("I can build REST APIs with FastAPI")
# → Stored in: knowledge_base (category: skill)

# 4. Process (automatically detected)
app.store_memory("To deploy: git push, then run docker build")
# → Stored in: knowledge_base (category: process)

# Search with hybrid algorithm
results = app.search_all("What can I do with Python?")
for result in results:
    print(f"{result['type']}: {result['content']}")
    print(f"Relevance: {result['score']:.2%}\n")
```

## API Reference

### Storage
- `store_memory(text, user_id)` - Auto-classify and store
- `store_knowledge(content, category, tags)` - Manual storage

### Search
- `search_all(query, limit, min_similarity)` - Hybrid search across all layers
- `search_by_category(query, category)` - Filter by semantic layer
- `get_user_context(user_id)` - Get complete user profile
## Tech Stack

- **Database**: PostgreSQL 17 with pgvector extension
- **LLM**: Groq API (Llama models) for classification & embeddings
- **Vector Search**: IVFFlat indexes for efficient similarity search
- **Text Search**: PostgreSQL full-text search (ts_vector)

## License

MIT
