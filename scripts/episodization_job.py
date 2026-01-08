#!/usr/bin/env python3
"""
Episodization Job
Runs every 6 hours to convert messages into episodes.
Processes messages that haven't been episodized yet.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5435'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        database=os.getenv('DB_NAME', 'bap_memory')
    )

def generate_episode_embedding(messages):
    """Generate a simple embedding for episode (384 dimensions for sentence-transformers)."""
    # In production, use actual embedding model
    # For now, generate random normalized vector
    vec = np.random.randn(384)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()

def episodize_super_chat(cur, conn):
    """Episodize super chat messages."""
    print("Processing super chat messages...")
    
    # Find all super chats with non-episodized messages
    cur.execute("""
        SELECT DISTINCT sc.id, sc.user_id
        FROM super_chat sc
        INNER JOIN super_chat_messages scm ON sc.id = scm.super_chat_id
        WHERE scm.episodized = FALSE
    """)
    
    super_chats = cur.fetchall()
    
    if not super_chats:
        print("  No super chat messages to episodize")
        return 0
    
    episodes_created = 0
    
    for super_chat_id, user_id in super_chats:
        # Get non-episodized messages ordered by time
        cur.execute("""
            SELECT id, role, content, created_at
            FROM super_chat_messages
            WHERE super_chat_id = %s AND episodized = FALSE
            ORDER BY created_at
        """, (super_chat_id,))
        
        messages = cur.fetchall()
        
        if not messages:
            continue
        
        # Group messages into episodes (by 6-hour windows or conversation breaks)
        current_episode = []
        episode_start_time = messages[0][3]
        message_ids_in_episode = []
        
        for msg_id, role, content, created_at in messages:
            time_diff = (created_at - episode_start_time).total_seconds() / 3600
            
            # If more than 6 hours have passed or we have 50+ messages, create episode
            if time_diff >= 6 or len(current_episode) >= 50:
                if current_episode:
                    # Create episode from accumulated messages
                    create_episode(
                        cur, conn, user_id, None, 'super_chat', 
                        super_chat_id, current_episode, message_ids_in_episode
                    )
                    episodes_created += 1
                
                # Start new episode
                current_episode = []
                message_ids_in_episode = []
                episode_start_time = created_at
            
            # Add message to current episode
            current_episode.append({
                'role': role,
                'content': content,
                'timestamp': created_at.isoformat()
            })
            message_ids_in_episode.append(msg_id)
        
        # Create episode for remaining messages
        if current_episode:
            create_episode(
                cur, conn, user_id, None, 'super_chat',
                super_chat_id, current_episode, message_ids_in_episode
            )
            episodes_created += 1
    
    print(f"✓ Created {episodes_created} episodes from super chat messages")
    return episodes_created

def episodize_deepdive(cur, conn):
    """Episodize deep dive messages."""
    print("Processing deep dive messages...")
    
    # Find all deep dive conversations with messages
    cur.execute("""
        SELECT DISTINCT dc.id, dc.user_id, dc.tenant_id
        FROM deepdive_conversations dc
        INNER JOIN deepdive_messages dm ON dc.id = dm.deepdive_conversation_id
        WHERE dm.id NOT IN (
            SELECT CAST(msg->>'id' AS INTEGER)
            FROM episodes, jsonb_array_elements(messages) AS msg
            WHERE source_type = 'deepdive' AND source_id = dc.id
        )
    """)
    
    conversations = cur.fetchall()
    
    if not conversations:
        print("  No deep dive messages to episodize")
        return 0
    
    episodes_created = 0
    
    for conv_id, user_id, tenant_id in conversations:
        # Get all messages for this conversation
        cur.execute("""
            SELECT id, role, content, created_at
            FROM deepdive_messages
            WHERE deepdive_conversation_id = %s
            ORDER BY created_at
        """, (conv_id,))
        
        messages = cur.fetchall()
        
        if not messages:
            continue
        
        # For deep dive, we can create episodes per conversation or chunk them
        # Let's chunk by 30 messages or 6-hour windows
        current_episode = []
        episode_start_time = messages[0][3]
        
        for msg_id, role, content, created_at in messages:
            time_diff = (created_at - episode_start_time).total_seconds() / 3600
            
            # Create episode if time exceeds 6 hours or we have 30+ messages
            if time_diff >= 6 or len(current_episode) >= 30:
                if current_episode:
                    create_episode(
                        cur, conn, user_id, tenant_id, 'deepdive',
                        conv_id, current_episode, []
                    )
                    episodes_created += 1
                
                # Start new episode
                current_episode = []
                episode_start_time = created_at
            
            # Add message to current episode
            current_episode.append({
                'role': role,
                'content': content,
                'timestamp': created_at.isoformat()
            })
        
        # Create episode for remaining messages
        if current_episode:
            create_episode(
                cur, conn, user_id, tenant_id, 'deepdive',
                conv_id, current_episode, []
            )
            episodes_created += 1
    
    print(f"✓ Created {episodes_created} episodes from deep dive messages")
    return episodes_created

def create_episode(cur, conn, user_id, tenant_id, source_type, source_id, messages, message_ids):
    """Create an episode from messages."""
    if not messages:
        return
    
    # Extract timestamps
    timestamps = [datetime.fromisoformat(msg['timestamp']) for msg in messages]
    date_from = min(timestamps)
    date_to = max(timestamps)
    
    # Generate embedding
    embedding = generate_episode_embedding(messages)
    
    # Create episode
    cur.execute("""
        INSERT INTO episodes 
        (user_id, tenant_id, source_type, source_id, messages, message_count, date_from, date_to, vector)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        tenant_id,
        source_type,
        source_id,
        json.dumps(messages),
        len(messages),
        date_from,
        date_to,
        embedding
    ))
    
    # Mark super chat messages as episodized
    if source_type == 'super_chat' and message_ids:
        cur.execute("""
            UPDATE super_chat_messages
            SET episodized = TRUE, episodized_at = NOW()
            WHERE id = ANY(%s)
        """, (message_ids,))
    
    conn.commit()

def main():
    """Main episodization function."""
    print("=" * 60)
    print("Episodization Job - Running at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    print()
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Episodize messages
        sc_episodes = episodize_super_chat(cur, conn)
        dd_episodes = episodize_deepdive(cur, conn)
        
        total_episodes = sc_episodes + dd_episodes
        
        # Get statistics
        cur.execute("SELECT COUNT(*) FROM episodes")
        total_episode_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM super_chat_messages WHERE episodized = FALSE")
        remaining_sc_messages = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Episodization completed!")
        print("=" * 60)
        print(f"  Episodes created this run: {total_episodes}")
        print(f"  Total episodes in database: {total_episode_count}")
        print(f"  Remaining super chat messages: {remaining_sc_messages}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during episodization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
