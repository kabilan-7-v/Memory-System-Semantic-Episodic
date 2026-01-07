# Semantic Memory System

Simple semantic memory system for storing and retrieving facts and user personas using PostgreSQL 17 and pgvector.

## Architecture

**Workflow: Input → Embedding → Storage → Search**

1. **Input**: User provides a fact or persona detail
2. **Embedding**: Text is converted to a vector using an embedding model (OpenAI/Mock)
3. **Storage**: PostgreSQL 17 stores both the text and vector
4. **Search**: Queries are converted to vectors and matched using similarity search

## Features

- ✅ Store facts with automatic vector embedding
- ✅ Store user personas (name, interests, expertise)
- ✅ Semantic search using vector similarity
- ✅ User context retrieval (persona + relevant facts)
- ✅ Simple, clean API

## Setup

### 1. Connect to Your PostgreSQL Server

You have the following servers in pgAdmin4:
- **Memory-Test** (recommended for this project)
- PostgreSQL 17
- PostgreSQL 18

We'll use the **Memory-Test** server.

### 2. Create Database

Option A: Using pgAdmin4
1. Open pgAdmin4
2. Connect to the "Memory-Test" server
3. Right-click on "Databases" → Create → Database
4. Name it `semantic_memory`
5. **IMPORTANT**: Go to the "Definition" tab
6. Set **Template** to `template0` (fixes locale provider issue)
7. Click Save

**Running the Schema:**
8. In the left panel, expand: Memory-Test → Databases → semantic_memory
9. Right-click on `semantic_memory` database → **Query Tool**
10. In the Query Tool, click **Open File** icon (folder icon in toolbar) OR press `Ctrl+O` (Windows/Linux) or `Cmd+O` (Mac)
11. Navigate to and select: `/Users/sharan/Downloads/September-Test/database/schema.sql`
12. Click **Execute/Run** button (▶ play icon) OR press `F5`
13. You should see "Query returned successfully" message

Option B: Using Terminal (if Memory-Test is on localhost:5432)
```bash
# Create database using template0 to avoid locale provider issues
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE semantic_memory TEMPLATE template0;"

# Run schema
psql -h localhost -p 5432 -U postgres -d semantic_memory -f database/schema.sql
```

**Note**: Using `template0` resolves the locale provider mismatch error between libc and icu.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Memory-Test server credentials:
# - DB_HOST: Usually 'localhost' or your server address
# - DB_PORT: Check your Memory-Test server port (usually 5432)
# - DB_USER: Your PostgreSQL username
# - DB_PASSWORD: Your PostgreSQL password
# - OPENAI_API_KEY: Optional, for embeddings
```

## Quick Start

### 1. Run Demo

```bash
export DB_PORT=5435 && python3 demo.py
```

### 2. Interactive Mode

```bash
export DB_PORT=5435 && python3 interactive.py
```

**Commands:**
- Type any text to store it in memory
- `? <query>` - Search memory
- `user <id>` - Switch user
- `persona <name>` - Create persona
- `context <query>` - Get user context
- `quit` - Exit

## Usage Example

```python
from semantic_memory import SemanticMemory

memory = SemanticMemory()

# 1. Store a fact
fact_id = memory.store_fact(
    content="Python is great for AI development",
    user_id="alice"
)

# 2. Store user persona
persona_id = memory.store_persona(
    user_id="alice",
    name="Alice",
    interests=["AI", "Python"],
    expertise=["machine learning"]
)

# 3. Search memory
results = memory.search(
    query="programming for AI",
    user_id="alice",
    limit=5
)

for result in results:
    print(f"{result['similarity']:.1%}: {result['content']}")

# 4. Get user context
context = memory.g

#### Storage Methods

**`store_fact(content, user_id=None, metadata=None)`**
- Store a fact in memory
- Returns: fact ID

**`store_persona(user_id, name=None, interests=None, expertise=None, preferences=None)`**
- Store user persona
- Returns: persona ID

#### Search Methods

**`search(query, user_id=None, limit=5, min_similarity=0.6)`**
- Search for similar facts
- Returns: List of results with similarity scores

**`search_persona(query, limit=3, min_similarity=0.7)`**
- Search for similar user personas
- Returns: List of matching personas

**`get_user_context(user_id, query=None, limit=5)`**
- Get complete user context (persona + relevant facts)
- Returns: Dictionary with persona and fact
- `add_knowledge_batch(knowledge_items)` - Add multiple items

#### Search Operations

- `search_knowledge(query, user_id, limit, min_similarity, category, tags, search_type)` - Search knowledge
  - `search_type='semantic'` - Vector similarity search
  - `search_type='text'` - Text-based search
- `get_contextual_knowledge(user_id, query, limit)` - Get personalized results
- `get_knowledge_by_category(category, user_id, limit)` - Filter by category
- `get_knowledge_by_tags(tags, user_id, limit)` - Filter by tags

## Database Schema

### Tables

- **user_personas**: User profiles with embeddings
- **knowledge_base**: Knowledge items with vector embeddings
- **semantic_memory_index**: Links between users and knowledge
- **concepts**: Abstract concepts for knowledge graph
- **concept_relationships**: Relationships between concepts

### Indexes

- IVFFlat vector indexes for fast similarity search
- GIN indexes for array fields (tags)
- B-tree indexes for common queries

## Embedding Options

The system supports multiple embedding providers:

1. **OpenAI** (recommended): Set `OPENAI_API_KEY` in `.env`
2. **Mock Embeddings**: Automatic fallback for testing

To use custom embeddings:

```python
from src.services.embedding_service import EmbeddingService, EmbeddingProvider

class CustomProvider(EmbeddingProvider):
    def generate_embedding(self, text: str):
        # Your implementation
        pass

embedding_service = EmbeddingService(provider=CustomProvider())
memory = SemanticMemoryService(embedding_service=embedding_service)
```

## Performance Tips

1. **Vector Index Tuning**: Adjust `lists` parameter based on data size
   - Small datasets (< 10K): lists = 100
   - Medium datasets (10K-100K): lists = 1000
   - Large datasets (> 100K): lists = 2000

2. **Batch Operations**: Use `add_knowledge_batch()` for multiple items

3. **Connection Pooling**: Configure pool size in `DatabaseConfig`

4. **Similarity Threshold**: Adjust `min_similarity` based on use case
   - High precision: 0.8-1.0
   - Balanced: 0.6-0.8
   - High recall: 0.4-0.6

## Integration with Episodic Memory

This semantic memory system is designed to work alongside an episodic memory system:

- **Semantic Memory** (this system): Stores factual knowledge and user personas
- **Episodic Memory** (your teammate): Stores time-based events and interactions

To integrate:

1. Share the same database and user_id schema
2. Use semantic memory for "what the user knows"
3. Use episodic memory for "what the user did"
4. Combine results for comprehensive context

## Troubleshooting

### pgvector extension not found
```sql
-- Connect to database and run:
CREATE EXTENSION IF NOT EXISTS vector;
```

### Connection errors
Check your `.env` file and ensure PostgreSQL is running:
```bash
brew services list
```

### Slow vector searches
Rebuild indexes with appropriate list size:
```sql
DROP INDEX idx_knowledge_base_embedding;
CREATE INDEX idx_knowledge_base_embedding 
ON knowledge_base USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 1000);
```

## License

MIT

## Contributing

Contributions welcome! Please ensure tests pass before submitting PRs.
