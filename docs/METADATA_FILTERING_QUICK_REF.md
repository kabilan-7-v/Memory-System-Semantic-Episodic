# 🔍 Metadata Filtering Quick Reference

## One-Liners

```python
from src.services.metadata_filter import FilterBuilder
from src.services.unified_hybrid_search import UnifiedHybridSearch

search = UnifiedHybridSearch()
```

### Common Filters

```python
# By category
FilterBuilder.equals("category", "knowledge")

# By importance
FilterBuilder.greater_than("importance_score", 0.7)

# Recent (last 7 days)
FilterBuilder.recent("created_at", days=7)

# Last 24 hours
FilterBuilder.time_window("created_at", hours=24)

# By tags (any)
FilterBuilder.has_tags("tags", ["python", "api"])

# Date range
FilterBuilder.between("created_at", start_date, end_date)

# Contains text
FilterBuilder.contains("title", "API", case_sensitive=False)

# Metadata field
FilterBuilder.equals("metadata.department", "engineering")
```

### Combining Filters

```python
from src.services.metadata_filter import FilterGroup, LogicalOperator

# AND (all must match)
filters = FilterGroup(operator=LogicalOperator.AND)
filters.add_filter(FilterBuilder.equals("category", "knowledge"))
filters.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
filters.add_filter(FilterBuilder.recent("created_at", days=7))

# OR (any can match)
filters = FilterGroup(operator=LogicalOperator.OR)
filters.add_filter(FilterBuilder.equals("category", "urgent"))
filters.add_filter(FilterBuilder.has_tags("tags", ["critical"]))
```

### Search Methods

```python
# 1. With custom filters
search.hybrid_search_with_filters(
    query="python tips",
    user_id="user_001",
    filters=filters,
    limit=10
)

# 2. By category
search.search_by_category(
    query="database design",
    user_id="user_001",
    category="knowledge",
    min_importance=0.7
)

# 3. By time window
search.search_by_time_window(
    query="what happened?",
    user_id="user_001",
    hours=24
)

# 4. By tags
search.search_by_tags(
    query="python",
    user_id="user_001",
    tags=["python", "backend"],
    match_all=False  # ANY tag
)

# 5. Important items
search.search_important_items(
    query="updates",
    user_id="user_001",
    min_importance=0.7,
    recent_days=30
)

# 6. Custom metadata
search.search_with_metadata(
    query="project status",
    user_id="user_001",
    metadata_conditions={
        "metadata.department": "engineering",
        "metadata.status": "active"
    }
)
```

## Operators Reference

| Operator | Use | Example |
|----------|-----|---------|
| `EQUALS` | Exact match | `category == 'knowledge'` |
| `NOT_EQUALS` | Not equal | `status != 'archived'` |
| `GREATER_THAN` | Numeric > | `score > 0.7` |
| `GREATER_THAN_OR_EQUAL` | Numeric >= | `score >= 0.7` |
| `LESS_THAN` | Numeric < | `age < 30` |
| `LESS_THAN_OR_EQUAL` | Numeric <= | `age <= 65` |
| `BETWEEN` | Range | `score BETWEEN 0.5 AND 0.9` |
| `CONTAINS` | Substring | `title CONTAINS 'API'` |
| `STARTS_WITH` | Prefix | `title STARTS_WITH 'How'` |
| `ENDS_WITH` | Suffix | `file ENDS_WITH '.pdf'` |
| `REGEX` | Pattern | `content MATCHES r'\d+'` |
| `IN` | Value in list | `status IN ['active', 'pending']` |
| `NOT_IN` | Not in list | `status NOT IN ['archived']` |
| `ANY_OF` | Array overlap | `tags ANY_OF ['python', 'api']` |
| `ALL_OF` | Array contains all | `tags ALL_OF ['python', 'backend']` |
| `NONE_OF` | Array contains none | `tags NONE_OF ['deprecated']` |
| `IS_NULL` | Null check | `field IS NULL` |
| `IS_NOT_NULL` | Not null | `field IS NOT NULL` |

## Real-World Patterns

### Pattern 1: Recent + Important
```python
filters = FilterGroup(operator=LogicalOperator.AND)
filters.add_filter(FilterBuilder.recent("created_at", days=7))
filters.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
```

