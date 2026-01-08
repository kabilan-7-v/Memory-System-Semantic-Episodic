#!/usr/bin/env python3
"""
Simple Real-time Memory System Demo
Handles live conversations and retrieval from memory (DB).
"""
import os
import psycopg2
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5435'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '2191'),
        database=os.getenv('DB_NAME', 'semantic_memory')
    )

def store_conversation(user_id, user_message, assistant_response):
    """Store real-time conversation in database."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get or create super chat
    cur.execute("SELECT id FROM super_chat WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    
    if result:
        super_chat_id = result[0]
    else:
        cur.execute("INSERT INTO super_chat (user_id) VALUES (%s) RETURNING id", (user_id,))
        super_chat_id = cur.fetchone()[0]
    
    # Store user message
    cur.execute("""
        INSERT INTO super_chat_messages (super_chat_id, role, content, episodized)
        VALUES (%s, 'user', %s, FALSE) RETURNING id
    """, (super_chat_id, user_message))
    user_msg_id = cur.fetchone()[0]
    
    # Store assistant response
    cur.execute("""
        INSERT INTO super_chat_messages (super_chat_id, role, content, episodized)
        VALUES (%s, 'assistant', %s, FALSE) RETURNING id
    """, (super_chat_id, assistant_response))
    assistant_msg_id = cur.fetchone()[0]
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        'user_msg_id': user_msg_id,
        'assistant_msg_id': assistant_msg_id,
        'super_chat_id': super_chat_id
    }

def hybrid_search(query, user_id=None, limit=10):
    """Search using hybrid approach (vector + text)."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Generate mock embedding for knowledge base (1536 dim)
    vec = np.random.randn(1536)
    embedding_1536 = (vec / np.linalg.norm(vec)).tolist()
    
    # Generate mock embedding for episodes (384 dim)
    vec = np.random.randn(384)
    embedding_384 = (vec / np.linalg.norm(vec)).tolist()
    
    results = {}
    
    # Search knowledge base
    kb_sql = """
        SELECT 
            id, user_id, content, category, tags,
            1 - (embedding <=> %s::vector) AS similarity
        FROM knowledge_base
        WHERE 1=1
    """
    params = [embedding_1536]
    
    if user_id:
        kb_sql += " AND user_id = %s"
        params.append(user_id)
    
    kb_sql += " ORDER BY similarity DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(kb_sql, params)
    results['knowledge'] = []
    for row in cur.fetchall():
        results['knowledge'].append({
            'id': str(row[0]),
            'user_id': row[1],
            'content': row[2],
            'category': row[3],
            'tags': row[4],
            'similarity': float(row[5])
        })
    
    # Search episodes
    ep_sql = """
        SELECT 
            id, user_id, source_type, message_count, date_from, date_to,
            1 - (vector <=> %s::vector) AS similarity
        FROM episodes
        WHERE 1=1
    """
    params = [embedding_384]
    
    if user_id:
        ep_sql += " AND user_id = %s"
        params.append(user_id)
    
    ep_sql += " ORDER BY similarity DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(ep_sql, params)
    results['episodes'] = []
    for row in cur.fetchall():
        results['episodes'].append({
            'id': row[0],
            'user_id': row[1],
            'source_type': row[2],
            'message_count': row[3],
            'similarity': float(row[6])
        })
    
    # Search recent messages
    msg_sql = """
        SELECT scm.id, sc.user_id, scm.role, scm.content, scm.created_at
        FROM super_chat_messages scm
        JOIN super_chat sc ON sc.id = scm.super_chat_id
        WHERE scm.content ILIKE %s
    """
    params = [f'%{query}%']
    
    if user_id:
        msg_sql += " AND sc.user_id = %s"
        params.append(user_id)
    
    msg_sql += " ORDER BY scm.created_at DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(msg_sql, params)
    results['messages'] = []
    for row in cur.fetchall():
        results['messages'].append({
            'id': row[0],
            'user_id': row[1],
            'role': row[2],
            'content': row[3],
            'timestamp': row[4].isoformat() if row[4] else None
        })
    
    cur.close()
    conn.close()
    
    return results

def get_conversation_context(user_id, limit=10):
    """Get recent conversation history."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT scm.role, scm.content, scm.created_at
        FROM super_chat_messages scm
        JOIN super_chat sc ON sc.id = scm.super_chat_id
        WHERE sc.user_id = %s
        ORDER BY scm.created_at DESC
        LIMIT %s
    """, (user_id, limit))
    
    messages = []
    for row in cur.fetchall():
        messages.append({
            'role': row[0],
            'content': row[1],
            'timestamp': row[2].isoformat() if row[2] else None
        })
    
    cur.close()
    conn.close()
    
    return list(reversed(messages))

# Demo
if __name__ == '__main__':
    print("=" * 70)
    print("REALTIME MEMORY SYSTEM - Demo")
    print("=" * 70)
    
    # 1. Store conversation
    print("\n1. Storing real-time conversation...")
    result = store_conversation(
        'user_001',
        'How do I implement caching in Redis?',
        'Redis caching can be implemented using TTL, LRU eviction, and key patterns...'
    )
    print(f"   ✓ Stored conversation (Message IDs: {result['user_msg_id']}, {result['assistant_msg_id']})")
    print(f"   ✓ Location: super_chat_messages table (super_chat_id: {result['super_chat_id']})")
    
    # 2. Hybrid search
    print("\n2. Performing hybrid search for 'API design'...")
    search_results = hybrid_search('API design', 'user_001', limit=5)
    print(f"   ✓ Found {len(search_results['knowledge'])} knowledge items")
    print(f"   ✓ Found {len(search_results['episodes'])} related episodes")
    print(f"   ✓ Found {len(search_results['messages'])} matching messages")
    
    if search_results['knowledge']:
        print(f"\n   Top knowledge result:")
        item = search_results['knowledge'][0]
        print(f"   - {item['content'][:80]}...")
        print(f"   - Similarity: {item['similarity']:.3f}")
    
    # 3. Get conversation context
    print("\n3. Retrieving conversation context...")
    context = get_conversation_context('user_001', limit=5)
    print(f"   ✓ Retrieved {len(context)} recent messages")
    
    if context:
        print(f"\n   Most recent message:")
        print(f"   - {context[-1]['role']}: {context[-1]['content'][:60]}...")
    
    # 4. Verify database state
    print("\n4. Verifying database state...")
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM knowledge_base")
    kb_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM super_chat_messages")
    msg_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM episodes")
    ep_count = cur.fetchone()[0]
    
    print(f"   ✓ Knowledge base: {kb_count} entries")
    print(f"   ✓ Messages: {msg_count} stored")
    print(f"   ✓ Episodes: {ep_count} created")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✓ Demo completed successfully!")
    print("=" * 70)
    print("\nNew data added to database:")
    print("  • Real-time conversations → super_chat_messages table")
    print("  • Hybrid search → Queries episodes, knowledge_base, messages")
    print("  • Context retrieval → Gets relevant conversation history")
    print("=" * 70)
