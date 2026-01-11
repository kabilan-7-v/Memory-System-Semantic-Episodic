#!/usr/bin/env python3
"""
Metadata Filtering Demo Application
=====================================
Demonstrates all 10 metadata filtering techniques in action

Run: python3 demo_metadata_filtering.py
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.metadata_filter import (
    MetadataFilterEngine,
    MetadataFilter,
    FilterGroup,
    FilterBuilder,
    FilterOperator,
    LogicalOperator
)
from src.services.unified_hybrid_search import UnifiedHybridSearch
from src.repositories.knowledge_repository import KnowledgeRepository
from src.services.embedding_service import EmbeddingService


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_results(results: List[Dict[str, Any]], max_display: int = 3):
    """Print search results in a formatted way"""
    if not results:
        print("  ⚠️  No results found\n")
        return
    
    print(f"  ✓ Found {len(results)} results:\n")
    for i, result in enumerate(results[:max_display], 1):
        print(f"  [{i}] {result.get('title') or result.get('content', '')[:80]}")
        if 'category' in result:
            print(f"      Category: {result['category']}")
        if 'importance_score' in result:
            print(f"      Importance: {result['importance_score']:.2f}")
        if 'created_at' in result:
            print(f"      Created: {result['created_at']}")
        if 'tags' in result and result['tags']:
            print(f"      Tags: {', '.join(result['tags'][:5])}")
        if 'hybrid_score' in result:
            print(f"      Relevance: {result['hybrid_score']:.3f}")
        print()
    
    if len(results) > max_display:
        print(f"  ... and {len(results) - max_display} more results\n")


def demo_1_exact_match_filtering():
    """Technique 1: Exact Match Filtering"""
    print_section("TECHNIQUE 1: Exact Match Filtering")
    print("  Use case: Find items with specific values")
    print("  Example: All knowledge items in 'engineering' category\n")
    
    # Create filter
    filter_obj = FilterBuilder.equals("category", "knowledge")
    
    print(f"  Filter: category == 'knowledge'")
    print(f"  SQL: {MetadataFilterEngine().to_sql_where(filter_obj)[0]}")
    
    # In production, you would query the database
    print("\n  ✓ This filter ensures only exact matches are returned")


def demo_2_range_filtering():
    """Technique 2: Range Filtering"""
    print_section("TECHNIQUE 2: Range Filtering")
    print("  Use case: Filter by numeric or date ranges")
    print("  Example: High-importance items (>= 0.7)\n")
    
    # Create filter
    filter_obj = FilterBuilder.greater_than("importance_score", 0.7)
    
    print(f"  Filter: importance_score > 0.7")
    
    # Also show BETWEEN
    filter_between = FilterBuilder.between("importance_score", 0.5, 0.9)
    print(f"  Filter: 0.5 <= importance_score <= 0.9")
    
    print("\n  ✓ Range filters are indexed for fast queries on sorted data")


def demo_3_multi_value_filtering():
    """Technique 3: Multi-value Filtering"""
    print_section("TECHNIQUE 3: Multi-value Filtering (Array Operations)")
    print("  Use case: Filter by tags, categories, or any array field")
    print("  Example: Items with ANY of [python, api, backend] tags\n")
    
    tags_to_find = ["python", "api", "backend"]
    
    # ANY_OF: Item has at least one of these tags
    filter_any = MetadataFilter("tags", FilterOperator.ANY_OF, tags_to_find)
    print(f"  Filter ANY_OF: tags contains any of {tags_to_find}")
    print(f"  SQL: tags && ARRAY{tags_to_find}")
    
    # ALL_OF: Item has all these tags
    filter_all = MetadataFilter("tags", FilterOperator.ALL_OF, ["python", "backend"])
    print(f"\n  Filter ALL_OF: tags contains all of ['python', 'backend']")
    print(f"  SQL: tags @> ARRAY['python', 'backend']")
    
    # NONE_OF: Item has none of these tags
    filter_none = MetadataFilter("tags", FilterOperator.NONE_OF, ["deprecated"])
    print(f"\n  Filter NONE_OF: tags contains none of ['deprecated']")
    
    print("\n  ✓ Array operators use GIN indexes for fast membership tests")


def demo_4_hierarchical_filtering():
    """Technique 4: Hierarchical Filtering (Nested JSON/JSONB)"""
    print_section("TECHNIQUE 4: Hierarchical Filtering (Nested JSONB)")
    print("  Use case: Filter by nested metadata fields")
    print("  Example: metadata.department == 'engineering'\n")
    
    # Create filter for nested field
    filter_obj = FilterBuilder.equals("metadata.department", "engineering")
    print(f"  Filter: metadata.department == 'engineering'")
    print(f"  Access nested fields with dot notation: field.subfield.value")
    
    # More complex nested example
    filter_nested = FilterBuilder.equals("metadata.settings.priority", "high")
    print(f"\n  Filter: metadata.settings.priority == 'high'")
    
    print("\n  ✓ JSONB GIN indexes enable fast nested field queries")
    print("  ✓ Supports arbitrary depth: metadata.a.b.c.d")


def demo_5_composite_filtering():
    """Technique 5: Composite Filtering (AND/OR/NOT)"""
    print_section("TECHNIQUE 5: Composite Filtering (Boolean Logic)")
    print("  Use case: Combine multiple conditions")
    print("  Example: Engineering docs with high importance created recently\n")
    
    # Create composite filter with AND
    filter_group = FilterGroup(operator=LogicalOperator.AND)
    filter_group.add_filter(FilterBuilder.equals("category", "knowledge"))
    filter_group.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
    filter_group.add_filter(FilterBuilder.recent("created_at", days=7))
    
    print("  Combined Filter (AND):")
    print("    - category == 'knowledge'")
    print("    - importance_score > 0.7")
    print("    - created_at >= (now - 7 days)")
    
    # Show OR example
    print("\n  OR Example:")
    or_group = FilterGroup(operator=LogicalOperator.OR)
    or_group.add_filter(FilterBuilder.equals("category", "urgent"))
    or_group.add_filter(FilterBuilder.greater_than("importance_score", 0.9))
    print("    - category == 'urgent' OR importance_score > 0.9")
    
    # Nested groups
    print("\n  Nested Example:")
    print("    - (category=='knowledge' AND importance>0.7) OR (tags contains 'urgent')")
    
    print("\n  ✓ Supports arbitrary nesting for complex business logic")


def demo_6_pattern_matching():
    """Technique 6: Pattern Matching (Regex, Wildcards)"""
    print_section("TECHNIQUE 6: Pattern Matching")
    print("  Use case: Flexible text matching")
    print("  Example: Find items with 'API' in title\n")
    
    # CONTAINS
    filter_contains = FilterBuilder.contains("title", "API", case_sensitive=False)
    print("  CONTAINS: title contains 'API' (case-insensitive)")
    
    # STARTS_WITH
    filter_starts = MetadataFilter("title", FilterOperator.STARTS_WITH, "How to")
    print("  STARTS_WITH: title starts with 'How to'")
    
    # REGEX
    filter_regex = MetadataFilter("content", FilterOperator.REGEX, r"\b(python|java|rust)\b")
    print("  REGEX: content matches pattern for programming languages")
    
    print("\n  ✓ Pattern matching uses PostgreSQL's text search capabilities")
    print("  ✓ REGEX uses ~ operator, LIKE for wildcards")


def demo_7_geospatial_filtering():
    """Technique 7: Geospatial Filtering"""
    print_section("TECHNIQUE 7: Geospatial Filtering")
    print("  Use case: Location-based queries")
    print("  Example: Find items related to specific locations\n")
    
    # Location stored in metadata
    filter_location = FilterBuilder.equals("metadata.location", "San Francisco")
    print("  Filter: metadata.location == 'San Francisco'")
    
    # Region filtering
    regions = ["US-West", "US-East"]
    filter_region = MetadataFilter("metadata.region", FilterOperator.IN, regions)
    print(f"  Filter: metadata.region IN {regions}")
    
    print("\n  Note: For true geospatial queries (radius, polygon), use PostGIS")
    print("  ✓ Basic location filtering works with standard JSONB fields")


def demo_8_time_based_filtering():
    """Technique 8: Time-based Filtering"""
    print_section("TECHNIQUE 8: Time-based Filtering")
    print("  Use case: Temporal queries and recency")
    print("  Example: Items from last 24 hours, specific date ranges\n")
    
    # Last 24 hours
    filter_recent = FilterBuilder.time_window("created_at", hours=24)
    print("  Filter: created_at >= (now - 24 hours)")
    
    # Last 7 days
    filter_week = FilterBuilder.recent("created_at", days=7)
    print("  Filter: created_at >= (now - 7 days)")
    
    # Specific date range
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 1, 31)
    filter_range = FilterBuilder.between("created_at", start_date, end_date)
    print(f"  Filter: created_at BETWEEN {start_date.date()} AND {end_date.date()}")
    
    # Before a date
    filter_before = FilterBuilder.less_than("updated_at", datetime(2025, 12, 31))
    print(f"  Filter: updated_at < 2025-12-31")
    
    print("\n  ✓ Timestamp indexes enable efficient temporal queries")
    print("  ✓ Perfect for 'recent changes', 'today', 'this week' queries")


def demo_9_statistical_filtering():
    """Technique 9: Statistical Filtering"""
    print_section("TECHNIQUE 9: Statistical Filtering")
    print("  Use case: Percentile-based, threshold filtering")
    print("  Example: Top 10% most important items\n")
    
    # Top percentile
    print("  Filter: importance_score >= (90th percentile)")
    print("  Implementation: Calculate threshold, then filter")
    print("    1. SELECT percentile_cont(0.9) WITHIN GROUP (ORDER BY importance_score)")
    print("    2. WHERE importance_score >= threshold")
    
    # Standard deviation filtering
    print("\n  Filter: Items with above-average importance")
    print("  Implementation: importance_score > AVG(importance_score)")
    
    # Composite statistical
    print("\n  Combined: Top 20% importance AND above median recency")
    
    print("\n  ✓ Useful for dynamic thresholds that adapt to your data")
    print("  ✓ Can be combined with other filters")


def demo_10_tag_hierarchy_filtering():
    """Technique 10: Tag Hierarchy Filtering"""
    print_section("TECHNIQUE 10: Tag-based Filtering with Hierarchies")
    print("  Use case: Taxonomies, skill trees, categorization")
    print("  Example: Find all 'backend' related skills\n")
    
    # Tag hierarchy example
    backend_tags = [
        "backend",
        "backend.api",
        "backend.database",
        "backend.microservices"
    ]
    
    filter_backend = MetadataFilter("tags", FilterOperator.ANY_OF, backend_tags)
    print(f"  Filter: tags contains any of backend hierarchy")
    print(f"  Tags: {backend_tags}")
    
    # Exclude certain tags
    filter_exclude = MetadataFilter("tags", FilterOperator.NONE_OF, ["deprecated", "archived"])
    print(f"\n  Exclude: tags contains none of ['deprecated', 'archived']")
    
    # Specific skill combinations
    filter_skills = FilterGroup(operator=LogicalOperator.AND)
    filter_skills.add_filter(
        MetadataFilter("tags", FilterOperator.ANY_OF, ["python", "javascript", "rust"])
    )
    filter_skills.add_filter(
        MetadataFilter("tags", FilterOperator.ALL_OF, ["api", "backend"])
    )
    print("\n  Combined: Has ANY programming language AND has ALL ['api', 'backend']")
    
    print("\n  ✓ Tag hierarchies enable flexible categorization")
    print("  ✓ Use dot notation for nested categories: parent.child.grandchild")


def demo_real_world_examples():
    """Real-world filtering examples"""
    print_section("REAL-WORLD EXAMPLES")
    
    print("Example 1: 'Find my recent important Python work'")
    print("-" * 60)
    filter1 = FilterGroup(operator=LogicalOperator.AND)
    filter1.add_filter(FilterBuilder.recent("created_at", days=30))
    filter1.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
    filter1.add_filter(FilterBuilder.has_tags("tags", ["python"]))
    print("  Filters:")
    print("    - created_at >= (now - 30 days)")
    print("    - importance_score > 0.7")
    print("    - tags contains 'python'")
    print("  Use: hybrid_search.search_with_metadata(...)")
    
    print("\n\nExample 2: 'Show engineering docs not yet reviewed'")
    print("-" * 60)
    filter2 = FilterGroup(operator=LogicalOperator.AND)
    filter2.add_filter(FilterBuilder.equals("metadata.department", "engineering"))
    filter2.add_filter(FilterBuilder.not_equals("metadata.review_status", "approved"))
    filter2.add_filter(FilterBuilder.equals("category", "knowledge"))
    print("  Filters:")
    print("    - metadata.department == 'engineering'")
    print("    - metadata.review_status != 'approved'")
    print("    - category == 'knowledge'")
    
    print("\n\nExample 3: 'Critical issues from this week'")
    print("-" * 60)
    filter3 = FilterGroup(operator=LogicalOperator.AND)
    filter3.add_filter(FilterBuilder.time_window("created_at", hours=168))  # 7 days
    filter3.add_filter(
        FilterGroup(operator=LogicalOperator.OR)
        .add_filter(FilterBuilder.equals("metadata.priority", "critical"))
        .add_filter(FilterBuilder.has_tags("tags", ["urgent", "blocker"]))
    )
    print("  Filters:")
    print("    - created_at >= (now - 7 days)")
    print("    - (metadata.priority == 'critical' OR tags contains ['urgent', 'blocker'])")
    
    print("\n\nExample 4: 'Find similar verified documents'")
    print("-" * 60)
    filter4 = FilterGroup(operator=LogicalOperator.AND)
    filter4.add_filter(FilterBuilder.equals("metadata.verified", True))
    filter4.add_filter(FilterBuilder.not_equals("metadata.confidential", True))
    filter4.add_filter(FilterBuilder.greater_than("importance_score", 0.5))
    print("  Filters:")
    print("    - metadata.verified == true")
    print("    - metadata.confidential != true")
    print("    - importance_score > 0.5")
    print("  Combined with semantic search for relevance ranking")


def demo_performance_tips():
    """Performance optimization tips"""
    print_section("PERFORMANCE OPTIMIZATION TIPS")
    
    tips = [
        ("1. Pre-filter before embedding search", 
         "Reduce vector search space by filtering first"),
        
        ("2. Use indexed fields in WHERE clause",
         "category, importance_score, created_at, tags have indexes"),
        
        ("3. Limit metadata nesting depth",
         "Shallow JSONB queries are faster than deep nesting"),
        
        ("4. Use appropriate operators",
         "= is faster than LIKE, && faster than multiple ORs"),
        
        ("5. Add indexes for custom filters",
         "CREATE INDEX ON table(jsonb_field->>'key') for frequent queries"),
        
        ("6. Combine filters efficiently",
         "Put most restrictive filters first in AND conditions"),
        
        ("7. Use metadata stats",
         "Monitor filter selectivity and adjust indexes"),
        
        ("8. Cache filter results in Redis",
         "Store frequently used filter results with TTL"),
        
        ("9. Batch filter operations",
         "Process multiple filters in single query when possible"),
        
        ("10. Monitor query plans",
         "Use EXPLAIN ANALYZE to optimize filter queries")
    ]
    
    for tip, explanation in tips:
        print(f"  {tip}")
        print(f"      → {explanation}\n")


def demo_api_usage():
    """Show API usage patterns"""
    print_section("API USAGE PATTERNS")
    
    code_examples = """
