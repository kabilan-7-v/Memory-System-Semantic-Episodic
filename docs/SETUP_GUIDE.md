# BAP Memory System - Setup & Usage Guide

## Overview

This guide will help you set up the BAP Memory System database with ~250 sample entries and configure automated jobs for memory lifecycle management.

## Prerequisites

- PostgreSQL 15+ installed with pgvector extension
- Python 3.8+
- pip package manager

## Installation Steps

### 1. Install PostgreSQL and pgvector

#### macOS (Homebrew)
```bash
brew install postgresql@15
brew services start postgresql@15

# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-15-pgvector
sudo systemctl start postgresql
```

### 2. Install Python Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Job scheduler dependencies
pip install -r requirements-jobs.txt
```

### 3. Configure Database Connection

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=bap_memory
```

## Database Setup

### Step 1: Initialize Database

This creates the database and all required tables:

```bash
python scripts/init_database.py
```

Expected output:
```
============================================================
BAP Memory System - Database Initialization
============================================================
Creating database 'bap_memory'...
✓ Database 'bap_memory' created successfully!

Initializing database schema...
✓ Schema initialized successfully!

✓ Created 11 tables:
  - user_persona
  - knowledge_base
  - semantic_memory_index
  - super_chat
  - super_chat_messages
  - deepdive_conversations
  - deepdive_messages
  - episodes
  - instances
  ...

============================================================
✓ Database initialization completed successfully!
============================================================
```

### Step 2: Populate Sample Data

This creates ~250 sample entries across all tables:

```bash
python scripts/populate_data.py
```

Expected output:
```
============================================================
BAP Memory System - Data Population
============================================================

Creating user personas...
✓ Created 5 user personas
Creating 50 knowledge base entries...
✓ Created 50 knowledge base entries
Creating conversations with ~150 messages...
✓ Created 5 super chats
✓ Created 300 messages
Creating 20 deep dive conversations...
✓ Created 20 deep dive conversations with 240 messages

============================================================
✓ Data population completed successfully!
============================================================

Total records created: 615
  - User Personas: 5
  - Knowledge Base: 50
  - Super Chat Messages: 300
  - Deep Dive Messages: 260
============================================================
```

## Memory Lifecycle Jobs

The system implements automated memory lifecycle management:

```
Messages → Episodes (< 30 days) → Instances (> 30 days) → Archive/Compression
```

### Job 1: Episodization (Every 6 Hours)

Converts messages into episodes:

```bash
python scripts/episodization_job.py
```

This job:
- Groups messages into episodes (6-hour windows or 50 messages max)
- Generates embeddings for semantic search
- Marks messages as episodized
- Can be run manually or via scheduler

### Job 2: Instance Migration (Daily)

Migrates old episodes (> 30 days) to instances table:

```bash
python scripts/instance_migration_job.py
```

This job:
- Finds episodes older than 30 days
- Moves them to instances table
- Cleans up orphaned data
- Prepares old instances for compression (placeholder)

### Running Jobs Automatically

Use the scheduler to run jobs automatically:

```bash
python scripts/scheduler.py
```

The scheduler:
- Runs episodization every 6 hours
- Runs instance migration daily at 2 AM
- Logs all job executions
- Can be stopped with Ctrl+C

#### Running as Background Service

**Option 1: Using systemd (Linux)**

Create `/etc/systemd/system/bap-scheduler.service`:

```ini
[Unit]
Description=BAP Memory System Job Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/September-Test
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python scripts/scheduler.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable bap-scheduler
sudo systemctl start bap-scheduler
sudo systemctl status bap-scheduler
```

**Option 2: Using cron**

```bash
crontab -e
```

Add these lines:
```cron
# Episodization every 6 hours
0 */6 * * * cd /path/to/September-Test && /path/to/python scripts/episodization_job.py >> /var/log/bap-episodization.log 2>&1

# Instance migration daily at 2 AM
0 2 * * * cd /path/to/September-Test && /path/to/python scripts/instance_migration_job.py >> /var/log/bap-migration.log 2>&1
```

## Verification

### Check Database Contents

Connect to PostgreSQL:

```bash
psql -U postgres -d bap_memory
```

Run queries:

