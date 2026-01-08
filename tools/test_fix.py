#!/usr/bin/env python3
"""Quick test to verify the episodes query fix"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    port=5435,
    database="semantic_memory",
    user="postgres",
    password="2191",
    cursor_factory=RealDictCursor
)

cur = conn.cursor()

# Test the fixed query
print("Testing episodes query with messages search...")
cur.execute("""
    SELECT 
        'EPISODIC-EPISODES' as source_layer,
        'episodes' as table_name,
        id,
        messages,
        message_count,
        source_type,
        created_at
    FROM episodes
    WHERE user_id = %s
      AND messages::text ILIKE %s
    ORDER BY created_at DESC
    LIMIT 5
""", ('tech_lead_001', '%hobby%'))

results = cur.fetchall()
print(f"✓ Query executed successfully!")
print(f"✓ Found {len(results)} episodes matching 'hobby'")

for item in results:
    print(f"\n  Episode ID: {item['id']}")
    print(f"  Messages: {item['message_count']}")
    import json
    messages = json.loads(item['messages']) if isinstance(item['messages'], str) else item['messages']
    if messages:
        print(f"  First message: {messages[0]['content'][:60]}...")

cur.close()
conn.close()

print("\n✅ Fix verified - episodes query working correctly!")
