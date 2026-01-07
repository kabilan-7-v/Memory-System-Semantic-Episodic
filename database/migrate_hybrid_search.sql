-- Migration: Add Hybrid Search Support (HNSW + BM25)
-- Adds full-text search column and upgrades to HNSW indexes

-- Step 1: Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Step 2: Add full-text search column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'content_tsv'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN content_tsv tsvector 
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title, '')), 'A') || 
                setweight(to_tsvector('english', coalesce(content, '')), 'B')
            ) STORED;
        RAISE NOTICE 'Added content_tsv column to knowledge_base';
    END IF;
END $$;

-- Step 3: Drop old IVFFlat indexes and create HNSW indexes
DO $$ 
BEGIN
    -- Drop old IVFFlat index on knowledge_base if it exists
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'knowledge_base' 
        AND indexname = 'idx_knowledge_base_embedding'
    ) THEN
        DROP INDEX idx_knowledge_base_embedding;
        RAISE NOTICE 'Dropped old IVFFlat index: idx_knowledge_base_embedding';
    END IF;
    
    -- Drop old IVFFlat index on user_personas if it exists
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'user_personas' 
        AND indexname = 'idx_user_personas_embedding'
    ) THEN
        DROP INDEX idx_user_personas_embedding;
        RAISE NOTICE 'Dropped old IVFFlat index: idx_user_personas_embedding';
    END IF;
END $$;

-- Step 4: Create HNSW indexes for better performance
-- HNSW parameters: m=16 (good balance), ef_construction=64 (build quality)
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding_hnsw 
    ON knowledge_base USING hnsw (embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_user_personas_embedding_hnsw 
    ON user_personas USING hnsw (embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

-- Step 5: Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_knowledge_base_content_tsv 
    ON knowledge_base USING GIN(content_tsv);

-- Step 6: Update concepts table index (keep IVFFlat for smaller dataset)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'concepts' 
        AND indexname = 'idx_concepts_embedding'
    ) THEN
        DROP INDEX idx_concepts_embedding;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_concepts_embedding_ivf 
    ON concepts USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Done!
SELECT 'Migration completed successfully!' AS status;
