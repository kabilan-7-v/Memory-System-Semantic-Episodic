# 🔍 Metadata Filtering System - Complete Guide

## Overview

The metadata filtering system provides **10 advanced filtering techniques** to precisely control what data is retrieved from your memory system. This goes beyond semantic similarity to enable exact, contextual, and business-logic-driven queries.

## Why Metadata Filtering is Essential

### 1. **Precision**
- Get exactly what you need, not just semantically similar results
- Filter by exact values, ranges, patterns, and complex conditions

### 2. **Performance**
- Pre-filter large datasets before expensive embedding operations
- Use indexed fields for fast queries (10-100x faster)
- Reduce vector search space for better scalability

### 3. **Security & Compliance**
- Implement row-level security (filter by user, tenant, department)
- Audit trails and data governance
- GDPR compliance (filter by consent, data retention)

### 4. **Context Awareness**
- Time-based queries ("show me what happened today")
- Location-based filtering
- User/team/project isolation

### 5. **Business Logic**
- Priority filtering (urgent, high-importance items)
- Status-based queries (approved, pending, archived)
- Custom metadata fields for any domain

---

## 🎯 10 Filtering Techniques

### 1. Exact Match Filtering

**Use Case:** Find items with specific categorical values

```python
from src.services.metadata_filter import FilterBuilder

# Filter by category
filter_obj = FilterBuilder.equals("category", "knowledge")

# Filter by user
filter_obj = FilterBuilder.equals("user_id", "user_001")

# Filter by nested metadata
filter_obj = FilterBuilder.equals("metadata.department", "engineering")
```

**SQL Generated:**
```sql
WHERE category = 'knowledge'
WHERE metadata->>'department' = 'engineering'
```

**Best For:** Categories, status fields, IDs, boolean flags

---

### 2. Range Filtering

**Use Case:** Numeric and date ranges

```python
# Importance score range
filter_obj = FilterBuilder.greater_than("importance_score", 0.7)
filter_obj = FilterBuilder.between("importance_score", 0.5, 0.9)

# Date ranges
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(days=7)
filter_obj = FilterBuilder.greater_than("created_at", cutoff)
```

**SQL Generated:**
```sql
WHERE importance_score > 0.7
WHERE importance_score BETWEEN 0.5 AND 0.9
WHERE created_at >= '2026-01-04T00:00:00'
```

**Best For:** Scores, ratings, timestamps, quantities, prices

---

### 3. Multi-value Filtering (Array Operations)

**Use Case:** Tag matching, skill filtering, category lists

```python
from src.services.metadata_filter import MetadataFilter, FilterOperator

# Item has ANY of these tags
filter_obj = MetadataFilter("tags", FilterOperator.ANY_OF, ["python", "api", "backend"])

# Item has ALL of these tags
filter_obj = MetadataFilter("tags", FilterOperator.ALL_OF, ["python", "backend"])

# Item has NONE of these tags
filter_obj = MetadataFilter("tags", FilterOperator.NONE_OF, ["deprecated", "archived"])
```

**SQL Generated:**
```sql
WHERE tags && ARRAY['python', 'api', 'backend']  -- ANY_OF (overlap)
WHERE tags @> ARRAY['python', 'backend']         -- ALL_OF (contains)
WHERE NOT (tags && ARRAY['deprecated'])          -- NONE_OF
```

**Performance:** Uses GIN indexes on array columns (very fast)

**Best For:** Tags, skills, categories, permissions, features

---

### 4. Hierarchical Filtering (Nested JSONB)

**Use Case:** Filter by nested metadata fields

```python
# Single level
filter_obj = FilterBuilder.equals("metadata.department", "engineering")

# Multiple levels
filter_obj = FilterBuilder.equals("metadata.project.status", "active")
filter_obj = FilterBuilder.equals("metadata.settings.notifications.email", True)

# Numeric nested fields
filter_obj = FilterBuilder.greater_than("metadata.metrics.response_time", 500)
```

**SQL Generated:**
```sql
WHERE metadata->>'department' = 'engineering'
WHERE metadata->'project'->>'status' = 'active'
WHERE metadata->'settings'->'notifications'->>'email' = 'true'
WHERE (metadata->'metrics'->>'response_time')::float > 500
```

