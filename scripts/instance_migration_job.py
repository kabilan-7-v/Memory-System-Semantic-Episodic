#!/usr/bin/env python3
"""
Instance Migration Job
Migrates episodes older than 30 days to the instances table.
Runs daily to archive old episodes.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
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

def migrate_episodes_to_instances(cur, conn):
    """Migrate episodes older than 30 days to instances table."""
    print("Checking for episodes older than 30 days...")
    
    # Calculate cutoff date (30 days ago)
    cutoff_date = datetime.now() - timedelta(days=30)
    
    # Find episodes older than 30 days
    cur.execute("""
        SELECT id, user_id, tenant_id, source_type, source_id, 
               messages, message_count, date_from, date_to
        FROM episodes
        WHERE created_at <= %s
        ORDER BY created_at
    """, (cutoff_date,))
    
    old_episodes = cur.fetchall()
    
    if not old_episodes:
        print("  No episodes found that need migration")
        return 0
    
    print(f"  Found {len(old_episodes)} episodes to migrate")
    
    migrated_count = 0
    
    for episode in old_episodes:
        (episode_id, user_id, tenant_id, source_type, source_id,
         messages, message_count, date_from, date_to) = episode
        
        # Insert into instances table
        cur.execute("""
            INSERT INTO instances 
            (user_id, tenant_id, source_type, source_id, original_episode_id,
             messages, message_count, date_from, date_to, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            tenant_id,
            source_type,
            source_id,
            episode_id,
            json.dumps(messages) if not isinstance(messages, str) else messages,
            message_count,
            date_from,
            date_to
        ))
        
        # Delete from episodes table
        cur.execute("DELETE FROM episodes WHERE id = %s", (episode_id,))
        
        migrated_count += 1
    
    conn.commit()
    print(f"✓ Migrated {migrated_count} episodes to instances")
    
    return migrated_count

def compress_old_instances(cur, conn, days_threshold=90):
    """
    Optional: Compress instances older than threshold.
    This is a placeholder for future compression logic.
    """
    print(f"\nChecking for instances older than {days_threshold} days for compression...")
    
    cutoff_date = datetime.now() - timedelta(days=days_threshold)
    
    cur.execute("""
        SELECT COUNT(*)
        FROM instances
        WHERE created_at <= %s AND compressed = FALSE
    """, (cutoff_date,))
    
    count = cur.fetchone()[0]
    
    if count > 0:
        print(f"  Found {count} instances eligible for compression")
        print("  (Compression logic not yet implemented)")
    else:
        print("  No instances found that need compression")
    
    return 0

def cleanup_orphaned_data(cur, conn):
    """Clean up any orphaned data or inconsistencies."""
    print("\nPerforming cleanup checks...")
    
    # Check for episodes without valid source references
    cur.execute("""
        SELECT COUNT(*)
        FROM episodes e
        WHERE e.source_type = 'super_chat' 
        AND NOT EXISTS (SELECT 1 FROM super_chat sc WHERE sc.id = e.source_id)
    """)
    orphaned_sc = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*)
        FROM episodes e
        WHERE e.source_type = 'deepdive'
        AND NOT EXISTS (SELECT 1 FROM deepdive_conversations dc WHERE dc.id = e.source_id)
    """)
    orphaned_dd = cur.fetchone()[0]
    
    if orphaned_sc > 0 or orphaned_dd > 0:
        print(f"  Warning: Found {orphaned_sc + orphaned_dd} orphaned episodes")
    else:
        print("  No orphaned episodes found")
    
    return orphaned_sc + orphaned_dd

def get_statistics(cur):
    """Get database statistics."""
    stats = {}
    
    cur.execute("SELECT COUNT(*) FROM episodes")
    stats['episodes'] = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM instances")
    stats['instances'] = cur.fetchone()[0]
    
    cur.execute("""
        SELECT 
            MIN(created_at) as oldest,
            MAX(created_at) as newest
        FROM episodes
    """)
    result = cur.fetchone()
    stats['episode_date_range'] = result if result[0] else None
    
    cur.execute("""
        SELECT 
            MIN(created_at) as oldest,
            MAX(created_at) as newest
        FROM instances
    """)
    result = cur.fetchone()
    stats['instance_date_range'] = result if result[0] else None
    
    return stats

def main():
    """Main instance migration function."""
    print("=" * 60)
    print("Instance Migration Job - Running at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    print()
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Get initial statistics
        print("Initial Statistics:")
        initial_stats = get_statistics(cur)
        print(f"  Episodes: {initial_stats['episodes']}")
        print(f"  Instances: {initial_stats['instances']}")
        print()
        
        # Migrate old episodes
        migrated = migrate_episodes_to_instances(cur, conn)
        
        # Optional compression
        compressed = compress_old_instances(cur, conn, days_threshold=90)
        
        # Cleanup
        orphaned = cleanup_orphaned_data(cur, conn)
        
        # Get final statistics
        print("\nFinal Statistics:")
        final_stats = get_statistics(cur)
        print(f"  Episodes: {final_stats['episodes']}")
        print(f"  Instances: {final_stats['instances']}")
        
        if final_stats['episode_date_range'] and final_stats['episode_date_range'][0]:
            oldest = final_stats['episode_date_range'][0]
            newest = final_stats['episode_date_range'][1]
            print(f"  Episode date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")
        
        if final_stats['instance_date_range'] and final_stats['instance_date_range'][0]:
            oldest = final_stats['instance_date_range'][0]
            newest = final_stats['instance_date_range'][1]
            print(f"  Instance date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Instance migration completed!")
        print("=" * 60)
        print(f"  Episodes migrated: {migrated}")
        print(f"  Instances compressed: {compressed}")
        if orphaned > 0:
            print(f"  ⚠ Warning: {orphaned} orphaned episodes detected")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during instance migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