# 1. Simple category filter
from src.services.metadata_filter import FilterBuilder

results = hybrid_search.search_by_category(
    query="database design",
    user_id="user_001",
    category="knowledge",
    min_importance=0.7
)

# 2. Time window search
results = hybrid_search.search_by_time_window(
    query="what did we discuss?",
    user_id="user_001",
    hours=24  # Last 24 hours
)

# 3. Tag-based search
results = hybrid_search.search_by_tags(
    query="python best practices",
    user_id="user_001",
    tags=["python", "coding", "best-practices"],
    match_all=False  # ANY tag matches
)

# 4. Custom metadata filter
results = hybrid_search.search_with_metadata(
    query="project updates",
    user_id="user_001",
    metadata_conditions={
        "metadata.department": "engineering",
        "metadata.project": "api-redesign",
        "importance_score": {"operator": "gte", "value": 0.7}
    }
)

# 5. Complex filter composition
from src.services.metadata_filter import FilterGroup, FilterBuilder, LogicalOperator

# Build complex filter
main_filter = FilterGroup(operator=LogicalOperator.AND)
main_filter.add_filter(FilterBuilder.equals("category", "knowledge"))
main_filter.add_filter(FilterBuilder.recent("created_at", days=7))

# Add OR subgroup
or_group = FilterGroup(operator=LogicalOperator.OR)
or_group.add_filter(FilterBuilder.greater_than("importance_score", 0.8))
or_group.add_filter(FilterBuilder.has_tags("tags", ["critical", "urgent"]))