**Best For:** Flexible schemas, evolving data models, multi-tenant apps

---

### 5. Composite Filtering (AND/OR/NOT)

**Use Case:** Combine multiple conditions with boolean logic

```python
from src.services.metadata_filter import FilterGroup, LogicalOperator

# AND: All conditions must be true
filter_group = FilterGroup(operator=LogicalOperator.AND)
filter_group.add_filter(FilterBuilder.equals("category", "knowledge"))
filter_group.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
filter_group.add_filter(FilterBuilder.recent("created_at", days=7))

# OR: Any condition can be true
or_group = FilterGroup(operator=LogicalOperator.OR)
or_group.add_filter(FilterBuilder.equals("category", "urgent"))
or_group.add_filter(FilterBuilder.greater_than("importance_score", 0.9))

# Nested groups
main_filter = FilterGroup(operator=LogicalOperator.AND)
main_filter.add_filter(FilterBuilder.equals("category", "knowledge"))
main_filter.add_filter(or_group)  # Add the OR group
```

**SQL Generated:**
```sql
WHERE category = 'knowledge' 
  AND importance_score > 0.7 
  AND created_at >= '2026-01-04'
  
WHERE category = 'urgent' OR importance_score > 0.9

WHERE category = 'knowledge' 
  AND (category = 'urgent' OR importance_score > 0.9)
```

**Best For:** Complex business rules, multi-criteria searches

---

### 6. Pattern Matching (Regex, Wildcards)

**Use Case:** Flexible text matching

```python
# Contains substring
filter_obj = FilterBuilder.contains("title", "API", case_sensitive=False)

# Starts with
filter_obj = MetadataFilter("title", FilterOperator.STARTS_WITH, "How to")

# Ends with
filter_obj = MetadataFilter("filename", FilterOperator.ENDS_WITH, ".pdf")

# Regular expression
filter_obj = MetadataFilter(
    "content", 
    FilterOperator.REGEX, 
    r"\b(python|java|rust)\b"
)
```

**SQL Generated:**
```sql
WHERE title ILIKE '%API%'
WHERE title LIKE 'How to%'
WHERE filename LIKE '%.pdf'
WHERE content ~ '\b(python|java|rust)\b'
```

**Best For:** Search, validation, format matching, text extraction

---

### 7. Geospatial Filtering

**Use Case:** Location-based queries

```python
# Exact location
filter_obj = FilterBuilder.equals("metadata.location", "San Francisco")

# Region list
filter_obj = MetadataFilter(
    "metadata.region", 
    FilterOperator.IN, 
    ["US-West", "US-East", "EU-Central"]
)

# For advanced geospatial (requires PostGIS):
# - Distance queries: ST_DWithin(location, point, radius)
# - Polygon containment: ST_Contains(polygon, point)
# - Nearest neighbor: ORDER BY location <-> point
```

**Best For:** Store locations, service areas, user regions, delivery zones

---

### 8. Time-based Filtering

**Use Case:** Temporal queries and recency

```python
# Last 24 hours
filter_obj = FilterBuilder.time_window("created_at", hours=24)

# Last 7 days
filter_obj = FilterBuilder.recent("created_at", days=7)

# Specific date range
from datetime import datetime
filter_obj = FilterBuilder.between(
    "created_at",
    datetime(2026, 1, 1),
    datetime(2026, 1, 31)
)

# Before a date
filter_obj = FilterBuilder.less_than("updated_at", datetime(2025, 12, 31))

# After a date
filter_obj = FilterBuilder.greater_than("created_at", datetime(2026, 1, 1))
```

**Common Patterns:**
```python
# Today
filter_obj = FilterBuilder.time_window("created_at", hours=24)

# This week
filter_obj = FilterBuilder.recent("created_at", days=7)

# This month
filter_obj = FilterBuilder.recent("created_at", days=30)

# Yesterday
yesterday = datetime.now() - timedelta(days=1)
filter_obj = FilterBuilder.between(
    "created_at",
    yesterday.replace(hour=0, minute=0),
    yesterday.replace(hour=23, minute=59)
)
```

