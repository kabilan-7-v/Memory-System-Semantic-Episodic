# 🎯 Unified Memory System Demo

## Overview

The **Unified Memory System** provides a single interface that automatically routes input to both semantic and episodic memory systems based on content.

## How It Works

### 1. Automatic Classification

```python
from unified_memory_system import UnifiedMemorySystem

memory = UnifiedMemorySystem(user_id="alice")

# Input gets automatically classified
result = memory.store_memory("Today I learned Python decorators at the workshop")
```

**Classification Result:**
```json
{
  "is_semantic": true,
  "is_episodic": true,
  "semantic_type": "knowledge",
  "episodic_type": "event",
  "reasoning": "Contains both timeless knowledge (decorators) and time-bound event (today, workshop)"
}
```

**Storage:**
- ✓ Semantic Memory: `knowledge_base` table (category: knowledge)
- ✓ Episodic Memory: `episodes` table (type: event)

---

### 2. Different Input Types

#### Pure Semantic (Persona)
```python
memory.store_memory("I'm a software engineer who loves Python and AI")
```
→ **Stored in:** `user_persona` table only

#### Pure Semantic (Knowledge)
```python
memory.store_memory("Python uses dynamic typing and supports multiple paradigms")
```
→ **Stored in:** `knowledge_base` (category: knowledge)

#### Pure Semantic (Skill)
```python
memory.store_memory("I can build REST APIs with FastAPI and deploy with Docker")
```
→ **Stored in:** `knowledge_base` (category: skill)

#### Pure Episodic (Event)
```python
memory.store_memory("Met Sarah at the coffee shop at 3pm to discuss the API design")
```
→ **Stored in:** `episodes` table only

#### Hybrid (Both)
```python
memory.store_memory("During today's meeting, I discovered that PostgreSQL's JSONB is faster than JSON")
```
→ **Stored in:** Both `knowledge_base` AND `episodes`

---

### 3. Unified Search

```python
# Search across both memory types
results = memory.search_memory("What do I know about Python?", limit=10)

# Results include both semantic and episodic
for result in results:
    print(f"Type: {result['memory_type']}")
    print(f"Content: {result['content']}")
    print(f"Relevance: {result['score']:.2%}")
    print(f"When: {result['timestamp']}")
    print("---")
```

**Example Output:**
```
Type: semantic
Content: I'm a software engineer who loves Python and AI
Relevance: 95.3%
When: 2026-01-07 10:15:00
---
Type: semantic
Content: Python uses dynamic typing and supports multiple paradigms
Relevance: 92.1%
When: 2026-01-07 10:16:00
---
Type: episodic
Content: Today I learned Python decorators at the workshop
Relevance: 88.7%
When: 2026-01-07 11:30:00
---
```

---

### 4. Context Retrieval

```python
# Get complete user context
context = memory.get_context("Tell me about my Python knowledge")

print(f"Semantic memories: {len(context['semantic_memories'])}")
print(f"Episodic memories: {len(context['episodic_memories'])}")

# Access specific memories
for mem in context['semantic_memories']:
    print(f"  [{mem['semantic_category']}] {mem['content']}")

for mem in context['episodic_memories']:
    print(f"  [{mem['episode_type']}] {mem['content']} - {mem['timestamp']}")
```

---

## Interactive Demo

### Run the System
```bash
python3 unified_memory_system.py
```

### Try These Commands

1. **Store different types of memories:**
   ```
   > I'm Alice, a machine learning engineer
   > Python is great for data science
   > I can train neural networks with PyTorch
   > Today I deployed my first ML model to production
   > Met with the team to discuss the new recommendation system
   ```

2. **Search your memories:**
   ```
   > search What have I learned?
   > search What happened today?
   > search What are my skills?
   ```

3. **Get full context:**
   ```
   > context Tell me about my work
   > context
   ```

---

## Architecture Benefits

### ✅ Single Interface
- One function for all memory types
- No need to manually choose semantic vs episodic

### ✅ Automatic Classification
- AI-powered routing using Groq LLM
- Handles hybrid inputs (both semantic and episodic)

### ✅ Unified Search
- Search across all memory types simultaneously
- Results ranked by relevance
- Temporal context preserved for episodic

### ✅ Complete Context
- Combines persona, knowledge, skills, and experiences
- Provides comprehensive user profile

---

## Use Cases

### 1. Personal Knowledge Management
```
Store: "Read an article about quantum computing today"
→ Knowledge (semantic) + Event (episodic)
Search: "What did I learn this week?"
→ Returns both facts and experiences
```

### 2. Skill Tracking
```
Store: "Completed course on React hooks"
→ Skill (semantic) + Event (episodic)
Search: "What skills do I have?"
→ Returns capabilities with acquisition timeline
```

### 3. Meeting Notes
```
Store: "In the standup, we decided to use GraphQL for the API"
→ Knowledge (semantic) + Interaction (episodic)
Search: "What decisions did we make?"
→ Returns decisions with context
```

### 4. Life Logging
```
Store: "Visited the art museum, learned about impressionism"
→ Knowledge (semantic) + Event (episodic)
Search: "What places have I visited?"
→ Returns experiences with learned information
```

---

## Comparison with Separate Systems

### Before (Separate)
```python
# Had to manually choose
semantic_memory.store_fact("Python is great")
episodic_memory.store_event("Learned Python today")

# Had to search separately
semantic_results = semantic_memory.search("Python")
episodic_results = episodic_memory.search("Python")
# Manually combine and rank results
```

### After (Unified)
```python
# Automatic routing
memory.store_memory("Learned Python today - it's great!")

# Automatic combination
results = memory.search_memory("Python")
# Already combined and ranked
```

---

## Next Steps

1. **Try the demo:** `python3 unified_memory_system.py`
2. **Explore APIs:** Check `README.md` for full API reference
3. **Customize:** Modify classification logic in `classify_memory_type()`
4. **Integrate:** Use `UnifiedMemorySystem` class in your applications

---

## Technical Details

- **Classification:** Groq LLM (llama-3.3-70b-versatile)
- **Embeddings:** Groq (nomic-embed-text-v1.5, 1536-dim)
- **Vector Search:** pgvector (IVFFlat cosine similarity)
- **Database:** PostgreSQL 17 with pgvector extension
- **Search Algorithm:** Hybrid (vector similarity + full-text)