main_filter.add_filter(or_group)

# Execute search
results = hybrid_search.hybrid_search_with_filters(
    query="urgent api changes",
    user_id="user_001",
    filters=main_filter,
    limit=10
)

# 6. Repository-level filtering (no semantic search)
from src.repositories.knowledge_repository import KnowledgeRepository

repo = KnowledgeRepository()
items = repo.find_by_metadata(
    filters=main_filter,
    user_id="user_001",
    limit=50
)

# 7. Get statistics for filtered data
stats = repo.get_filtered_stats(
    user_id="user_001",
    filters=FilterBuilder.recent("created_at", days=30)
)
print(f"Found {stats['total_count']} items")
print(f"Average importance: {stats['avg_importance']:.2f}")
"""
    
    print(code_examples)


def main():
    """Run all demonstrations"""
    print("\n" + "="*80)
    print(" "*20 + "METADATA FILTERING DEMONSTRATION")
    print("="*80)
    print("\n  This demo showcases 10 advanced metadata filtering techniques")
    print("  for the Interactive Memory System.\n")
    
    # Run all demos
    demo_1_exact_match_filtering()
    demo_2_range_filtering()
    demo_3_multi_value_filtering()
    demo_4_hierarchical_filtering()
    demo_5_composite_filtering()
    demo_6_pattern_matching()
    demo_7_geospatial_filtering()
    demo_8_time_based_filtering()
    demo_9_statistical_filtering()
    demo_10_tag_hierarchy_filtering()
    
    # Real-world examples
    demo_real_world_examples()
    
    # Performance tips
    demo_performance_tips()
    
    # API usage
    demo_api_usage()
    
    # Summary
    print_section("SUMMARY")
    print("  ✓ 10 filtering techniques implemented")
    print("  ✓ SQL and Redis query generation")
    print("  ✓ Integrated with hybrid search")
    print("  ✓ Optimized with proper indexes")
    print("  ✓ Flexible API for all use cases")
    print("\n  Next steps:")
    print("    1. Run: psql < database/add_metadata_support.sql")
    print("    2. Use filters in your searches")
    print("    3. Monitor performance with EXPLAIN ANALYZE")
    print("    4. Add custom metadata fields as needed")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