**Best For:** "Recent changes", "today's updates", audit logs, time series

---

### 9. Statistical Filtering

**Use Case:** Dynamic thresholds based on data distribution

```python
# Top 10% by importance (requires two-step query)
# Step 1: Get threshold
SELECT percentile_cont(0.9) WITHIN GROUP (ORDER BY importance_score) 
FROM knowledge_base;

# Step 2: Filter
threshold = 0.85  # Result from step 1
filter_obj = FilterBuilder.greater_than("importance_score", threshold)

# Above average
SELECT AVG(importance_score) FROM knowledge_base;
filter_obj = FilterBuilder.greater_than("importance_score", avg_score)

# Outlier detection (outside 2 std deviations)
# mean ± 2*stddev
filter_group = FilterGroup(operator=LogicalOperator.OR)
filter_group.add_filter(FilterBuilder.less_than("score", mean - 2*stddev))
filter_group.add_filter(FilterBuilder.greater_than("score", mean + 2*stddev))
```

**Implementation Pattern:**
```python
def get_top_percentile_items(percentile: float = 0.9):
    # Calculate threshold
    with db_config.get_cursor() as cursor:
        cursor.execute("""
            SELECT percentile_cont(%s) 
            WITHIN GROUP (ORDER BY importance_score)
            FROM knowledge_base
        """, (percentile,))
        threshold = cursor.fetchone()[0]
    
    # Filter using threshold
    filter_obj = FilterBuilder.greater_than("importance_score", threshold)
    return search_with_filters(filters=filter_obj)
```

**Best For:** Adaptive thresholds, anomaly detection, quality scoring

---

### 10. Tag Hierarchy Filtering

**Use Case:** Taxonomies, skill trees, nested categories

```python
# Tag hierarchy with dot notation
backend_tags = [
    "backend",
    "backend.api",
    "backend.database",
    "backend.microservices",
    "backend.api.rest",
    "backend.api.graphql"
]

# Find all backend-related items
filter_obj = MetadataFilter("tags", FilterOperator.ANY_OF, backend_tags)

# Specific subtree
api_tags = [t for t in backend_tags if t.startswith("backend.api")]
filter_obj = MetadataFilter("tags", FilterOperator.ANY_OF, api_tags)

# Exclude deprecated items
filter_group = FilterGroup(operator=LogicalOperator.AND)
filter_group.add_filter(
    MetadataFilter("tags", FilterOperator.ANY_OF, backend_tags)
)
filter_group.add_filter(
    MetadataFilter("tags", FilterOperator.NONE_OF, ["deprecated", "archived"])
)

# Skill combination: ANY language + ALL backend tags
filter_group = FilterGroup(operator=LogicalOperator.AND)
filter_group.add_filter(
    MetadataFilter("tags", FilterOperator.ANY_OF, ["python", "javascript", "rust"])
)
filter_group.add_filter(
    MetadataFilter("tags", FilterOperator.ALL_OF, ["api", "backend"])
)
```

**Tag Hierarchy Design:**
```
root
├── backend
│   ├── api
│   │   ├── rest
│   │   └── graphql
│   ├── database
│   │   ├── sql
│   │   └── nosql
│   └── microservices
├── frontend
│   ├── web
│   └── mobile
└── devops
    ├── ci-cd
    └── monitoring
```

**Best For:** Skills, categories, product taxonomies, org hierarchies

---

## 🚀 Quick Start

### Basic Usage

```python
from src.services.unified_hybrid_search import UnifiedHybridSearch
from src.services.metadata_filter import FilterBuilder

# Initialize search
search = UnifiedHybridSearch()

# 1. Simple category filter
results = search.search_by_category(
    query="database design",
    user_id="user_001",
    category="knowledge",
    min_importance=0.7
)

# 2. Time window
results = search.search_by_time_window(
    query="what happened today?",
    user_id="user_001",
    hours=24
)

# 3. Tag search
results = search.search_by_tags(
    query="python tips",
    user_id="user_001",
    tags=["python", "coding"],
    match_all=False
)

# 4. Custom metadata
results = search.search_with_metadata(
    query="project updates",
    user_id="user_001",
    metadata_conditions={
        "metadata.department": "engineering",
        "metadata.project": "api-redesign",
        "importance_score": {"operator": "gte", "value": 0.7}
    }
)
```

