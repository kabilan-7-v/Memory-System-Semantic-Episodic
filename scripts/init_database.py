#!/usr/bin/env python3
"""
Database Initialization Script
Creates the database and all required tables according to the unified schema.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Create the database if it doesn't exist."""
    # Connect to PostgreSQL server
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5435'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        database='postgres'  # Connect to default database
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    db_name = os.getenv('DB_NAME', 'bap_memory')
    
    # Check if database exists
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
    exists = cur.fetchone()
    
    if not exists:
        print(f"Creating database '{db_name}'...")
        cur.execute(f'CREATE DATABASE {db_name}')
        print(f"✓ Database '{db_name}' created successfully!")
    else:
        print(f"✓ Database '{db_name}' already exists.")
    
    cur.close()
    conn.close()

def init_schema():
    """Initialize all tables and indexes."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5435'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        database=os.getenv('DB_NAME', 'bap_memory')
    )
    cur = conn.cursor()
    
    print("\nInitializing database schema...")
    
    # Read and execute schema file
    schema_path = Path(__file__).parent.parent / 'database' / 'unified_schema.sql'
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    cur.execute(schema_sql)
    conn.commit()
    
    print("✓ Schema initialized successfully!")
    
    # Verify tables created
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    print(f"\n✓ Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    
    cur.close()
    conn.close()

def main():
    """Main initialization function."""
    print("=" * 60)
    print("BAP Memory System - Database Initialization")
    print("=" * 60)
    
    try:
        # Step 1: Create database
        create_database()
        
        # Step 2: Initialize schema
        init_schema()
        
        print("\n" + "=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
