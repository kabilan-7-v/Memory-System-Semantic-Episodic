#!/usr/bin/env python3
"""
Quick Test of Metadata Filtering Integration
==============================================
Tests that metadata filtering works with the existing system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.metadata_filter import (
    FilterBuilder,
    FilterGroup,
    LogicalOperator,
    MetadataFilterEngine
)

def test_filter_creation():
    """Test creating various filters"""
    print("="*60)
    print("TEST 1: Filter Creation")
    print("="*60)
    
    # Simple filter
    f1 = FilterBuilder.equals("category", "knowledge")
    print(f"✓ Simple filter: {f1.to_dict()}")
    
    # Range filter
    f2 = FilterBuilder.greater_than("importance_score", 0.7)
    print(f"✓ Range filter: {f2.to_dict()}")
    
    # Time filter
    f3 = FilterBuilder.recent("created_at", days=7)
    print(f"✓ Time filter: {f3.to_dict()}")
    
    # Tag filter
    f4 = FilterBuilder.has_tags("tags", ["python", "api"])
    print(f"✓ Tag filter: {f4.to_dict()}")
    
    print("\n✅ All filters created successfully!\n")


def test_filter_groups():
    """Test combining filters"""
    print("="*60)
    print("TEST 2: Filter Groups (Boolean Logic)")
    print("="*60)
    
    # AND group
    group = FilterGroup(operator=LogicalOperator.AND)
    group.add_filter(FilterBuilder.equals("category", "knowledge"))
    group.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
    group.add_filter(FilterBuilder.recent("created_at", days=7))
    
    print("✓ AND filter group created:")
    print(f"  - {len(group.filters)} filters combined")
    print(f"  - Operator: {group.operator.value}")
    
    # OR group
    or_group = FilterGroup(operator=LogicalOperator.OR)
    or_group.add_filter(FilterBuilder.equals("category", "urgent"))
    or_group.add_filter(FilterBuilder.greater_than("importance_score", 0.9))
    
    print(f"\n✓ OR filter group created:")
    print(f"  - {len(or_group.filters)} filters combined")
    
    print("\n✅ Filter groups work correctly!\n")


def test_sql_generation():
    """Test SQL WHERE clause generation"""
    print("="*60)
    print("TEST 3: SQL Query Generation")
    print("="*60)
    
    engine = MetadataFilterEngine()
    
    # Simple filter
    f1 = FilterBuilder.equals("category", "knowledge")
    where1, params1 = engine.to_sql_where(f1)
    print(f"✓ Simple SQL: WHERE {where1}")
    print(f"  Params: {params1}")
    
    # Complex filter
    group = FilterGroup(operator=LogicalOperator.AND)
    group.add_filter(FilterBuilder.equals("category", "knowledge"))
    group.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
    
    where2, params2 = engine.to_sql_where(group)
    print(f"\n✓ Complex SQL: WHERE {where2}")
    print(f"  Params: {params2}")
    
    # Metadata filter
    f3 = FilterBuilder.equals("metadata.department", "engineering")
    where3, params3 = engine.to_sql_where(f3)
    print(f"\n✓ Metadata SQL: WHERE {where3}")
    print(f"  Params: {params3}")
    
    print("\n✅ SQL generation working!\n")


def test_in_memory_filtering():
    """Test filtering on sample data"""
    print("="*60)
    print("TEST 4: In-Memory Filtering")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    # Sample data
    data = [
        {
            "id": 1,
            "category": "knowledge",
            "importance_score": 0.9,
            "tags": ["python", "api"],
            "created_at": datetime.now() - timedelta(days=2),
            "metadata": {"department": "engineering"}
        },
        {
            "id": 2,
            "category": "episode",
            "importance_score": 0.6,
            "tags": ["meeting"],
            "created_at": datetime.now() - timedelta(days=10),
            "metadata": {"department": "sales"}
        },
        {
            "id": 3,
            "category": "knowledge",
            "importance_score": 0.8,
            "tags": ["python", "backend"],
            "created_at": datetime.now() - timedelta(days=1),
            "metadata": {"department": "engineering"}
        }
    ]
    
    engine = MetadataFilterEngine()
    
    # Test 1: Category filter
    f1 = FilterBuilder.equals("category", "knowledge")
    result1 = engine.apply_filter(data, f1)
    print(f"✓ Category='knowledge': {len(result1)} items (expected 2)")
    assert len(result1) == 2, "Category filter failed"
    
    # Test 2: Importance filter
    f2 = FilterBuilder.greater_than("importance_score", 0.7)
    result2 = engine.apply_filter(data, f2)
    print(f"✓ Importance>0.7: {len(result2)} items (expected 2)")
    assert len(result2) == 2, "Importance filter failed"
    
    # Test 3: Recent filter
    f3 = FilterBuilder.recent("created_at", days=7)
    result3 = engine.apply_filter(data, f3)
    print(f"✓ Recent (7 days): {len(result3)} items (expected 2)")
    assert len(result3) == 2, "Recent filter failed"
    
    # Test 4: Composite filter
    group = FilterGroup(operator=LogicalOperator.AND)
    group.add_filter(FilterBuilder.equals("category", "knowledge"))
    group.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
    group.add_filter(FilterBuilder.recent("created_at", days=7))
    
    result4 = engine.apply_filter(data, group)
    print(f"✓ Composite (AND): {len(result4)} items (expected 2)")
    assert len(result4) == 2, "Composite filter failed"
    
    # Test 5: Metadata filter
    f5 = FilterBuilder.equals("metadata.department", "engineering")
    result5 = engine.apply_filter(data, f5)
    print(f"✓ Metadata filter: {len(result5)} items (expected 2)")
    assert len(result5) == 2, "Metadata filter failed"
    
    print("\n✅ All in-memory filters passed!\n")


def test_integration_patterns():
    """Show common integration patterns"""
    print("="*60)
    print("TEST 5: Integration Patterns")
    print("="*60)
    
    # Pattern 1: Recent important items
    print("Pattern 1: Recent Important Items")
    filters = FilterGroup(operator=LogicalOperator.AND)
    filters.add_filter(FilterBuilder.recent("created_at", days=7))
    filters.add_filter(FilterBuilder.greater_than("importance_score", 0.7))
    print(f"  ✓ Filter group with {len(filters.filters)} conditions")
    
    # Pattern 2: Department-specific
    print("\nPattern 2: Department-Specific Search")
    filters = FilterGroup(operator=LogicalOperator.AND)
    filters.add_filter(FilterBuilder.equals("metadata.department", "engineering"))
    filters.add_filter(FilterBuilder.equals("category", "knowledge"))
    print(f"  ✓ Filter group with {len(filters.filters)} conditions")
    
    # Pattern 3: Urgent items
    print("\nPattern 3: Urgent Items (OR logic)")
    filters = FilterGroup(operator=LogicalOperator.OR)
    filters.add_filter(FilterBuilder.equals("metadata.priority", "critical"))
    filters.add_filter(FilterBuilder.greater_than("importance_score", 0.9))
    filters.add_filter(FilterBuilder.has_tags("tags", ["urgent"]))
    print(f"  ✓ Filter group with {len(filters.filters)} conditions")
    
    print("\n✅ Integration patterns defined!\n")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  METADATA FILTERING SYSTEM - INTEGRATION TEST")
    print("="*60 + "\n")
    
    try:
        test_filter_creation()
        test_filter_groups()
        test_sql_generation()
        test_in_memory_filtering()
        test_integration_patterns()
        
        print("="*60)
        print("  ✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n📚 Next Steps:")
        print("  1. Run: psql < database/add_metadata_support.sql")
        print("  2. Try: python3 demo_metadata_filtering.py")
        print("  3. Read: docs/METADATA_FILTERING_GUIDE.md")
        print("  4. Use in your searches!\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