```sql
-- Count records in each table
SELECT 'user_persona' as table, COUNT(*) FROM user_persona
UNION ALL
SELECT 'knowledge_base', COUNT(*) FROM knowledge_base
UNION ALL
SELECT 'super_chat_messages', COUNT(*) FROM super_chat_messages
UNION ALL
SELECT 'deepdive_messages', COUNT(*) FROM deepdive_messages
UNION ALL
SELECT 'episodes', COUNT(*) FROM episodes
UNION ALL
SELECT 'instances', COUNT(*) FROM instances;

-- Check episodization status
SELECT 
    COUNT(*) as total_messages,
    COUNT(*) FILTER (WHERE episodized = TRUE) as episodized,
    COUNT(*) FILTER (WHERE episodized = FALSE) as not_episodized
FROM super_chat_messages;

-- View recent episodes
SELECT 
    id, user_id, source_type, message_count, 
    date_from, date_to, created_at
FROM episodes
ORDER BY created_at DESC
LIMIT 10;

-- View instances
SELECT 
    id, user_id, source_type, message_count,
    date_from, date_to, created_at
FROM instances
ORDER BY created_at DESC
LIMIT 10;
```

## Memory Lifecycle Architecture

### Short-Term Memory (STM)
- **Charter Store**: Execution blueprints from Planner Agent
- **Agent Notes**: Scratchpad for agent reasoning
- **Recent Context**: Last 15 contexts from Dynamic Context Management
- **TTL**: 24 hours (auto-cleanup)

### Long-Term Memory (LTM)

#### 1. Episodic Memory
- **Messages**: Raw conversation messages (super chat & deep dive)
- **Episodes**: Consolidated messages < 30 days old
- **Instances**: Archived episodes > 30 days old
- **Lifecycle**: Messages → Episodes → Instances → Archive

#### 2. Semantic Memory
- **User Persona**: User preferences, communication style, behavioral patterns
- **Knowledge Base**: Facts, skills, processes learned over time
- **Embeddings**: Vector search for semantic retrieval

#### 3. File Memory
- User-uploaded files with content extraction
- Full-text and vector search capabilities

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Check if database exists
psql -U postgres -l | grep bap_memory

# Test connection
psql -U postgres -d bap_memory -c "SELECT NOW();"
```

### pgvector Extension Not Found

```bash
# Verify extension is installed
psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"

# Enable extension manually
psql -U postgres -d bap_memory -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Job Execution Errors

Check logs and verify:
- Database connection parameters in `.env`
- Python dependencies installed
- Scripts have execute permissions: `chmod +x scripts/*.py`

## Next Steps

1. **Integrate with Application**: Use the populated database with your memory system
2. **Customize Jobs**: Adjust episodization windows or migration thresholds
3. **Monitor Performance**: Track job execution times and database growth
4. **Implement Compression**: Add compression logic for old instances
5. **Add Analytics**: Create dashboards for memory usage patterns

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│          SHORT-TERM MEMORY                  │
│  - Working Memory (Charter, Notes, Context) │
│  - Cache Entries (L1, L2, L3)              │
│  - TTL: 24 hours                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│          LONG-TERM MEMORY                   │
│  ┌───────────────────────────────────────┐  │
│  │ Episodic (Conversations & Summaries)  │  │
│  │  - Super Chat Messages                │  │
│  │  - Deep Dive Conversations            │  │
│  │  - Episodes (< 30 days)               │  │
│  │  - Instances (> 30 days)              │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ Semantic Memory                       │  │
│  │  - User Persona                       │  │
│  │  - Knowledge & Entities               │  │
│  │  - Processes & Skills                 │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ File Memory (User Files)              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘

         Automated Jobs (scheduled)
         
┌─────────────────────────────────────────────┐
│  Episodization Job (Every 6 hours)          │
│  • Groups messages into episodes            │
│  • Generates embeddings                     │
│  • Marks messages as episodized             │
└─────────────────────────────────────────────┘
         
┌─────────────────────────────────────────────┐
│  Instance Migration Job (Daily)             │
│  • Migrates old episodes (>30 days)         │
│  • Archives to instances table              │
│  • Optional compression                     │
└─────────────────────────────────────────────┘
```

## Support

For issues or questions, refer to the main documentation:
- `MEMORY_SYSTEM_SCHEMA.md` - Complete schema documentation
- `IMPLEMENTATION_SUMMARY.md` - System implementation details
- `UNIFIED_DEMO.md` - API usage examples