### Pattern 2: Department + Status
```python
filters = FilterGroup(operator=LogicalOperator.AND)
filters.add_filter(FilterBuilder.equals("metadata.department", "engineering"))
filters.add_filter(FilterBuilder.equals("metadata.status", "active"))
```

### Pattern 3: Urgent Items
```python
filters = FilterGroup(operator=LogicalOperator.OR)
filters.add_filter(FilterBuilder.equals("metadata.priority", "critical"))
filters.add_filter(FilterBuilder.has_tags("tags", ["urgent", "blocker"]))
filters.add_filter(FilterBuilder.greater_than("importance_score", 0.9))
```

### Pattern 4: Multi-tenant Isolation
```python
filters = FilterGroup(operator=LogicalOperator.AND)
filters.add_filter(FilterBuilder.equals("metadata.tenant_id", tenant_id))
filters.add_filter(FilterBuilder.equals("metadata.access_level", "shared"))
```

### Pattern 5: Skills + Recent
```python
filters = FilterGroup(operator=LogicalOperator.AND)
filters.add_filter(
    MetadataFilter("tags", FilterOperator.ANY_OF, ["python", "javascript", "rust"])
)
filters.add_filter(FilterBuilder.recent("created_at", days=90))
filters.add_filter(FilterBuilder.greater_than("importance_score", 0.6))
```

## Performance Tips

### ✅ DO
- Use indexed fields (category, importance_score, created_at, tags)
- Filter before vector search
- Add indexes for frequently filtered metadata fields
- Use partial indexes for common conditions
- Cache filter results in Redis

### ❌ DON'T
- Deep JSONB nesting (>3 levels)
- Filtering after retrieving large result sets
- Regex on unindexed text fields
- Multiple separate OR conditions (use ANY_OF instead)
- Complex LIKE patterns without indexes

## SQL Snippets

```sql
-- Add index for metadata field
CREATE INDEX idx_kb_department 
ON knowledge_base((metadata->>'department'));

-- Partial index for high-importance items
CREATE INDEX idx_kb_important 
ON knowledge_base(importance_score) 
WHERE importance_score > 0.7;

-- Check query performance
EXPLAIN ANALYZE
SELECT * FROM knowledge_base
WHERE metadata->>'department' = 'engineering'
  AND importance_score > 0.7
LIMIT 10;
```

## Common Use Cases

| Use Case | Filters |
|----------|---------|
| Today's updates | `time_window(hours=24)` |
| My recent work | `user_id + recent(days=7)` |
| High-priority items | `importance > 0.8 OR tags contains 'urgent'` |
| Department docs | `metadata.department == 'X'` |
| Approved content | `metadata.status == 'approved'` |
| Multi-language | `tags ANY_OF ['python', 'java', 'rust']` |
| Exclude archived | `tags NONE_OF ['archived', 'deprecated']` |
| This month | `recent(days=30)` |
| Specific project | `metadata.project == 'X'` |
| Verified only | `metadata.verified == true` |

## Cheat Sheet

```python
# Import
from src.services.metadata_filter import FilterBuilder, FilterGroup, LogicalOperator
from src.services.unified_hybrid_search import UnifiedHybridSearch

# Initialize
search = UnifiedHybridSearch()

# Simple filter
filter_obj = FilterBuilder.equals("category", "knowledge")

# Combine filters
filters = FilterGroup(operator=LogicalOperator.AND)
filters.add_filter(FilterBuilder.equals("category", "knowledge"))
filters.add_filter(FilterBuilder.greater_than("importance_score", 0.7))

# Search
results = search.hybrid_search_with_filters(
    query="python tips",
    user_id="user_001",
    filters=filters,
    limit=10
)

# Access results
for item in results["combined"]:
    print(item["title"], item["hybrid_score"])
```

---

**📚 Full Guide:** See [METADATA_FILTERING_GUIDE.md](METADATA_FILTERING_GUIDE.md)

**🎯 Demo:** Run `python3 demo_metadata_filtering.py`

**🔧 Setup:** Run `psql < database/add_metadata_support.sql`
