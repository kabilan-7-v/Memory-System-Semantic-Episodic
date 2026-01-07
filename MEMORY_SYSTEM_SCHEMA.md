# BAP Memory System - Developer Documentation

Stack: PostgreSQL 15+ with pgvector Extension
Vector Dimension: 1536 (OpenAI ada-002 compatible)

## Table of Contents

1. [Overview](#overview)
2. [Database Setup](#database-setup)
3. [Memory Architecture](#memory-architecture)
4. [Schema Definitions](#schema-definitions)
   - [Short-Term Memory](#short-term-memory)
   - [Long-Term Memory - Conversations](#long-term-memory---conversations)
   - [Long-Term Memory - Summaries](#long-term-memory---summaries)
   - [Long-Term Memory - Semantic](#long-term-memory---semantic)
   - [Long-Term Memory - Files](#long-term-memory---files)
   - [Lifecycle Management](#lifecycle-management)
   - [Freshness Tracking](#freshness-tracking)
5. [Indexing Strategy](#indexing-strategy)
6. [Performance Optimization](#performance-optimization)
7. [Search Implementation](#search-implementation)
   - [Hybrid Search](#1-hybrid-search-vector--full-text-combined)
   - [Search Types](#2-search-types)
   - [Search API Patterns](#3-search-api-patterns)
   - [Ranking & Relevance](#4-ranking--relevance)
   - [Performance Considerations](#5-performance-considerations)

---

## Overview

The BAP Memory System is a multi-tiered memory architecture designed for AI agents, combining PostgreSQL's robust data management with pgvector's efficient vector similarity search capabilities.

### Memory Hierarchy

```
┌─────────────────────────────────────────────┐
│          SHORT-TERM MEMORY                  │
│  - Working Memory (Charter, Notes, Context) │
│  - Cache Entries (L1, L2, L3)              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│          LONG-TERM MEMORY                   │
│  ┌───────────────────────────────────────┐  │
│  │ Episodic (Conversations & Summaries)  │  │
│  │  - Super Chat Messages                │  │
│  │  - Deep Dive Conversations            │  │
│  │  - Episodes (< 30 days)               │  │
│  │  - Instances (> 30 days)              │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ Semantic Memory                       │  │
│  │  - User Persona                       │  │
│  │  - Knowledge & Entities               │  │
│  │  - Processes & Skills                 │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ File Memory (User Files)              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## Database Setup

### Required Extensions

```sql
-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram similarity
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector for embeddings

-- Configure vector extension
SET ivfflat.probes = 10;
```

### Installation Steps

1. **Install PostgreSQL 15+**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-15

# macOS (Homebrew)
brew install postgresql@15
```

2. **Install pgvector Extension**
```bash
# Clone pgvector repository
git clone --branch v0.5.0 https://github.com/pgvector/pgvector.git
cd pgvector

# Build and install
make
sudo make install

# Or using package manager (Ubuntu/Debian)
sudo apt install postgresql-15-pgvector
```

3. **Enable Extensions in Database**
```sql
-- Connect to your database
\c bap_database

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

---

## Memory Architecture

### Key Concepts

1. Short-Term Memory (STM): Temporary storage for active execution state
   - Charter Store: Execution blueprints from Planner Agent
   - Agent Notes: Scratchpad for agent reasoning
   - Recent Context: Last 15 contexts from Dynamic Context Management
   - TTL: 24 hours (auto-cleanup)

2. Long-Term Memory (LTM): Persistent storage organized by type
   - **Episodic**: Time-ordered conversation history
   - **Semantic**: Facts, knowledge, and learned behaviors
   - **Files**: User document storage with content extraction

3. Memory Lifecycle:
   ```
   Messages → Episodes (< 30 days) → Instances (> 30 days) → Archive/Compression
   ```

---

## Schema Definitions

### Short-Term Memory

#### 1. Working Memory

Stores active execution state with automatic expiration.

```sql
CREATE TABLE working_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    task_id UUID REFERENCES tasks(id),
    type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,  -- Charter schema (agents[], dag{}, resources{}, metadata{})
    priority INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours',

    CONSTRAINT chk_wm_type CHECK (type IN ('charter_store', 'agent_notes', 'recent_context'))
);

-- Indexes
CREATE INDEX idx_working_memory_user ON working_memory(user_id);
CREATE INDEX idx_working_memory_task ON working_memory(task_id);
CREATE INDEX idx_working_memory_expires ON working_memory(expires_at);
CREATE INDEX idx_working_memory_type ON working_memory(user_id, type);

-- Optimized index for Charter queries (status filtering common)
CREATE INDEX idx_working_memory_charter_status ON working_memory(user_id, type, (content->>'status'))
WHERE type = 'charter_store';
```

**Content Types:**
- `charter_store`: Execution blueprints created by Planner Agent
- `agent_notes`: Agent scratchpad for reasoning during execution
- `recent_context`: Last 15 contexts built by Dynamic Context Management

#### 2. Cache Entries

Tracks cache metadata for Redis invalidation.

```sql
CREATE TABLE cache_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    cache_key VARCHAR(255) NOT NULL,
    cache_type VARCHAR(50) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, cache_key),
    CONSTRAINT chk_cache_type CHECK (cache_type IN ('l1_hot', 'l2_warm', 'l3_cold'))
);

-- Indexes
CREATE INDEX idx_cache_user ON cache_entries(user_id);
CREATE INDEX idx_cache_expires ON cache_entries(expires_at);
```

---

### Long-Term Memory - Conversations

Messages are episodized every 6 hours. Episodes < 30 days stay in `episodes` table, then migrate to `instances` table.

#### 3. Super Chat

One Super Chat per user for continuous conversations.

```sql
CREATE TABLE super_chat (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE super_chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    super_chat_id UUID NOT NULL REFERENCES super_chat(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    task_id UUID REFERENCES tasks(id),
    model_used VARCHAR(100),
    tokens_used INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    episodized BOOLEAN NOT NULL DEFAULT FALSE,
    episodized_at TIMESTAMPTZ,

    CONSTRAINT chk_sc_role CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes
CREATE INDEX idx_super_chat_messages_chat ON super_chat_messages(super_chat_id);
CREATE INDEX idx_super_chat_messages_created ON super_chat_messages(created_at DESC);
CREATE INDEX idx_super_chat_messages_not_episodized ON super_chat_messages(super_chat_id, created_at)
    WHERE episodized = FALSE;
```

#### 4. Deep Dive Conversations

Project-based conversations with tenant isolation.

```sql
CREATE TABLE deepdive_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    mode VARCHAR(20) NOT NULL DEFAULT 'personal',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,

    CONSTRAINT chk_dd_mode CHECK (mode IN ('personal', 'team')),
    CONSTRAINT chk_dd_status CHECK (status IN ('active', 'archived'))
);

-- Indexes
CREATE INDEX idx_deepdive_conv_user ON deepdive_conversations(user_id);
CREATE INDEX idx_deepdive_conv_tenant ON deepdive_conversations(tenant_id);
CREATE INDEX idx_deepdive_conv_status ON deepdive_conversations(status);
```

#### 5. Deep Dive Messages

Raw messages within Deep Dive conversations.

```sql
CREATE TABLE deepdive_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deepdive_conversation_id UUID NOT NULL REFERENCES deepdive_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    task_id UUID REFERENCES tasks(id),
    model_used VARCHAR(100),
    tokens_used INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    episodized BOOLEAN NOT NULL DEFAULT FALSE,
    episodized_at TIMESTAMPTZ,

    CONSTRAINT chk_dd_msg_role CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes
CREATE INDEX idx_deepdive_messages_conv ON deepdive_messages(deepdive_conversation_id);
CREATE INDEX idx_deepdive_messages_created ON deepdive_messages(created_at DESC);
CREATE INDEX idx_deepdive_messages_not_episodized ON deepdive_messages(deepdive_conversation_id, created_at)
    WHERE episodized = FALSE;
```

#### 6. Episodes

Complete raw text of recent episodes (< 30 days old).

```sql
CREATE TABLE episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    source_type VARCHAR(20) NOT NULL,
    source_id UUID NOT NULL,
    messages JSONB NOT NULL,
    message_count INTEGER NOT NULL,
    date_from TIMESTAMPTZ NOT NULL,
    date_to TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_episode_source CHECK (source_type IN ('super_chat', 'deepdive'))
);

-- Indexes
CREATE INDEX idx_episodes_user ON episodes(user_id);
CREATE INDEX idx_episodes_source ON episodes(source_type, source_id);
CREATE INDEX idx_episodes_date_from ON episodes(date_from);
CREATE INDEX idx_episodes_created ON episodes(created_at);
-- Index for finding episodes older than 30 days (for instancization job)
CREATE INDEX idx_episodes_old ON episodes(created_at) WHERE created_at <= NOW() - INTERVAL '30 days';
```

#### 7. Instances

Complete raw text of archived instances (episodes > 30 days old).

```sql
CREATE TABLE instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    source_type VARCHAR(20) NOT NULL,
    source_id UUID NOT NULL,
    original_episode_id UUID,
    messages JSONB NOT NULL,
    message_count INTEGER NOT NULL,
    date_from TIMESTAMPTZ NOT NULL,
    date_to TIMESTAMPTZ NOT NULL,
    compressed BOOLEAN NOT NULL DEFAULT FALSE,
    archived_data BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    instancized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_instance_source CHECK (source_type IN ('super_chat', 'deepdive'))
);

-- Indexes
CREATE INDEX idx_instances_user ON instances(user_id);
CREATE INDEX idx_instances_source ON instances(source_type, source_id);
CREATE INDEX idx_instances_date_from ON instances(date_from);
```

---

### Long-Term Memory - Summaries

Summaries reference raw conversations in episodes/instances tables.

#### 8. Episode Summaries

Searchable summaries with vector embeddings for recent episodes.

```sql
CREATE TABLE episode_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL UNIQUE REFERENCES episodes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    key VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    content_embedding vector(1536),
    importance_score DECIMAL(3, 2),
    date_from TIMESTAMPTZ NOT NULL,
    date_to TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_episode_sum_user ON episode_summaries(user_id);
CREATE INDEX idx_episode_sum_embedding ON episode_summaries USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_episode_sum_tags ON episode_summaries USING gin(tags);
CREATE INDEX idx_episode_sum_key_fts ON episode_summaries USING gin(to_tsvector('english', key || ' ' || description));
```

#### 9. Instance Summaries

Searchable summaries with vector embeddings for archived instances.

```sql
CREATE TABLE instance_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_id UUID NOT NULL UNIQUE REFERENCES instances(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    key VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    content_embedding vector(1536),
    importance_score DECIMAL(3, 2),
    date_from TIMESTAMPTZ NOT NULL,
    date_to TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_instance_sum_user ON instance_summaries(user_id);
CREATE INDEX idx_instance_sum_embedding ON instance_summaries USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_instance_sum_tags ON instance_summaries USING gin(tags);
CREATE INDEX idx_instance_sum_key_fts ON instance_summaries USING gin(to_tsvector('english', key || ' ' || description));
```

---

### Long-Term Memory - Semantic

Stores learned facts, preferences, and behavioral patterns.

#### 10. User Persona

User preferences, communication style, and behavioral patterns.

```sql
CREATE TABLE user_persona (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    preferences JSONB NOT NULL DEFAULT '{}',
    communication_style JSONB NOT NULL DEFAULT '{}',
    behavior_patterns JSONB NOT NULL DEFAULT '{}',
    content_embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_persona_user ON user_persona(user_id);
CREATE INDEX idx_user_persona_embedding ON user_persona USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
```

#### 11. Semantic Knowledge

Knowledge, entities, processes, and skills stored in semantic memory.

```sql
CREATE TABLE semantic_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    type VARCHAR(50) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    content_embedding vector(1536),
    confidence_score DECIMAL(3, 2),
    source_type VARCHAR(50),
    source_refs JSONB,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_sk_type CHECK (type IN ('knowledge', 'entity', 'process', 'skill')),
    CONSTRAINT chk_sk_source CHECK (source_type IS NULL OR source_type IN ('user_stated', 'inferred', 'asset_derived'))
);

-- Indexes
CREATE INDEX idx_semantic_know_user ON semantic_knowledge(user_id);
CREATE INDEX idx_semantic_know_type ON semantic_knowledge(type);
CREATE INDEX idx_semantic_know_subject ON semantic_knowledge(subject);
CREATE INDEX idx_semantic_know_embedding ON semantic_knowledge USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
```

---

### Long-Term Memory - Files

Document storage with content extraction and vector search.

#### 12. User Files

Personal files uploaded by users with content extraction.

```sql
CREATE TABLE user_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path TEXT NOT NULL,
    content_text TEXT,
    content_embedding vector(1536),
    metadata JSONB NOT NULL DEFAULT '{}',
    last_accessed_at TIMESTAMPTZ,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_files_user ON user_files(user_id);
CREATE INDEX idx_user_files_tenant ON user_files(tenant_id);
CREATE INDEX idx_user_files_type ON user_files(file_type);
CREATE INDEX idx_user_files_last_accessed ON user_files(last_accessed_at DESC);
CREATE INDEX idx_user_files_embedding ON user_files USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_user_files_content_fts ON user_files USING gin(to_tsvector('english', content_text)) WHERE content_text IS NOT NULL;
```

---

### Lifecycle Management

#### 13. Lifecycle Audit

Comprehensive audit trail for all memory lifecycle events.

```sql
CREATE TABLE lifecycle_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_lifecycle_event CHECK (event_type IN (
        'episode_instance_migration',
        'auto_archive',
        'manual_archive',
        'restore',
        'user_deletion',
        'compression',
        'cache_cleanup'
    )),
    CONSTRAINT chk_lifecycle_entity CHECK (entity_type IN (
        'episode',
        'instance',
        'craft',
        'deepdive',
        'user',
        'cache'
    )),
    CONSTRAINT chk_lifecycle_action CHECK (action IN (
        'migrated',
        'archived',
        'restored',
        'deleted',
        'compressed',
        'decompressed',
        'cleaned'
    ))
);

-- Indexes
CREATE INDEX idx_lifecycle_event_type ON lifecycle_audit(event_type);
CREATE INDEX idx_lifecycle_entity ON lifecycle_audit(entity_type, entity_id);
CREATE INDEX idx_lifecycle_user ON lifecycle_audit(user_id);
CREATE INDEX idx_lifecycle_timestamp ON lifecycle_audit(timestamp DESC);
```

---

### Freshness Tracking

#### 14. Memory Freshness

Tracks access patterns for context optimization.

```sql
CREATE TABLE memory_freshness (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What memory record
    memory_type TEXT NOT NULL, -- 'episode', 'instance', 'knowledge', 'persona', 'file'
    memory_id UUID NOT NULL,   -- References specific record
    user_id UUID NOT NULL REFERENCES users(id),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    -- Freshness timestamps
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_updated_at TIMESTAMPTZ, -- When underlying source changed (e.g., file updated)

    -- Computed scores
    access_freshness_score DECIMAL(3, 2) NOT NULL DEFAULT 1.0, -- 1.0 (fresh) to 0.0 (30+ days)
    change_frequency DECIMAL(3, 2), -- How often this memory changes

    -- Context tracking
    last_access_context TEXT, -- 'context_assembly', 'user_query', 'background_task'

    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Composite unique constraint
    UNIQUE(memory_type, memory_id)
);

-- Indexes
CREATE INDEX idx_freshness_user ON memory_freshness(user_id);
CREATE INDEX idx_freshness_type ON memory_freshness(memory_type);
CREATE INDEX idx_freshness_score ON memory_freshness(access_freshness_score DESC);
CREATE INDEX idx_freshness_stale ON memory_freshness(last_accessed_at) WHERE access_freshness_score < 0.5;
```

**Usage:**
- Prioritizes fresh memories in context assembly (20% score boost)
- Detects stale assets (>7 days) and notifies user
- Auto-trigger re-processing for critical stale assets (>14 days + frequently accessed)

---

## Indexing Strategy

### Vector Indexes (IVFFlat)

All embedding columns use IVFFlat indexes for approximate nearest neighbor (ANN) search with cosine similarity:

```sql
-- Episode summaries
CREATE INDEX idx_episode_sum_embedding ON episode_summaries
USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);

-- Instance summaries
CREATE INDEX idx_instance_sum_embedding ON instance_summaries
USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);

-- User persona
CREATE INDEX idx_user_persona_embedding ON user_persona
USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);

-- Semantic knowledge
CREATE INDEX idx_semantic_know_embedding ON semantic_knowledge
USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);

-- User files
CREATE INDEX idx_user_files_embedding ON user_files
USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
```

**IVFFlat Configuration:**
- `lists = 100`: Number of clusters/partitions (optimal for 10K-1M vectors)
- `vector_cosine_ops`: Cosine similarity operator class
- `ivfflat.probes = 10`: Number of lists to search at query time
- Optimal `lists` value: `sqrt(num_rows)` rounded to nearest 10

**Vector Distance Operators:**
- `<=>` : Cosine distance (0 = identical, 2 = opposite)
- `<->` : L2/Euclidean distance
- `<#>` : Inner product (negative for similarity)

### Full-Text Search Indexes (GIN + BM25)

PostgreSQL's native full-text search using GIN indexes with BM25-like ranking via `ts_rank`:

```sql
-- Episode summaries
CREATE INDEX idx_episode_sum_key_fts ON episode_summaries
USING gin(to_tsvector('english', key || ' ' || description));

-- Instance summaries
CREATE INDEX idx_instance_sum_key_fts ON instance_summaries
USING gin(to_tsvector('english', key || ' ' || description));

-- User files content
CREATE INDEX idx_user_files_content_fts ON user_files
USING gin(to_tsvector('english', content_text))
WHERE content_text IS NOT NULL;
```

**Full-Text Search Components:**
- `to_tsvector('english', text)`: Tokenizes and stems text
- `plainto_tsquery('english', query)`: Converts plain text query to search query
- `@@`: Match operator for full-text search
- `ts_rank()`: BM25-like ranking function (considers term frequency and document length)

### Array Indexes (GIN)

For tag-based filtering:

```sql
CREATE INDEX idx_episode_sum_tags ON episode_summaries USING gin(tags);
CREATE INDEX idx_instance_sum_tags ON instance_summaries USING gin(tags);
```

### JSONB Indexes

For filtering on JSONB fields:

```sql
-- Charter status filtering
CREATE INDEX idx_working_memory_charter_status
ON working_memory(user_id, type, (content->>'status'))
WHERE type = 'charter_store';
```

### Partial Indexes

For common filtering patterns:

```sql
-- Episodes older than 30 days (for migration job)
CREATE INDEX idx_episodes_old ON episodes(created_at)
WHERE created_at <= NOW() - INTERVAL '30 days';

-- Non-episodized messages
CREATE INDEX idx_super_chat_messages_not_episodized
ON super_chat_messages(super_chat_id, created_at)
WHERE episodized = FALSE;

-- Stale memory (freshness tracking)
CREATE INDEX idx_freshness_stale ON memory_freshness(last_accessed_at)
WHERE access_freshness_score < 0.5;
```

---

## Performance Optimization

### 1. Connection Pooling

```javascript
// Using pg-pool (Node.js example)
const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.DB_HOST,
  port: 5432,
  database: 'bap_database',
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 20,                    // Maximum pool size
  idleTimeoutMillis: 30000,   // Close idle clients after 30s
  connectionTimeoutMillis: 2000,
});
```

### 2. IVFFlat Index Tuning

**Configuration Parameters:**

```sql
-- At session level
SET ivfflat.probes = 10;  -- Default: good balance of speed/accuracy

-- For higher accuracy (slower)
SET ivfflat.probes = 20;

-- For faster search (less accurate)
SET ivfflat.probes = 5;
```

**Index Build Parameters:**

```sql
-- For small datasets (< 10K vectors)
CREATE INDEX idx_name ON table USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- For medium datasets (10K - 100K vectors)
CREATE INDEX idx_name ON table USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- For large datasets (100K - 1M vectors)
CREATE INDEX idx_name ON table USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);

-- For very large datasets (> 1M vectors)
CREATE INDEX idx_name ON table USING ivfflat (embedding vector_cosine_ops) WITH (lists = 2000);
```

### 3. Query Optimization

**Optimize vector search with user-based pre-filtering:**

```sql
-- Good: Filter by user_id first, then vector search
SELECT * FROM episode_summaries
WHERE user_id = $1
ORDER BY content_embedding <=> $2::vector
LIMIT 10;

-- Bad: Vector search across all users
SELECT * FROM episode_summaries
ORDER BY content_embedding <=> $1::vector
LIMIT 10;
```

**Use EXPLAIN ANALYZE to verify index usage:**

```sql
EXPLAIN ANALYZE
SELECT * FROM episode_summaries
WHERE user_id = 'uuid-here'
ORDER BY content_embedding <=> '[...]'::vector
LIMIT 10;
```

### 4. Batch Operations

```javascript
// Batch insert for episodes
const insertBatch = async (episodes) => {
  const values = episodes.map((e, i) =>
    `($${i*7+1}, $${i*7+2}, $${i*7+3}, $${i*7+4}, $${i*7+5}, $${i*7+6}, $${i*7+7})`
  ).join(',');

  const query = `
    INSERT INTO episodes (user_id, source_type, source_id, messages, message_count, date_from, date_to)
    VALUES ${values}
  `;

  const flatParams = episodes.flatMap(e => [
    e.user_id, e.source_type, e.source_id,
    JSON.stringify(e.messages), e.message_count, e.date_from, e.date_to
  ]);

  await pool.query(query, flatParams);
};
```

### 5. Caching Strategy

**Three-tier cache architecture:**

```
L1 (Hot):  Redis, TTL 5min   → Most recent contexts, active charters
L2 (Warm): Redis, TTL 1hr    → Recent summaries, frequent searches
L3 (Cold): Postgres          → Full memory archive
```

### 6. Regular Maintenance

```sql
-- Vacuum and analyze (run weekly)
VACUUM ANALYZE episodes;
VACUUM ANALYZE instances;
VACUUM ANALYZE episode_summaries;
VACUUM ANALYZE instance_summaries;

-- Reindex vector indexes (run monthly)
REINDEX INDEX CONCURRENTLY idx_episode_sum_embedding;
REINDEX INDEX CONCURRENTLY idx_instance_sum_embedding;
```

---

## Search Implementation

### Overview

The BAP Memory System uses a hybrid search approach combining:
- **Vector Similarity Search (IVFFlat)**: Semantic understanding via embeddings
- **Full-Text Search (GIN + BM25)**: Keyword matching with relevance ranking
- **Metadata Filtering**: Date ranges, tags, importance scores, freshness

### 1. Hybrid Search (Vector + Full-Text Combined)

Combines semantic similarity and keyword matching for optimal results.

#### Episode Summaries Hybrid Search

```sql
-- Hybrid search with weighted ranking
SELECT
    es.id,
    es.key,
    es.description,
    es.date_from,
    es.date_to,
    es.importance_score,
    es.tags,
    -- Vector similarity score (0 to 1, higher is better)
    1 - (es.content_embedding <=> $1::vector) AS vector_similarity,
    -- Full-text search rank (BM25-like)
    ts_rank(
        to_tsvector('english', es.key || ' ' || es.description),
        plainto_tsquery('english', $2)
    ) AS text_rank,
    -- Combined weighted score (70% vector, 30% text)
    (
        (1 - (es.content_embedding <=> $1::vector)) * 0.7 +
        ts_rank(to_tsvector('english', es.key || ' ' || es.description), plainto_tsquery('english', $2)) * 0.3
    ) AS combined_score
FROM episode_summaries es
WHERE
    es.user_id = $3
    AND (
        -- Match either by vector similarity OR full-text search
        es.content_embedding <=> $1::vector < 0.3  -- Cosine distance threshold
        OR to_tsvector('english', es.key || ' ' || es.description) @@ plainto_tsquery('english', $2)
    )
ORDER BY combined_score DESC
LIMIT 20;
```

**Parameters:**
- `$1`: Query embedding vector (1536 dimensions)
- `$2`: Plain text query string
- `$3`: User ID

**Threshold Tuning:**
- `< 0.3`: High similarity (strict matching)
- `< 0.5`: Medium similarity (balanced)
- `< 0.7`: Low similarity (broader results)

#### Instance Summaries Hybrid Search

```sql
-- Same pattern for archived instances
SELECT
    is_tbl.id,
    is_tbl.key,
    is_tbl.description,
    is_tbl.date_from,
    is_tbl.date_to,
    1 - (is_tbl.content_embedding <=> $1::vector) AS vector_similarity,
    ts_rank(
        to_tsvector('english', is_tbl.key || ' ' || is_tbl.description),
        plainto_tsquery('english', $2)
    ) AS text_rank,
    (
        (1 - (is_tbl.content_embedding <=> $1::vector)) * 0.7 +
        ts_rank(to_tsvector('english', is_tbl.key || ' ' || is_tbl.description), plainto_tsquery('english', $2)) * 0.3
    ) AS combined_score
FROM instance_summaries is_tbl
WHERE
    is_tbl.user_id = $3
    AND (
        is_tbl.content_embedding <=> $1::vector < 0.3
        OR to_tsvector('english', is_tbl.key || ' ' || is_tbl.description) @@ plainto_tsquery('english', $2)
    )
ORDER BY combined_score DESC
LIMIT 20;
```

### 2. Search Types

#### A. Semantic Search (Pure Vector Similarity)

For concept-based queries where meaning matters more than exact keywords.

```sql
-- Semantic search on episode summaries
SELECT
    id,
    key,
    description,
    1 - (content_embedding <=> $1::vector) AS similarity
FROM episode_summaries
WHERE
    user_id = $2
    AND content_embedding <=> $1::vector < 0.4  -- Similarity threshold
ORDER BY content_embedding <=> $1::vector  -- Sort by distance (ascending = more similar)
LIMIT 10;
```

**Use Cases:**
- "Find conversations about machine learning" (matches ML, AI, neural networks, etc.)
- "What did we discuss about project deadlines?" (semantic understanding)
- Cross-lingual concept matching

#### B. Keyword Search (Pure Full-Text)

For exact term matching and phrase searches.

```sql
-- Full-text keyword search
SELECT
    id,
    key,
    description,
    ts_rank(
        to_tsvector('english', key || ' ' || description),
        plainto_tsquery('english', $1)
    ) AS rank,
    ts_headline(
        'english',
        description,
        plainto_tsquery('english', $1),
        'MaxWords=50, MinWords=25'
    ) AS snippet
FROM episode_summaries
WHERE
    user_id = $2
    AND to_tsvector('english', key || ' ' || description) @@ plainto_tsquery('english', $1)
ORDER BY rank DESC
LIMIT 10;
```

**Use Cases:**
- "Find mentions of 'API v2.0'" (exact version number)
- "Search for 'John Smith'" (specific name)
- Technical terms, product names, specific phrases

#### C. Filtered Search with Metadata

Combine search with date ranges, tags, and importance.

```sql
-- Filtered hybrid search
SELECT
    es.id,
    es.key,
    es.description,
    es.date_from,
    es.tags,
    es.importance_score,
    1 - (es.content_embedding <=> $1::vector) AS similarity,
    ts_rank(
        to_tsvector('english', es.key || ' ' || es.description),
        plainto_tsquery('english', $2)
    ) AS text_rank
FROM episode_summaries es
WHERE
    es.user_id = $3
    -- Date range filter
    AND es.date_from >= $4::timestamptz
    AND es.date_to <= $5::timestamptz
    -- Tag filter (array overlap)
    AND (
        $6::text[] IS NULL OR
        es.tags && $6::text[]  -- Overlaps operator
    )
    -- Importance threshold
    AND (es.importance_score IS NULL OR es.importance_score >= $7)
    -- Search conditions
    AND (
        es.content_embedding <=> $1::vector < 0.3
        OR to_tsvector('english', es.key || ' ' || es.description) @@ plainto_tsquery('english', $2)
    )
ORDER BY
    es.importance_score DESC NULLS LAST,
    (1 - (es.content_embedding <=> $1::vector)) DESC
LIMIT 20;
```

**Parameters:**
- `$4`, `$5`: Date range (from, to)
- `$6`: Array of tags to filter by
- `$7`: Minimum importance score (0.0 to 1.0)

#### D. Multi-Table Search (Episodes + Instances + Knowledge)

Search across all memory types simultaneously.

```sql
-- Union search across multiple tables
WITH episode_results AS (
    SELECT
        id,
        'episode' AS source_type,
        key AS title,
        description,
        date_from AS created_at,
        1 - (content_embedding <=> $1::vector) AS similarity,
        ts_rank(to_tsvector('english', key || ' ' || description), plainto_tsquery('english', $2)) AS text_rank
    FROM episode_summaries
    WHERE
        user_id = $3
        AND (
            content_embedding <=> $1::vector < 0.3
            OR to_tsvector('english', key || ' ' || description) @@ plainto_tsquery('english', $2)
        )
),
instance_results AS (
    SELECT
        id,
        'instance' AS source_type,
        key AS title,
        description,
        date_from AS created_at,
        1 - (content_embedding <=> $1::vector) AS similarity,
        ts_rank(to_tsvector('english', key || ' ' || description), plainto_tsquery('english', $2)) AS text_rank
    FROM instance_summaries
    WHERE
        user_id = $3
        AND (
            content_embedding <=> $1::vector < 0.3
            OR to_tsvector('english', key || ' ' || description) @@ plainto_tsquery('english', $2)
        )
),
knowledge_results AS (
    SELECT
        id,
        'knowledge' AS source_type,
        subject AS title,
        content::text AS description,
        created_at,
        1 - (content_embedding <=> $1::vector) AS similarity,
        ts_rank(to_tsvector('english', subject || ' ' || content::text), plainto_tsquery('english', $2)) AS text_rank
    FROM semantic_knowledge
    WHERE
        user_id = $3
        AND (
            content_embedding <=> $1::vector < 0.3
            OR to_tsvector('english', subject || ' ' || content::text) @@ plainto_tsquery('english', $2)
        )
)
SELECT * FROM episode_results
UNION ALL
SELECT * FROM instance_results
UNION ALL
SELECT * FROM knowledge_results
ORDER BY
    (similarity * 0.7 + text_rank * 0.3) DESC
LIMIT 30;
```

### 3. Search API Patterns

#### Pattern 1: Simple Semantic Search

```javascript
const searchMemoryBySemantic = async (userId, queryText) => {
  // Generate embedding for query
  const embedding = await generateEmbedding(queryText);

  const query = `
    SELECT
      id, key, description,
      1 - (content_embedding <=> $1::vector) AS similarity
    FROM episode_summaries
    WHERE user_id = $2
      AND content_embedding <=> $1::vector < 0.4
    ORDER BY content_embedding <=> $1::vector
    LIMIT 10;
  `;

  return await pool.query(query, [JSON.stringify(embedding), userId]);
};
```

#### Pattern 2: Hybrid Search with Pagination

```javascript
const searchMemoryHybrid = async (userId, queryText, page = 1, pageSize = 20) => {
  const embedding = await generateEmbedding(queryText);
  const offset = (page - 1) * pageSize;

  const query = `
    SELECT
      id, key, description, date_from, date_to,
      1 - (content_embedding <=> $1::vector) AS vector_similarity,
      ts_rank(to_tsvector('english', key || ' ' || description), plainto_tsquery('english', $2)) AS text_rank,
      (
        (1 - (content_embedding <=> $1::vector)) * 0.7 +
        ts_rank(to_tsvector('english', key || ' ' || description), plainto_tsquery('english', $2)) * 0.3
      ) AS combined_score
    FROM episode_summaries
    WHERE
      user_id = $3
      AND (
        content_embedding <=> $1::vector < 0.3
        OR to_tsvector('english', key || ' ' || description) @@ plainto_tsquery('english', $2)
      )
    ORDER BY combined_score DESC
    LIMIT $4 OFFSET $5;
  `;

  return await pool.query(query, [
    JSON.stringify(embedding),
    queryText,
    userId,
    pageSize,
    offset
  ]);
};
```

#### Pattern 3: Filtered Search

```javascript
const searchMemoryFiltered = async (userId, queryText, filters = {}) => {
  const embedding = await generateEmbedding(queryText);

  const {
    dateFrom,
    dateTo,
    tags,
    minImportance = 0.0,
    limit = 20
  } = filters;

  const query = `
    SELECT
      id, key, description, date_from, date_to, tags, importance_score,
      1 - (content_embedding <=> $1::vector) AS similarity
    FROM episode_summaries
    WHERE
      user_id = $2
      AND ($3::timestamptz IS NULL OR date_from >= $3)
      AND ($4::timestamptz IS NULL OR date_to <= $4)
      AND ($5::text[] IS NULL OR tags && $5)
      AND (importance_score IS NULL OR importance_score >= $6)
      AND content_embedding <=> $1::vector < 0.4
    ORDER BY
      importance_score DESC NULLS LAST,
      content_embedding <=> $1::vector
    LIMIT $7;
  `;

  return await pool.query(query, [
    JSON.stringify(embedding),
    userId,
    dateFrom || null,
    dateTo || null,
    tags || null,
    minImportance,
    limit
  ]);
};
```

#### Pattern 4: File Content Search

```javascript
const searchFileContent = async (userId, queryText) => {
  const embedding = await generateEmbedding(queryText);

  const query = `
    SELECT
      id, filename, file_type, content_text,
      1 - (content_embedding <=> $1::vector) AS vector_similarity,
      ts_rank(to_tsvector('english', content_text), plainto_tsquery('english', $2)) AS text_rank,
      ts_headline(
        'english',
        content_text,
        plainto_tsquery('english', $2),
        'MaxWords=50, MinWords=25'
      ) AS snippet
    FROM user_files
    WHERE
      user_id = $3
      AND content_text IS NOT NULL
      AND (
        content_embedding <=> $1::vector < 0.3
        OR to_tsvector('english', content_text) @@ plainto_tsquery('english', $2)
      )
    ORDER BY
      (vector_similarity * 0.6 + text_rank * 0.4) DESC
    LIMIT 15;
  `;

  return await pool.query(query, [
    JSON.stringify(embedding),
    queryText,
    userId
  ]);
};
```

### 4. Ranking & Relevance

#### Freshness Boosting

Prioritize recently accessed memories with freshness score.

```sql
-- Search with freshness boost
SELECT
    es.id,
    es.key,
    es.description,
    1 - (es.content_embedding <=> $1::vector) AS vector_similarity,
    ts_rank(to_tsvector('english', es.key || ' ' || es.description), plainto_tsquery('english', $2)) AS text_rank,
    COALESCE(mf.access_freshness_score, 0.5) AS freshness,
    -- Combined score with freshness boost (20%)
    (
        (1 - (es.content_embedding <=> $1::vector)) * 0.5 +
        ts_rank(to_tsvector('english', es.key || ' ' || es.description), plainto_tsquery('english', $2)) * 0.3 +
        COALESCE(mf.access_freshness_score, 0.5) * 0.2
    ) AS final_score
FROM episode_summaries es
LEFT JOIN memory_freshness mf ON mf.memory_type = 'episode' AND mf.memory_id = es.id
WHERE
    es.user_id = $3
    AND (
        es.content_embedding <=> $1::vector < 0.3
        OR to_tsvector('english', es.key || ' ' || es.description) @@ plainto_tsquery('english', $2)
    )
ORDER BY final_score DESC
LIMIT 20;
```

#### Importance Score Weighting

Combine multiple relevance signals.

```sql
-- Multi-signal ranking
SELECT
    es.id,
    es.key,
    es.description,
    es.importance_score,
    1 - (es.content_embedding <=> $1::vector) AS vector_similarity,
    ts_rank(to_tsvector('english', es.key || ' ' || es.description), plainto_tsquery('english', $2)) AS text_rank,
    COALESCE(mf.access_freshness_score, 0.5) AS freshness,
    -- Weighted combined score
    (
        (1 - (es.content_embedding <=> $1::vector)) * 0.40 +  -- Vector: 40%
        ts_rank(to_tsvector('english', es.key || ' ' || es.description), plainto_tsquery('english', $2)) * 0.25 +  -- Text: 25%
        COALESCE(mf.access_freshness_score, 0.5) * 0.15 +     -- Freshness: 15%
        COALESCE(es.importance_score, 0.5) * 0.20              -- Importance: 20%
    ) AS final_score
FROM episode_summaries es
LEFT JOIN memory_freshness mf ON mf.memory_type = 'episode' AND mf.memory_id = es.id
WHERE
    es.user_id = $3
    AND (
        es.content_embedding <=> $1::vector < 0.3
        OR to_tsvector('english', es.key || ' ' || es.description) @@ plainto_tsquery('english', $2)
    )
ORDER BY final_score DESC
LIMIT 20;
```

**Weighting Strategies:**

| Use Case | Vector | Text | Freshness | Importance |
|----------|--------|------|-----------|------------|
| Semantic-focused | 70% | 20% | 5% | 5% |
| Keyword-focused | 30% | 60% | 5% | 5% |
| Balanced hybrid | 50% | 30% | 10% | 10% |
| Recency-focused | 40% | 25% | 25% | 10% |
| Priority-focused | 35% | 25% | 10% | 30% |

#### Recency Decay Function

Time-based relevance decay for temporal queries.

```sql
-- Search with time-based decay
SELECT
    es.id,
    es.key,
    es.description,
    es.date_from,
    1 - (es.content_embedding <=> $1::vector) AS vector_similarity,
    -- Exponential decay: 1.0 (today) → 0.5 (30 days) → 0.25 (60 days)
    EXP(-0.023 * EXTRACT(EPOCH FROM (NOW() - es.date_from)) / 86400) AS recency_score,
    (
        (1 - (es.content_embedding <=> $1::vector)) * 0.6 +
        EXP(-0.023 * EXTRACT(EPOCH FROM (NOW() - es.date_from)) / 86400) * 0.4
    ) AS final_score
FROM episode_summaries es
WHERE
    es.user_id = $2
    AND es.content_embedding <=> $1::vector < 0.4
ORDER BY final_score DESC
LIMIT 20;
```

### 5. Performance Considerations

#### When to Use Vector Search
- ✅ Concept-based queries ("find similar conversations")
- ✅ Cross-lingual searches
- ✅ Fuzzy semantic matching
- ✅ User doesn't know exact keywords
- ❌ Exact phrase matching (use full-text instead)
- ❌ Very short queries (< 3 words) - less effective

#### When to Use Full-Text Search
- ✅ Exact term matching ("find 'API v2.0'")
- ✅ Named entities (people, products, locations)
- ✅ Technical jargon and acronyms
- ✅ Boolean queries (AND, OR, NOT)
- ❌ Concept similarity (use vector instead)
- ❌ Multilingual queries (use vector instead)

#### When to Use Hybrid Search
- ✅ General-purpose search
- ✅ Unknown user intent
- ✅ Best recall and precision balance
- ✅ Production-ready default approach
- ⚠️ Slightly slower than single-method search

#### Query Optimization Tips

1. **Pre-filter by user_id**: Always filter by user before vector search
2. **Use appropriate thresholds**: Adjust cosine distance based on use case
3. **Limit result set**: Use LIMIT to prevent full table scans
4. **Cache embeddings**: Store query embeddings for repeated searches
5. **Monitor index usage**: Use EXPLAIN ANALYZE to verify IVFFlat usage

```sql
-- Verify index usage
EXPLAIN ANALYZE
SELECT * FROM episode_summaries
WHERE user_id = 'uuid-here'
  AND content_embedding <=> '[...]'::vector < 0.3
ORDER BY content_embedding <=> '[...]'::vector
LIMIT 10;

-- Should show: "Index Scan using idx_episode_sum_embedding on episode_summaries"
```

---

## Additional Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [IVFFlat Index Tuning](https://github.com/pgvector/pgvector#ivfflat)
- [PostgreSQL ts_rank (BM25-like)](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-RANKING)