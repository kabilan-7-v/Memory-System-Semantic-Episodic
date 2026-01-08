# Data Retrieval Guide

## Database Structure

Your office data is stored across multiple tables:

### Semantic Memory (Facts & Knowledge)
- **knowledge_base** - HR policies, management practices, training info
- **semantic_memory_index** - Links users to their knowledge entries

### Episodic Memory (Conversations & Events)
- **super_chat** + **super_chat_messages** - Daily office conversations
- **deepdive_conversations** + **deepdive_messages** - Detailed discussions
- **episodes** - Time-windowed summaries (created every 6 hours)
- **instances** - Long-term archived episodes (>30 days)

---

## SQL Retrieval Examples

### 1. Get All Knowledge for a User
```sql
SELECT kb.id, kb.content, kb.category, kb.tags, kb.created_at
FROM knowledge_base kb
JOIN semantic_memory_index smi ON kb.id = smi.knowledge_id
WHERE smi.user_id = 'hr_manager'
ORDER BY kb.created_at DESC;
```

### 2. Search Knowledge by Keyword
```sql
SELECT content, category, tags
FROM knowledge_base
WHERE content ILIKE '%performance review%'
ORDER BY created_at DESC;
```

### 3. Get Recent Conversations
```sql
SELECT sc.user_id, scm.role, scm.content, scm.created_at
FROM super_chat_messages scm
JOIN super_chat sc ON scm.super_chat_id = sc.id
WHERE sc.user_id = 'tech_lead'
ORDER BY scm.created_at DESC
LIMIT 20;
```

### 4. Get All Episodes for a User
```sql
SELECT id, summary, created_at, message_count
FROM episodes
WHERE user_id = 'hr_manager'
ORDER BY created_at DESC;
```

### 5. Search Deepdive Discussions
```sql
SELECT dc.title, dm.role, dm.content, dm.created_at
FROM deepdive_messages dm
JOIN deepdive_conversations dc ON dm.deepdive_conversation_id = dc.id
WHERE dc.user_id = 'project_manager'
  AND dc.title ILIKE '%budget%'
ORDER BY dm.created_at;
```

### 6. Get Complete User Context
```sql
-- Knowledge
SELECT 'Knowledge' as type, content as data, created_at
FROM knowledge_base 
WHERE user_id = 'hr_manager'

UNION ALL

-- Recent Messages
SELECT 'Chat', scm.content, scm.created_at
FROM super_chat_messages scm
JOIN super_chat sc ON scm.super_chat_id = sc.id
WHERE sc.user_id = 'hr_manager'

UNION ALL

-- Episodes
SELECT 'Episode', summary, created_at
FROM episodes
WHERE user_id = 'hr_manager'

ORDER BY created_at DESC
LIMIT 50;
```

---

## Python Retrieval Methods

### Method 1: Using unified_memory_app.py (Interactive)

```bash
python3 unified_memory_app.py
```

Commands:
- `user hr_manager` - Switch to a specific user
- `search performance review` - Search semantic memory
- `episodes` - View episodic memories
- `context` - Get full context (semantic + episodic)
- `chat what are our HR policies?` - AI chat with full memory

### Method 2: Using simple_realtime_demo.py (Hybrid Search)

```python
# Edit simple_realtime_demo.py or create a new script:

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def hybrid_search(query, user_id='hr_manager', limit=10):
    """Hybrid search: vector similarity + text search"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5435)),
        database=os.getenv('DB_NAME', 'semantic_memory'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '2191'),
        cursor_factory=RealDictCursor
    )
    
    cur = conn.cursor()
    
    # Search knowledge base (text search)
    cur.execute("""
        SELECT 'knowledge' as source, content, category, created_at
        FROM knowledge_base
        WHERE user_id = %s 
          AND content ILIKE %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, f'%{query}%', limit))
    
    knowledge_results = cur.fetchall()
    
    # Search messages (text search)
    cur.execute("""
        SELECT 'message' as source, scm.content, scm.role, scm.created_at
        FROM super_chat_messages scm
        JOIN super_chat sc ON scm.super_chat_id = sc.id
        WHERE sc.user_id = %s
          AND scm.content ILIKE %s
        ORDER BY scm.created_at DESC
        LIMIT %s
    """, (user_id, f'%{query}%', limit))
    
    message_results = cur.fetchall()
    
    # Search episodes
    cur.execute("""
        SELECT 'episode' as source, summary, message_count, created_at
        FROM episodes
        WHERE user_id = %s
          AND summary ILIKE %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, f'%{query}%', limit))
    
    episode_results = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        'knowledge': knowledge_results,
        'messages': message_results,
        'episodes': episode_results
    }

# Usage
results = hybrid_search('performance review', 'hr_manager')
print(f"Found {len(results['knowledge'])} knowledge items")
print(f"Found {len(results['messages'])} messages")
print(f"Found {len(results['episodes'])} episodes")
```

### Method 3: Direct psycopg2 Query

```python
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host='localhost',
    port=5435,
    database='semantic_memory',
    user='postgres',
    password='2191',
    cursor_factory=RealDictCursor
)

cur = conn.cursor()

# Get all HR policies
cur.execute("""
    SELECT content, tags, created_at 
    FROM knowledge_base 
    WHERE category = 'HR Policies'
    ORDER BY created_at DESC
""")

policies = cur.fetchall()
for policy in policies:
    print(f"- {policy['content'][:100]}...")
    
cur.close()
conn.close()
```

---

## Quick Retrieval Commands

### Terminal SQL Queries

```bash
# Get all knowledge for hr_manager
psql -h localhost -p 5435 -U postgres -d semantic_memory -c \
  "SELECT content FROM knowledge_base WHERE user_id = 'hr_manager';"

# Search for specific topic
psql -h localhost -p 5435 -U postgres -d semantic_memory -c \
  "SELECT content FROM knowledge_base WHERE content ILIKE '%onboarding%';"

# Get recent conversations
psql -h localhost -p 5435 -U postgres -d semantic_memory -c \
  "SELECT role, content FROM super_chat_messages LIMIT 10;"

# Get episodes summary
psql -h localhost -p 5435 -U postgres -d semantic_memory -c \
  "SELECT user_id, summary, message_count FROM episodes ORDER BY created_at DESC LIMIT 10;"
```

---

## API Endpoints (If using Flask app)

If you start the Flask API (`python3 src/episodic/app.py`):

- `GET /memories` - Get all memories
- `POST /search` - Search memories
- `GET /episodes` - Get episodes
- `POST /conversations` - Store new conversation

---

## Users Available

- `hr_manager` - HR policies and employee management
- `tech_lead` - Technical leadership and team operations
- `project_manager` - Project planning and stakeholder communication
- `department_head` - Strategic planning and resource allocation
- `employee_001` - General employee perspective

Switch between users in the app with: `user <user_id>`