### Advanced Usage

```python
from src.services.metadata_filter import (
    FilterGroup, 
    FilterBuilder, 
    LogicalOperator
)

# Complex filter: Recent important engineering docs
main_filter = FilterGroup(operator=LogicalOperator.AND)
main_filter.add_filter(FilterBuilder.equals("category", "knowledge"))
main_filter.add_filter(FilterBuilder.recent("created_at", days=7))
main_filter.add_filter(FilterBuilder.equals("metadata.department", "engineering"))

# Add OR subgroup for urgency
or_group = FilterGroup(operator=LogicalOperator.OR)
or_group.add_filter(FilterBuilder.greater_than("importance_score", 0.8))
or_group.add_filter(FilterBuilder.has_tags("tags", ["critical", "urgent"]))

main_filter.add_filter(or_group)

# Execute search with filters
results = search.hybrid_search_with_filters(
    query="api security updates",
    user_id="user_001",
    filters=main_filter,
    limit=10
)

# Access results
for item in results["combined"]:
    print(f"Title: {item['title']}")
    print(f"Score: {item['hybrid_score']:.3f}")
    print(f"Category: {item['category']}")
    print()
```

---

## 📊 Database Setup

### 1. Run Migration

```bash
psql -U postgres -d semantic_memory < database/add_metadata_support.sql
```

This adds:
- JSONB metadata columns
- Tag array columns with GIN indexes
- Importance score columns
- Timestamp indexes
- Helper functions

### 2. Verify Setup

```sql
-- Check columns
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('knowledge_base', 'episodes')
  AND column_name IN ('metadata', 'tags', 'importance_score')
ORDER BY table_name, column_name;

-- Check indexes
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename IN ('knowledge_base', 'episodes')
ORDER BY tablename, indexname;
```

---

## 🎨 Real-World Examples

### Example 1: Personal Assistant Query

**User:** "Show me my important Python work from last month"

```python
filter_group = FilterGroup(operator=LogicalOperator.AND)
filter_group.add_filter(FilterBuilder.recent("created_at", days=30))
filter_group.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
filter_group.add_filter(FilterBuilder.has_tags("tags", ["python"]))

results = search.hybrid_search_with_filters(
    query="python work",
    user_id="user_001",
    filters=filter_group
)
```

### Example 2: Document Review Queue

**User:** "Show engineering docs not yet reviewed"

```python
filter_group = FilterGroup(operator=LogicalOperator.AND)
filter_group.add_filter(FilterBuilder.equals("metadata.department", "engineering"))
filter_group.add_filter(FilterBuilder.not_equals("metadata.review_status", "approved"))
filter_group.add_filter(FilterBuilder.equals("category", "knowledge"))

results = search.hybrid_search_with_filters(
    query="",  # No semantic search, pure filtering
    user_id="user_001",
    filters=filter_group,
    limit=50
)
```

### Example 3: Crisis Management

**User:** "Critical issues from this week"

```python
filter_group = FilterGroup(operator=LogicalOperator.AND)
filter_group.add_filter(FilterBuilder.time_window("created_at", hours=168))

# Critical if: priority=critical OR tagged urgent/blocker
urgency_group = FilterGroup(operator=LogicalOperator.OR)
urgency_group.add_filter(FilterBuilder.equals("metadata.priority", "critical"))
urgency_group.add_filter(FilterBuilder.has_tags("tags", ["urgent", "blocker"]))

filter_group.add_filter(urgency_group)

results = search.hybrid_search_with_filters(
    query="critical issues",
    user_id="user_001",
    filters=filter_group
)
```

### Example 4: Multi-tenant SaaS

**Use Case:** Ensure data isolation between tenants

