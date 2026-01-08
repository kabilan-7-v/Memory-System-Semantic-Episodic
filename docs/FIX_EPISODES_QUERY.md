# Fix Applied: Episodes Query Error

## Issue
```
❌ Error: column "summary" does not exist
LINE 6:                 summary,
```

When asking questions like "what are my hobby?", the system tried to search the episodes table for a "summary" column that doesn't exist.

## Root Cause
The hybrid_search() method was querying for a `summary` field in the episodes table, but the actual schema has:
- `messages` (jsonb) - contains the actual conversation messages
- No `summary` field

## Fix Applied

### 1. Updated Episodes Query
**Before:**
```sql
SELECT summary, message_count, source_type, created_at
FROM episodes
WHERE user_id = %s AND summary ILIKE %s
```

**After:**
```sql
SELECT messages, message_count, source_type, created_at
FROM episodes  
WHERE user_id = %s AND messages::text ILIKE %s
```

### 2. Updated Display Function
**Before:**
```python
print(f"   Summary: {item['summary'][:100]}...")
```

**After:**
```python
messages = json.loads(item['messages']) if isinstance(item['messages'], str) else item['messages']
first_msg = messages[0]['content'][:80] if messages else 'No messages'
print(f"   Preview: {first_msg}...")
```

## Result
✅ Questions now work correctly  
✅ Episodes are searchable by message content  
✅ Search displays actual message previews instead of non-existent summaries

## Test
```
user tech_lead_001
what are my hobbies?
```

Expected behavior:
1. ✓ Question stored in EPISODIC
2. ✓ Searches across all layers (including episodes)
3. ✓ AI generates response based on Michael Chen's stored data
4. ✓ No "summary" column errors

## Files Modified
- `interactive_memory_app.py` (lines 380-391, 443-449)
