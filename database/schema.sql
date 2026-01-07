-- Semantic Memory System Schema for PostgreSQL 17 with pgvector
-- This schema supports knowledge storage and user persona management with vector search

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- User Personas Table
-- Stores user-specific information and preferences for personalized context
CREATE TABLE user_personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    traits JSONB DEFAULT '{}',
    communication_style TEXT,
    interests TEXT[],
    expertise_areas TEXT[],
    embedding vector(1536), -- Embedding dimension (1536 for OpenAI, adjust as needed)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Base Table
-- Stores semantic knowledge chunks with embeddings for RAG/context retrieval
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255), -- Optional: user-specific knowledge
    title VARCHAR(500),
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- text, code, fact, concept, etc.
    category VARCHAR(100),
    tags TEXT[],
    embedding vector(1536), -- Embedding dimension
    source VARCHAR(500),
    confidence_score FLOAT DEFAULT 1.0,
    importance_score FLOAT DEFAULT 0.5,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE
);

-- Semantic Memory Index
-- Links knowledge to users and tracks usage patterns
CREATE TABLE semantic_memory_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    knowledge_id UUID REFERENCES knowledge_base(id) ON DELETE CASCADE,
    relevance_score FLOAT DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context_tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, knowledge_id)
);

-- Concepts and Relationships Table
-- Stores abstract concepts and their relationships for knowledge graph
CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255), -- NULL for global concepts
    concept_name VARCHAR(255) NOT NULL,
    description TEXT,
    concept_type VARCHAR(100), -- entity, skill, topic, preference, etc.
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, concept_name)
);

-- Concept Relationships for knowledge graph
CREATE TABLE concept_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    target_concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100), -- is_a, related_to, requires, implies, etc.
    strength FLOAT DEFAULT 0.5,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_concept_id, target_concept_id, relationship_type)
);

-- Add full-text search column for BM25-style ranking
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS content_tsv tsvector 
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') || 
        setweight(to_tsvector('english', coalesce(content, '')), 'B')
    ) STORED;

-- Create indexes for performance
-- Using HNSW for better performance with vector search (optimized for 10GB+ datasets)
CREATE INDEX idx_user_personas_user_id ON user_personas(user_id);
CREATE INDEX idx_user_personas_embedding ON user_personas USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_knowledge_base_user_id ON knowledge_base(user_id);
CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_base_tags ON knowledge_base USING GIN(tags);

-- HNSW index for vector search (m=16 for balanced recall/memory, ef_construction=64 for build quality)
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- GIN index for full-text search (BM25-style ranking)
CREATE INDEX idx_knowledge_base_content_tsv ON knowledge_base USING GIN(content_tsv);

CREATE INDEX idx_knowledge_base_content_type ON knowledge_base(content_type);

CREATE INDEX idx_semantic_memory_user_id ON semantic_memory_index(user_id);
CREATE INDEX idx_semantic_memory_knowledge_id ON semantic_memory_index(knowledge_id);
CREATE INDEX idx_semantic_memory_relevance ON semantic_memory_index(relevance_score DESC);

CREATE INDEX idx_concepts_user_id ON concepts(user_id);
CREATE INDEX idx_concepts_type ON concepts(concept_type);
CREATE INDEX idx_concepts_embedding ON concepts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_concept_relationships_source ON concept_relationships(source_concept_id);
CREATE INDEX idx_concept_relationships_target ON concept_relationships(target_concept_id);
CREATE INDEX idx_concept_relationships_type ON concept_relationships(relationship_type);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_personas_updated_at BEFORE UPDATE ON user_personas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_concepts_updated_at BEFORE UPDATE ON concepts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
