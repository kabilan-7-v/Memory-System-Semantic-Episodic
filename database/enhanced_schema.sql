-- Enhanced Schema with Separate Tables for Semantic Memory

-- User Persona Table
CREATE TABLE IF NOT EXISTS user_persona (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT,
    preferences JSONB DEFAULT '{}',
    communication_style JSONB DEFAULT '{}',
    behavior_patterns JSONB DEFAULT '{}',
    traits JSONB DEFAULT '{}',
    interests TEXT[] DEFAULT '{}',
    expertise_areas TEXT[] DEFAULT '{}',
    raw_content TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Table
CREATE TABLE IF NOT EXISTS semantic_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    content_data JSONB DEFAULT '{}',
    category TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    content_tsv tsvector,
    confidence_score FLOAT DEFAULT 1.0,
    source_type TEXT DEFAULT 'user_stated',
    verified BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Process Table
CREATE TABLE IF NOT EXISTS semantic_process (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    description TEXT NOT NULL,
    steps JSONB DEFAULT '[]',
    category TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    content_tsv tsvector,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Skill Table
CREATE TABLE IF NOT EXISTS semantic_skill (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    description TEXT NOT NULL,
    proficiency_level TEXT,
    category TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    content_tsv tsvector,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for vector search (HNSW)
CREATE INDEX IF NOT EXISTS idx_user_persona_embedding ON user_persona USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON semantic_knowledge USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_process_embedding ON semantic_process USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_skill_embedding ON semantic_skill USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Create full-text search indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_tsv ON semantic_knowledge USING gin(content_tsv);
CREATE INDEX IF NOT EXISTS idx_process_tsv ON semantic_process USING gin(content_tsv);
CREATE INDEX IF NOT EXISTS idx_skill_tsv ON semantic_skill USING gin(content_tsv);

-- Create triggers for automatic tsvector updates
CREATE OR REPLACE FUNCTION update_knowledge_tsv() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', COALESCE(NEW.subject, '') || ' ' || COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_process_tsv() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', COALESCE(NEW.process_name, '') || ' ' || COALESCE(NEW.description, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_skill_tsv() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', COALESCE(NEW.skill_name, '') || ' ' || COALESCE(NEW.description, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS knowledge_tsv_update ON semantic_knowledge;
CREATE TRIGGER knowledge_tsv_update BEFORE INSERT OR UPDATE ON semantic_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_knowledge_tsv();

DROP TRIGGER IF EXISTS process_tsv_update ON semantic_process;
CREATE TRIGGER process_tsv_update BEFORE INSERT OR UPDATE ON semantic_process
    FOR EACH ROW EXECUTE FUNCTION update_process_tsv();

DROP TRIGGER IF EXISTS skill_tsv_update ON semantic_skill;
CREATE TRIGGER skill_tsv_update BEFORE INSERT OR UPDATE ON semantic_skill
    FOR EACH ROW EXECUTE FUNCTION update_skill_tsv();

-- Indexes for user_id lookups
CREATE INDEX IF NOT EXISTS idx_user_persona_user_id ON user_persona(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_user_id ON semantic_knowledge(user_id);
CREATE INDEX IF NOT EXISTS idx_process_user_id ON semantic_process(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_user_id ON semantic_skill(user_id);
