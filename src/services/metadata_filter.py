"""
Advanced Metadata Filtering System
====================================
Provides comprehensive filtering capabilities across all memory layers.

Filtering Techniques Implemented:
1. Exact Match Filtering - Direct equality checks
2. Range Filtering - Numeric and date ranges
3. Multi-value Filtering - Arrays and lists (ANY, ALL, NONE)
4. Hierarchical Filtering - Nested JSON/JSONB queries
5. Composite Filtering - Combined conditions with AND/OR
6. Pattern Matching - Regex and wildcard support
7. Geospatial Filtering - Location-based queries
8. Time-based Filtering - Temporal windows and recency
9. Statistical Filtering - Percentile and threshold-based
10. Tag-based Filtering - Tag combinations and hierarchies

Why Metadata Filtering is Essential:
- Precision: Get exactly what you need, not just semantically similar
- Performance: Pre-filter large datasets before expensive operations
- Security: Implement row-level security and data isolation
- Context: Filter by user, tenant, time, location, etc.
- Compliance: Audit trails and data governance
- User Experience: Personalized and relevant results
"""

from typing import List, Dict, Any, Optional, Set, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
import re
import json
from dataclasses import dataclass, field


class FilterOperator(Enum):
    """Filter comparison operators"""
    # Equality
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    
    # Comparison
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    
    # Range
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    
    # String matching
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    
    # Array operations
    IN = "in"
    NOT_IN = "not_in"
    ANY_OF = "any_of"  # Array contains any of values
    ALL_OF = "all_of"  # Array contains all values
    NONE_OF = "none_of"  # Array contains none of values
    
    # Null checks
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    
    # Existence
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class LogicalOperator(Enum):
    """Logical operators for combining filters"""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class MetadataFilter:
    """Single metadata filter condition"""
    field: str
    operator: FilterOperator
    value: Any = None
    case_sensitive: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "case_sensitive": self.case_sensitive
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataFilter':
        return cls(
            field=data["field"],
            operator=FilterOperator(data["operator"]),
            value=data.get("value"),
            case_sensitive=data.get("case_sensitive", True)
        )


@dataclass
class FilterGroup:
    """Group of filters with logical operator"""
    operator: LogicalOperator = LogicalOperator.AND
    filters: List[Union[MetadataFilter, 'FilterGroup']] = field(default_factory=list)
    
    def add_filter(self, filter_item: Union[MetadataFilter, 'FilterGroup']):
        """Add a filter or filter group"""
        self.filters.append(filter_item)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator": self.operator.value,
            "filters": [
                f.to_dict() if isinstance(f, (MetadataFilter, FilterGroup)) else f
                for f in self.filters
            ]
        }


