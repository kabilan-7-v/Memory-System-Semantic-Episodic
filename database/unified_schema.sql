-- Unified Schema: Semantic + Episodic Memory System
-- PostgreSQL 17 with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- SEMANTIC MEMORY TABLES
-- ============================================================================

-- User Personas: Personal information layer
CREATE TABLE IF NOT EXISTS user_persona (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255),
    bio TEXT,
    interests TEXT[],
    expertise TEXT[],
    preferences JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge Base: Multi-purpose knowledge storage
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'knowledge', -- knowledge, skill, process
    tags TEXT[] DEFAULT '{}',
    importance_score FLOAT DEFAULT 0.5,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    ts_vector tsvector,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Semantic Memory Index: User-knowledge relationships
CREATE TABLE IF NOT EXISTS semantic_memory_index (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    knowledge_id INTEGER REFERENCES knowledge_base(id) ON DELETE CASCADE,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EPISODIC MEMORY TABLES
-- ============================================================================

-- Super Chat: Ongoing conversations
CREATE TABLE IF NOT EXISTS super_chat (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS super_chat_messages (
    id SERIAL PRIMARY KEY,
    super_chat_id INTEGER REFERENCES super_chat(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    episodized BOOLEAN DEFAULT FALSE,
    episodized_at TIMESTAMP
);

-- Deep Dive Conversations: Focused discussion threads
CREATE TABLE IF NOT EXISTS deepdive_conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(100),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deepdive_messages (
    id SERIAL PRIMARY KEY,
    deepdive_conversation_id INTEGER REFERENCES deepdive_conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Episodes: Consolidated conversation chunks
CREATE TABLE IF NOT EXISTS episodes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(100),
    source_type VARCHAR(50) NOT NULL,  -- 'super_chat' or 'deepdive'
    source_id INTEGER NOT NULL,
    messages JSONB NOT NULL,
    message_count INTEGER NOT NULL,
    date_from TIMESTAMP NOT NULL,
    date_to TIMESTAMP NOT NULL,
    vector vector(384),  -- for sentence-transformers
    created_at TIMESTAMP DEFAULT NOW()
);

-- Instances: Archived episodes
CREATE TABLE IF NOT EXISTS instances (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(100),
    source_type VARCHAR(50) NOT NULL,
    source_id INTEGER NOT NULL,
    original_episode_id INTEGER NOT NULL,
    messages JSONB NOT NULL,
    message_count INTEGER NOT NULL,
    date_from TIMESTAMP NOT NULL,
    date_to TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR SEMANTIC MEMORY
-- ============================================================================

-- Vector similarity indexes for semantic search
CREATE INDEX IF NOT EXISTS idx_user_persona_embedding 
ON user_persona USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding 
ON knowledge_base USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_knowledge_base_ts_vector 
ON knowledge_base USING GIN (ts_vector);

-- Category and tags indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_base_category 
ON knowledge_base(category);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_tags 
ON knowledge_base USING GIN (tags);

-- User lookup indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_base_user_id 
ON knowledge_base(user_id);

CREATE INDEX IF NOT EXISTS idx_semantic_memory_index_user_id 
ON semantic_memory_index(user_id);

-- ============================================================================
-- INDEXES FOR EPISODIC MEMORY
-- ============================================================================

-- Vector similarity index for episodes
CREATE INDEX IF NOT EXISTS idx_episodes_vector 
ON episodes USING ivfflat (vector vector_cosine_ops) 
WITH (lists = 100);

-- User and source lookup indexes
CREATE INDEX IF NOT EXISTS idx_super_chat_user_id 
ON super_chat(user_id);

CREATE INDEX IF NOT EXISTS idx_episodes_user_id 
ON episodes(user_id);

CREATE INDEX IF NOT EXISTS idx_episodes_source 
ON episodes(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_deepdive_conversations_user_id 
ON deepdive_conversations(user_id);

-- Episodization tracking
CREATE INDEX IF NOT EXISTS idx_super_chat_messages_episodized 
ON super_chat_messages(episodized, created_at);

-- ============================================================================
-- TRIGGERS FOR SEMANTIC MEMORY
-- ============================================================================

-- Auto-update ts_vector for full-text search
CREATE OR REPLACE FUNCTION update_knowledge_ts_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.ts_vector := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_knowledge_ts_vector
BEFORE INSERT OR UPDATE ON knowledge_base
FOR EACH ROW
EXECUTE FUNCTION update_knowledge_ts_vector();

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_persona_updated_at
BEFORE UPDATE ON user_persona
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_knowledge_base_updated_at
BEFORE UPDATE ON knowledge_base
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