```python
# Every query must include tenant filter
def search_for_tenant(tenant_id: str, query: str, **kwargs):
    base_filter = FilterBuilder.equals("metadata.tenant_id", tenant_id)
    
    # Combine with any additional filters
    if 'filters' in kwargs:
        combined = FilterGroup(operator=LogicalOperator.AND)
        combined.add_filter(base_filter)
        combined.add_filter(kwargs['filters'])
        kwargs['filters'] = combined
    else:
        kwargs['filters'] = base_filter
    
    return search.hybrid_search_with_filters(query=query, **kwargs)
```

---

## ⚡ Performance Optimization

### 1. Index Strategy

```sql
-- Add indexes for frequently filtered fields
CREATE INDEX idx_kb_dept ON knowledge_base((metadata->>'department'));
CREATE INDEX idx_kb_project ON knowledge_base((metadata->>'project'));
CREATE INDEX idx_kb_user_importance ON knowledge_base(user_id, importance_score DESC);

-- Partial indexes for common filters
CREATE INDEX idx_kb_high_importance 
ON knowledge_base(importance_score) 
WHERE importance_score > 0.7;

CREATE INDEX idx_kb_recent 
ON knowledge_base(created_at) 
WHERE created_at > NOW() - INTERVAL '30 days';
```

### 2. Query Optimization

```python
# ✅ GOOD: Filter before vector search
filter_obj = FilterBuilder.equals("category", "knowledge")
results = search.hybrid_search_with_filters(
    query="python",
    user_id="user_001",
    filters=filter_obj,  # Reduces search space
    limit=10
)

# ❌ BAD: Vector search then filter
all_results = search.hybrid_search(query="python", limit=1000)
filtered = [r for r in all_results if r['category'] == 'knowledge']
```

### 3. Monitor Performance

```sql
-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM knowledge_base
WHERE metadata->>'department' = 'engineering'
  AND importance_score > 0.7
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY importance_score DESC
LIMIT 10;

-- Look for:
-- - Index Scan (good) vs Seq Scan (bad)
-- - Execution time < 10ms for indexed queries
-- - Rows filtered early in plan
```

---

## 🔧 Troubleshooting

### Issue 1: Slow Queries

**Symptom:** Filtering takes > 100ms

**Solutions:**
1. Add indexes on filtered fields
2. Use EXPLAIN ANALYZE to identify bottlenecks
3. Reduce result limit
4. Cache frequent filter combinations in Redis

### Issue 2: Empty Results

**Symptom:** Filters return no results unexpectedly

**Debug:**
```python
# Test filters individually
filter1 = FilterBuilder.equals("category", "knowledge")
filter2 = FilterBuilder.greater_than("importance_score", 0.7)

results1 = search.hybrid_search_with_filters(filters=filter1)
results2 = search.hybrid_search_with_filters(filters=filter2)

print(f"Category filter: {len(results1)} results")
print(f"Importance filter: {len(results2)} results")
```

### Issue 3: Type Mismatches

**Symptom:** JSONB field comparison fails

**Solution:** Ensure type casting
```sql
-- Wrong: treats as string
WHERE metadata->>'priority' > 5

-- Correct: cast to numeric
WHERE (metadata->>'priority')::int > 5
```

---

## 📚 Additional Resources

- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [GIN Index Performance](https://www.postgresql.org/docs/current/gin.html)
- [Array Operators Reference](https://www.postgresql.org/docs/current/functions-array.html)
- [Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)

---

## 🎉 Summary

**10 Techniques Implemented:**
1. ✅ Exact Match Filtering
2. ✅ Range Filtering  
3. ✅ Multi-value Filtering
4. ✅ Hierarchical Filtering
5. ✅ Composite Filtering
6. ✅ Pattern Matching
7. ✅ Geospatial Filtering
8. ✅ Time-based Filtering
9. ✅ Statistical Filtering
10. ✅ Tag Hierarchy Filtering

**Benefits:**
- 🎯 Precision: Get exactly what you need
- ⚡ Performance: 10-100x faster with indexes
- 🔒 Security: Row-level access control
- 🎨 Flexibility: Combine any filters with boolean logic
- 📊 Insight: Filter statistics and analytics

**Next Steps:**
1. Run database migration
2. Try demo: `python3 demo_metadata_filtering.py`
3. Integrate filters into your workflows
4. Monitor performance and add indexes as needed
5. Customize metadata schema for your domain
