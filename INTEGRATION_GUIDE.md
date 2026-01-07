# Integration Guide: Unified Memory System

## Overview

This project now combines **two powerful memory systems**:

1. **Semantic Memory** (from your original project)
   - Long-term factual knowledge
   - User personas, skills, processes
   - Always available, context-rich

2. **Episodic Memory** (from cloned repository)
   - Time-based conversation episodes
   - Chat history with episodization
   - "Remember when we talked about...?" capability

## What Was Integrated

### Files Added

```
src/episodic/                      ← New episodic modules
├── episodization.py              → Converts chats to episodes
├── hybrid_retriever.py           → Episode search (vector + BM25)
├── chat_service.py               → Chat management
├── context_builder.py            → Context assembly
├── embeddings.py                 → Sentence-transformers
├── bm25_index.py                 → Keyword search
├── db.py & db_setup.py           → Database utilities
└── jobs/                         → Background episodization tasks

database/unified_schema.sql        ← Combined schema
unified_memory_app.py              ← Main unified application
```

### Dependencies Added

- `sentence-transformers` - For episodic embeddings (384-dim)
- `flask` - Optional REST API support

## Architecture

### Memory Flow

```
User Input
    ↓
┌─────────────────────────────────────────┐
│  Is it a chat conversation?             │
├─────────────────┬───────────────────────┤
│      YES        │         NO            │
│       ↓         │         ↓             │
│  EPISODIC       │    SEMANTIC           │
│  - Store in     │    - Auto-classify    │
│    chat         │    - Store in:        │
│  - Auto-        │      * user_persona   │
│    episodize    │      * knowledge_base │
│    after 2min   │                       │
└─────────────────┴───────────────────────┘
            ↓
    Search/Retrieval
            ↓
┌─────────────────────────────────────────┐
│     Unified Context Assembly            │
├─────────────────────────────────────────┤
│  • User Persona                         │
│  • Relevant Knowledge (semantic)        │
│  • Recent Chat (episodic)               │
│  • Past Episodes (episodic)             │
└─────────────────────────────────────────┘
            ↓
      AI Response
```

## Database Schema Changes

### New Tables (Episodic)

1. **super_chat** & **super_chat_messages**
   - Stores ongoing conversations
   - Messages auto-episodize after 2 minutes

2. **episodes**
   - Consolidated conversation chunks
   - 384-dim vector embeddings
   - Enables semantic episode search

3. **deepdive_conversations** & **deepdive_messages**
   - Separate focused discussion threads

4. **instances**
   - Archived episodes for long-term storage

### Existing Tables (Semantic)
- `user_persona` - Unchanged
- `knowledge_base` - Unchanged
- `semantic_memory_index` - Unchanged

## Usage Comparison

### Before (Semantic Only)
```python
from enhanced_memory_app import EnhancedMemoryApp

app = EnhancedMemoryApp()
app.store_memory("I love Python")  # Store fact
results = app.search_all("Python")  # Search
```

### After (Unified)
```python
from unified_memory_app import UnifiedMemorySystem

app = UnifiedMemorySystem()

# Semantic storage (same as before)
app.classify_and_store("I love Python")

# NEW: Episodic chat with full context
response = app.chat("What languages do I know?")
# Uses: persona + knowledge + past conversations

# NEW: Search episodes
episodes = app.search_episodes("Python deployment")

# NEW: Get complete context
context = app.get_full_context("What can I do?")
```

## Setup Instructions

### 1. Update Database

**Option A: Fresh Install**
```bash
psql -U postgres -d semantic_memory -f database/unified_schema.sql
```

**Option B: Migrate Existing Database**
```sql
-- Add episodic tables to existing database
-- Run the episodic sections from unified_schema.sql manually
```

### 2. Install New Dependencies
```bash
pip install -r requirements.txt
# New: sentence-transformers, flask
```

### 3. Run Unified Application
```bash
python3 unified_memory_app.py
```

## Key Differences

| Feature | Semantic Only | Unified System |
|---------|--------------|----------------|
| **Memory Type** | Facts only | Facts + Conversations |
| **Time Context** | No | Yes (when it happened) |
| **Chat Support** | No | Yes (with episodization) |
| **Episode Search** | No | Yes |
| **Vector Dim** | 1536 (hash-based) | 1536 (semantic) + 384 (episodic) |
| **Search Types** | Vector + Text | Vector + Text + BM25 |
| **Context** | Persona + Knowledge | Persona + Knowledge + Episodes |

## Background Jobs (Optional)

For automatic episodization, run these background jobs:

```bash
# Episodize old chats (every 5 minutes)
python3 src/episodic/jobs/run_episodization.py

# Archive old episodes (daily)
python3 src/episodic/jobs/run_instancization.py
```

## Migration Path

### For Existing Users

Your existing data is **100% compatible**:

1. Semantic tables unchanged
2. New episodic tables added separately
3. Can use both `enhanced_memory_app.py` (old) and `unified_memory_app.py` (new)

### Recommendation

- **Development/Testing**: Use `unified_memory_app.py`
- **Production**: Gradually migrate to unified system
- **Fallback**: Original `enhanced_memory_app.py` still works

## Benefits

✅ **Complete Memory**: Both "what you know" and "what happened"
✅ **Better Context**: AI has full conversation history
✅ **Time Awareness**: "Remember last week when...?"
✅ **Backwards Compatible**: Existing semantic data preserved
✅ **Flexible**: Can use semantic-only or unified mode

## Next Steps

1. ✅ Database schema created
2. ✅ Code integrated
3. ✅ README updated
4. ⏭️ Test with sample data
5. ⏭️ Set up background episodization jobs
6. ⏭️ Optional: Add REST API (Flask app included)

---

**Questions?** Check the main README.md or review the code in `unified_memory_app.py`