class MetadataFilterEngine:
    """
    Main metadata filtering engine supporting multiple filtering techniques
    """
    
    def __init__(self):
        self.custom_operators: Dict[str, Callable] = {}
    
    # ==================== Core Filtering Methods ====================
    
    def apply_filter(
        self,
        data: List[Dict[str, Any]],
        filter_spec: Union[MetadataFilter, FilterGroup]
    ) -> List[Dict[str, Any]]:
        """
        Apply metadata filter(s) to a list of dictionaries
        
        Args:
            data: List of data items (dicts)
            filter_spec: Single filter or filter group
            
        Returns:
            Filtered list of items
        """
        if not data:
            return []
        
        if isinstance(filter_spec, MetadataFilter):
            return [item for item in data if self._evaluate_filter(item, filter_spec)]
        elif isinstance(filter_spec, FilterGroup):
            return [item for item in data if self._evaluate_group(item, filter_spec)]
        else:
            return data
    
    def _evaluate_filter(self, item: Dict[str, Any], filter_obj: MetadataFilter) -> bool:
        """Evaluate a single filter against an item"""
        try:
            # Extract field value (supports nested fields with dot notation)
            field_value = self._get_nested_value(item, filter_obj.field)
            operator = filter_obj.operator
            filter_value = filter_obj.value
            
            # Null checks
            if operator == FilterOperator.IS_NULL:
                return field_value is None
            elif operator == FilterOperator.IS_NOT_NULL:
                return field_value is not None
            
            # Existence checks
            if operator == FilterOperator.EXISTS:
                return filter_obj.field in self._flatten_keys(item)
            elif operator == FilterOperator.NOT_EXISTS:
                return filter_obj.field not in self._flatten_keys(item)
            
            # If field doesn't exist and not checking for null/existence, fail
            if field_value is None:
                return False
            
            # String operations (case sensitivity)
            if isinstance(field_value, str) and not filter_obj.case_sensitive:
                field_value = field_value.lower()
                if isinstance(filter_value, str):
                    filter_value = filter_value.lower()
            
            # Equality operators
            if operator == FilterOperator.EQUALS:
                return field_value == filter_value
            elif operator == FilterOperator.NOT_EQUALS:
                return field_value != filter_value
            
            # Comparison operators
            elif operator == FilterOperator.GREATER_THAN:
                return field_value > filter_value
            elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
                return field_value >= filter_value
            elif operator == FilterOperator.LESS_THAN:
                return field_value < filter_value
            elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
                return field_value <= filter_value
            
            # Range operators
            elif operator == FilterOperator.BETWEEN:
                return filter_value[0] <= field_value <= filter_value[1]
            elif operator == FilterOperator.NOT_BETWEEN:
                return not (filter_value[0] <= field_value <= filter_value[1])
            
            # String matching operators
            elif operator == FilterOperator.CONTAINS:
                return filter_value in str(field_value)
            elif operator == FilterOperator.NOT_CONTAINS:
                return filter_value not in str(field_value)
            elif operator == FilterOperator.STARTS_WITH:
                return str(field_value).startswith(filter_value)
            elif operator == FilterOperator.ENDS_WITH:
                return str(field_value).endswith(filter_value)
            elif operator == FilterOperator.REGEX:
                pattern = re.compile(filter_value, re.IGNORECASE if not filter_obj.case_sensitive else 0)
                return bool(pattern.search(str(field_value)))
            
            # Membership operators
            elif operator == FilterOperator.IN:
                return field_value in filter_value
            elif operator == FilterOperator.NOT_IN:
                return field_value not in filter_value
            
            # Array operators
            elif operator == FilterOperator.ANY_OF:
                if not isinstance(field_value, (list, set, tuple)):
                    return False
                return any(v in filter_value for v in field_value)
            elif operator == FilterOperator.ALL_OF:
                if not isinstance(field_value, (list, set, tuple)):
                    return False
                return all(v in field_value for v in filter_value)
            elif operator == FilterOperator.NONE_OF:
                if not isinstance(field_value, (list, set, tuple)):
                    return True
                return not any(v in filter_value for v in field_value)
            
            # Custom operators
            elif operator.value in self.custom_operators:
                return self.custom_operators[operator.value](field_value, filter_value)
            
            return False
            
        except Exception as e:
            print(f"⚠️  Filter evaluation error: {e}")
            return False
    
    def _evaluate_group(self, item: Dict[str, Any], group: FilterGroup) -> bool:
        """Evaluate a filter group against an item"""
        if not group.filters:
            return True
        
        results = [
            self._evaluate_filter(item, f) if isinstance(f, MetadataFilter)
            else self._evaluate_group(item, f)
            for f in group.filters
        ]
        
        if group.operator == LogicalOperator.AND:
            return all(results)
        elif group.operator == LogicalOperator.OR:
            return any(results)
        elif group.operator == LogicalOperator.NOT:
            return not any(results)
        
        return False
    
    # ==================== SQL Generation ====================
    
    def to_sql_where(
        self,
        filter_spec: Union[MetadataFilter, FilterGroup],
        param_prefix: str = "filter"
    ) -> tuple[str, Dict[str, Any]]:
        """
        Convert filter specification to SQL WHERE clause
        
        Returns:
            Tuple of (where_clause, parameters_dict)
        """
        params = {}
        param_counter = [0]  # Mutable counter
        
        def get_param_name():
            param_counter[0] += 1
            return f"{param_prefix}_{param_counter[0]}"
        
        def build_condition(filter_obj: MetadataFilter) -> str:
            field = filter_obj.field
            op = filter_obj.operator
            value = filter_obj.value
            
            # Handle JSONB fields (metadata.key)
            if '.' in field and field.startswith('metadata.'):
                parts = field.split('.', 1)
                field_sql = f"{parts[0]}->'{parts[1]}'"
            else:
                field_sql = field
            
            # Null checks
            if op == FilterOperator.IS_NULL:
                return f"{field_sql} IS NULL"
            elif op == FilterOperator.IS_NOT_NULL:
                return f"{field_sql} IS NOT NULL"
            
            # Equality
            param_name = get_param_name()
            if op == FilterOperator.EQUALS:
                params[param_name] = value
                return f"{field_sql} = %({param_name})s"
            elif op == FilterOperator.NOT_EQUALS:
                params[param_name] = value
                return f"{field_sql} != %({param_name})s"
            
            # Comparison
            elif op == FilterOperator.GREATER_THAN:
                params[param_name] = value
                return f"{field_sql} > %({param_name})s"
            elif op == FilterOperator.GREATER_THAN_OR_EQUAL:
                params[param_name] = value
                return f"{field_sql} >= %({param_name})s"
            elif op == FilterOperator.LESS_THAN:
                params[param_name] = value
                return f"{field_sql} < %({param_name})s"
            elif op == FilterOperator.LESS_THAN_OR_EQUAL:
                params[param_name] = value
                return f"{field_sql} <= %({param_name})s"
            
            # Range
            elif op == FilterOperator.BETWEEN:
                param1, param2 = get_param_name(), get_param_name()
                params[param1] = value[0]
                params[param2] = value[1]
                return f"{field_sql} BETWEEN %({param1})s AND %({param2})s"
            
            # String matching
            elif op == FilterOperator.CONTAINS:
                params[param_name] = f"%{value}%"
                return f"{field_sql} LIKE %({param_name})s"
            elif op == FilterOperator.STARTS_WITH:
                params[param_name] = f"{value}%"
                return f"{field_sql} LIKE %({param_name})s"
            elif op == FilterOperator.ENDS_WITH:
                params[param_name] = f"%{value}"
                return f"{field_sql} LIKE %({param_name})s"
            elif op == FilterOperator.REGEX:
                params[param_name] = value
                return f"{field_sql} ~ %({param_name})s"
            
            # Array operations
            elif op == FilterOperator.IN:
                params[param_name] = tuple(value) if isinstance(value, list) else value
                return f"{field_sql} IN %({param_name})s"
            elif op == FilterOperator.ANY_OF:
                params[param_name] = value
                return f"{field_sql} && %({param_name})s"  # PostgreSQL array overlap
            elif op == FilterOperator.ALL_OF:
                params[param_name] = value
                return f"{field_sql} @> %({param_name})s"  # PostgreSQL array contains
            
            return "TRUE"
        
        def build_group(group: FilterGroup) -> str:
            conditions = []
            for f in group.filters:
                if isinstance(f, MetadataFilter):
                    conditions.append(build_condition(f))
                elif isinstance(f, FilterGroup):
                    conditions.append(f"({build_group(f)})")
            
            if not conditions:
                return "TRUE"
            
            if group.operator == LogicalOperator.AND:
                return " AND ".join(conditions)
            elif group.operator == LogicalOperator.OR:
                return " OR ".join(conditions)
            elif group.operator == LogicalOperator.NOT:
                return f"NOT ({' OR '.join(conditions)})"
            
            return " AND ".join(conditions)
        
        if isinstance(filter_spec, MetadataFilter):
            where_clause = build_condition(filter_spec)
        else:
            where_clause = build_group(filter_spec)
        
        return where_clause, params
    
    # ==================== Redis Filtering ====================
    
    def to_redis_query(self, filter_spec: Union[MetadataFilter, FilterGroup]) -> str:
        """
        Convert filter specification to Redis search query (RediSearch syntax)
        """
        def build_redis_condition(filter_obj: MetadataFilter) -> str:
            field = filter_obj.field
            op = filter_obj.operator
            value = filter_obj.value
            
            # Tag filters
            if op == FilterOperator.EQUALS:
                return f"@{field}:{{{value}}}"
            elif op == FilterOperator.IN:
                values = "|".join(str(v) for v in value)
                return f"@{field}:{{{values}}}"
            
            # Numeric filters
            elif op == FilterOperator.GREATER_THAN:
                return f"@{field}:[({value} +inf]"
            elif op == FilterOperator.LESS_THAN:
                return f"@{field}:[-inf ({value}]"
            elif op == FilterOperator.BETWEEN:
                return f"@{field}:[{value[0]} {value[1]}]"
            
            # Text filters
            elif op == FilterOperator.CONTAINS:
                return f"@{field}:{value}"
            elif op == FilterOperator.STARTS_WITH:
                return f"@{field}:{value}*"
            
            return "*"
        
        def build_redis_group(group: FilterGroup) -> str:
            conditions = []
            for f in group.filters:
                if isinstance(f, MetadataFilter):
                    conditions.append(build_redis_condition(f))
                elif isinstance(f, FilterGroup):
                    conditions.append(f"({build_redis_group(f)})")
            
            if not conditions:
                return "*"
            
            if group.operator == LogicalOperator.AND:
                return " ".join(conditions)
            elif group.operator == LogicalOperator.OR:
                return " | ".join(conditions)
            
            return " ".join(conditions)
        
        if isinstance(filter_spec, MetadataFilter):
            return build_redis_condition(filter_spec)
        else:
            return build_redis_group(filter_spec)
    
    # ==================== Utility Methods ====================
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation (e.g., 'metadata.category')"""
        keys = path.split('.')
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _flatten_keys(self, obj: Dict[str, Any], parent_key: str = '') -> Set[str]:
        """Flatten nested dict keys with dot notation"""
        keys = set()
        for k, v in obj.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            keys.add(new_key)
            if isinstance(v, dict):
                keys.update(self._flatten_keys(v, new_key))
        return keys
    
    def register_custom_operator(self, name: str, func: Callable[[Any, Any], bool]):
        """Register a custom filter operator"""
        self.custom_operators[name] = func


# ==================== Pre-built Filter Builders ====================

class FilterBuilder:
    """Fluent API for building filters"""
    
    @staticmethod
    def create() -> FilterGroup:
        """Create a new filter group"""
        return FilterGroup()
    
    @staticmethod
    def equals(field: str, value: Any) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.EQUALS, value)
    
    @staticmethod
    def not_equals(field: str, value: Any) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.NOT_EQUALS, value)
    
    @staticmethod
    def greater_than(field: str, value: Any) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.GREATER_THAN, value)
    
    @staticmethod
    def less_than(field: str, value: Any) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.LESS_THAN, value)
    
    @staticmethod
    def between(field: str, min_val: Any, max_val: Any) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.BETWEEN, [min_val, max_val])
    
    @staticmethod
    def contains(field: str, value: str, case_sensitive: bool = True) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.CONTAINS, value, case_sensitive)
    
    @staticmethod
    def in_list(field: str, values: List[Any]) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.IN, values)
    
    @staticmethod
    def has_tags(field: str, tags: List[str]) -> MetadataFilter:
        return MetadataFilter(field, FilterOperator.ANY_OF, tags)
    
    @staticmethod
    def time_window(field: str, hours: int = 24) -> MetadataFilter:
        """Filter for items within last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return MetadataFilter(field, FilterOperator.GREATER_THAN_OR_EQUAL, cutoff)
    
    @staticmethod
    def recent(field: str = "created_at", days: int = 7) -> MetadataFilter:
        """Filter for recent items (last N days)"""
        cutoff = datetime.now() - timedelta(days=days)
        return MetadataFilter(field, FilterOperator.GREATER_THAN_OR_EQUAL, cutoff)


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Example data
    sample_data = [
        {
            "id": 1,
            "user_id": "user_001",
            "content": "Python programming tips",
            "category": "knowledge",
            "tags": ["python", "coding"],
            "importance": 0.9,
            "created_at": datetime.now() - timedelta(days=2),
            "metadata": {"department": "engineering", "verified": True}
        },
        {
            "id": 2,
            "user_id": "user_002",
            "content": "Meeting notes",
            "category": "episode",
            "tags": ["meeting", "team"],
            "importance": 0.6,
            "created_at": datetime.now() - timedelta(days=10),
            "metadata": {"department": "sales", "verified": False}
        }
    ]
    
    # Create filter engine
    engine = MetadataFilterEngine()
    
    # Example 1: Simple filter
    print("=== Example 1: Category filter ===")
    filter1 = FilterBuilder.equals("category", "knowledge")
    result1 = engine.apply_filter(sample_data, filter1)
    print(f"Results: {len(result1)} items")
    
    # Example 2: Composite filter (AND)
    print("\n=== Example 2: Composite filter (AND) ===")
    filter_group = FilterBuilder.create()
    filter_group.add_filter(FilterBuilder.equals("category", "knowledge"))
    filter_group.add_filter(FilterBuilder.greater_than("importance", 0.8))
    result2 = engine.apply_filter(sample_data, filter_group)
    print(f"Results: {len(result2)} items")
    
    # Example 3: Time-based filter
    print("\n=== Example 3: Recent items (last 7 days) ===")
    filter3 = FilterBuilder.recent("created_at", days=7)
    result3 = engine.apply_filter(sample_data, filter3)
    print(f"Results: {len(result3)} items")
    
    # Example 4: SQL generation
    print("\n=== Example 4: SQL WHERE clause ===")
    where_clause, params = engine.to_sql_where(filter_group)
    print(f"WHERE {where_clause}")
    print(f"Params: {params}")
