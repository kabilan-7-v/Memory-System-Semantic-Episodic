-- Enhanced Schema with Metadata Filtering Support
-- Migration script to add/enhance metadata columns and indexes

-- ============================================================================
-- ENHANCE KNOWLEDGE_BASE TABLE
-- ============================================================================

-- Ensure metadata column exists and has proper type
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;
END $$;

-- Add source tracking if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'source'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN source VARCHAR(100) DEFAULT 'manual';
    END IF;
END $$;

-- Add confidence score if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN confidence_score FLOAT DEFAULT 1.0;
    END IF;
END $$;

-- Add content_type if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'content_type'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN content_type VARCHAR(50) DEFAULT 'text';
    END IF;
END $$;

-- Add title if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'title'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN title VARCHAR(255);
    END IF;
END $$;

-- Add last_accessed_at for tracking usage
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge_base' AND column_name = 'last_accessed_at'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN last_accessed_at TIMESTAMP;
    END IF;
END $$;

-- ============================================================================
-- ENHANCE EPISODES TABLE
-- ============================================================================

-- Add metadata to episodes
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'episodes' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE episodes ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;
END $$;

-- Add importance score to episodes
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'episodes' AND column_name = 'importance_score'
    ) THEN
        ALTER TABLE episodes ADD COLUMN importance_score FLOAT DEFAULT 0.5;
    END IF;
END $$;

-- Add tags to episodes
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'episodes' AND column_name = 'tags'
    ) THEN
        ALTER TABLE episodes ADD COLUMN tags TEXT[] DEFAULT '{}';
    END IF;
END $$;

-- ============================================================================
-- CREATE INDEXES FOR METADATA FILTERING
-- ============================================================================

-- GIN index for JSONB metadata (supports fast filtering on nested fields)
CREATE INDEX IF NOT EXISTS idx_knowledge_metadata 
ON knowledge_base USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_episodes_metadata 
ON episodes USING GIN (metadata);

-- B-tree indexes for commonly filtered fields
CREATE INDEX IF NOT EXISTS idx_knowledge_category 
ON knowledge_base(category);

CREATE INDEX IF NOT EXISTS idx_knowledge_importance 
ON knowledge_base(importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_created_at 
ON knowledge_base(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_user_category 
ON knowledge_base(user_id, category);

-- GIN index for tag arrays (supports overlap operators &&, @>, <@)
CREATE INDEX IF NOT EXISTS idx_knowledge_tags 
ON knowledge_base USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_episodes_tags 
ON episodes USING GIN (tags);

-- Composite indexes for common filter combinations
CREATE INDEX IF NOT EXISTS idx_knowledge_user_importance_date 
ON knowledge_base(user_id, importance_score DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_episodes_user_date 
ON episodes(user_id, date_from DESC);

-- ============================================================================
-- ADD USEFUL METADATA FIELDS TO EXISTING TABLES
-- ============================================================================

-- Add department to user_persona for organizational filtering
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_persona' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE user_persona ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;
END $$;

-- ============================================================================
-- CREATE HELPER FUNCTIONS FOR METADATA QUERIES
-- ============================================================================

-- Function to extract metadata field as text
CREATE OR REPLACE FUNCTION get_metadata_field(metadata_col JSONB, field_path TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN metadata_col #>> string_to_array(field_path, '.');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to check if metadata contains key-value pair
CREATE OR REPLACE FUNCTION metadata_matches(metadata_col JSONB, key TEXT, value TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (metadata_col ->> key) = value;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- SAMPLE METADATA STRUCTURES (for documentation)
-- ============================================================================

-- Example metadata for knowledge_base:
-- {
--   "department": "engineering",
--   "project": "api-redesign",
--   "verified": true,
--   "version": "2.0",
--   "author": "tech_lead_001",
--   "review_status": "approved",
--   "confidential": false,
--   "location": "San Francisco",
--   "related_docs": ["doc_123", "doc_456"]
-- }

-- Example metadata for episodes:
-- {
--   "meeting_type": "standup",
--   "participants": ["user_001", "user_002"],
--   "action_items": 3,
--   "duration_minutes": 30,
--   "sentiment": "positive",
--   "topics": ["sprint planning", "bug fixes"]
-- }

-- ============================================================================
-- UPDATE STATISTICS
-- ============================================================================

ANALYZE knowledge_base;
ANALYZE episodes;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check metadata support
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('knowledge_base', 'episodes')
    AND column_name IN ('metadata', 'tags', 'importance_score', 'category')
ORDER BY table_name, column_name;

-- Check indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('knowledge_base', 'episodes')
    AND indexname LIKE '%metadata%' OR indexname LIKE '%tags%' OR indexname LIKE '%importance%'
ORDER BY tablename, indexname;

COMMENT ON COLUMN knowledge_base.metadata IS 'JSONB field for flexible metadata filtering. Use GIN index for fast queries.';
COMMENT ON COLUMN episodes.metadata IS 'JSONB field for episode metadata. Supports nested field queries.';
COMMENT ON COLUMN knowledge_base.tags IS 'Array of tags. Use GIN index for ANY/ALL filtering with &&, @> operators.';
COMMENT ON COLUMN episodes.tags IS 'Array of tags for categorizing episodes.';

-- Sample query examples:
-- 1. Find knowledge by metadata field:
--    SELECT * FROM knowledge_base WHERE metadata->>'department' = 'engineering';
--
-- 2. Find by nested metadata:
--    SELECT * FROM knowledge_base WHERE metadata->'settings'->>'priority' = 'high';
--
-- 3. Find by any tag:
--    SELECT * FROM knowledge_base WHERE tags && ARRAY['python', 'api'];
--
-- 4. Find by all tags:
--    SELECT * FROM knowledge_base WHERE tags @> ARRAY['python', 'backend'];
--
-- 5. Combined metadata + importance:
--    SELECT * FROM knowledge_base 
--    WHERE metadata->>'department' = 'engineering' 
--      AND importance_score > 0.7
--      AND created_at > NOW() - INTERVAL '7 days';
