# Scripts Directory

This directory contains all database setup, data population, and lifecycle management scripts for the BAP Memory System.

## Scripts Overview

### Setup Scripts

#### `init_database.py`
Creates and initializes the PostgreSQL database with all required tables.

**Usage:**
```bash
python scripts/init_database.py
```

**What it does:**
- Creates `bap_memory` database
- Enables pgvector extension
- Creates all tables from unified schema
- Creates indexes for vector and full-text search
- Sets up triggers for auto-updates

**Requirements:**
- PostgreSQL 15+ installed
- `.env` file configured with DB credentials

---

#### `populate_data.py`
Generates ~250 sample entries across all memory tables.

**Usage:**
```bash
python scripts/populate_data.py
```

**What it creates:**
- 5 user personas (diverse professional profiles)
- 50 knowledge base entries (various tech topics)
- 300 super chat messages (distributed over 45 days)
- 260 deep dive messages (20 conversations)
- Total: ~615 records

**Data characteristics:**
- Realistic conversation patterns
- Multiple topics and expertise areas
- Time-distributed messages for testing lifecycle
- Mock embeddings (1536-dim and 384-dim)

---

### Lifecycle Management Scripts

#### `episodization_job.py`
Converts raw messages into searchable episodes.

**Usage:**
```bash
python scripts/episodization_job.py
```

**Schedule:** Every 6 hours (via scheduler)

**Process:**
1. Finds non-episodized messages
2. Groups into episodes by time window (6 hours) or message count (50)
3. Generates episode embeddings
4. Marks messages as episodized

**Grouping rules:**
- **Super Chat**: 6-hour windows OR 50 messages (whichever comes first)
- **Deep Dive**: 6-hour windows OR 30 messages (whichever comes first)

**Output:**
- Episode records in `episodes` table
- Updated `episodized` flag on messages
- Episode embeddings for semantic search

---

#### `instance_migration_job.py`
Archives old episodes (>30 days) to instances table.

**Usage:**
```bash
python scripts/instance_migration_job.py
```

**Schedule:** Daily at 02:00 (via scheduler)

**Process:**
1. Finds episodes created >30 days ago
2. Copies to `instances` table
3. Deletes from `episodes` table
4. Reports orphaned data
5. Prepares for compression (>90 days, placeholder)

**Benefits:**
- Keeps recent episodes table small and fast
- Maintains full history in instances
- Optimizes query performance
- Reduces storage costs over time

---

#### `scheduler.py`
Automated job scheduler that runs both lifecycle jobs.

**Usage:**
```bash
python scripts/scheduler.py
```

**Schedule:**
- **Episodization**: Every 6 hours
- **Instance Migration**: Daily at 02:00

**Features:**
- Runs episodization immediately on startup
- Logs all job executions
- Graceful shutdown with Ctrl+C
- Can be run as systemd service or daemon

**Running as background service:**

**Option 1: Direct execution**
```bash
nohup python scripts/scheduler.py > scheduler.log 2>&1 &
```

**Option 2: Systemd (Linux)**
```ini
# /etc/systemd/system/bap-scheduler.service
[Unit]
Description=BAP Memory System Scheduler
After=postgresql.service

[Service]
Type=simple
ExecStart=/path/to/python /path/to/scripts/scheduler.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable bap-scheduler
sudo systemctl start bap-scheduler
```

**Option 3: Cron (Unix/Linux/macOS)**
```cron
# Episodization every 6 hours
0 */6 * * * cd /path/to/September-Test && python scripts/episodization_job.py >> /var/log/bap-episodization.log 2>&1

# Instance migration daily at 2 AM
0 2 * * * cd /path/to/September-Test && python scripts/instance_migration_job.py >> /var/log/bap-migration.log 2>&1
```

---

## Quick Start

### Automated Setup (Recommended)

Use the quickstart script from project root:

```bash
./quickstart.sh
```

This runs all setup steps automatically.

### Manual Setup

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-jobs.txt

# 3. Initialize database
python scripts/init_database.py

# 4. Populate sample data
python scripts/populate_data.py

# 5. Run initial episodization
python scripts/episodization_job.py

# 6. Start scheduler (optional)
python scripts/scheduler.py
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=bap_memory
```

---

## Verification Commands

### Check Database Status

```bash
# Connect to database
psql -U postgres -d bap_memory

# Count records
SELECT 
    'user_persona' as table, COUNT(*) FROM user_persona
UNION ALL
SELECT 'knowledge_base', COUNT(*) FROM knowledge_base
UNION ALL
SELECT 'super_chat_messages', COUNT(*) FROM super_chat_messages
UNION ALL
SELECT 'episodes', COUNT(*) FROM episodes
UNION ALL
SELECT 'instances', COUNT(*) FROM instances;

# Check episodization status
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE episodized = TRUE) as episodized,
    COUNT(*) FILTER (WHERE episodized = FALSE) as pending
FROM super_chat_messages;

# View recent episodes
SELECT id, user_id, source_type, message_count, date_from, date_to
FROM episodes
ORDER BY created_at DESC
LIMIT 10;
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL is running
pg_isready

# Test connection
psql -U postgres -c "SELECT NOW();"

# Check database exists
psql -U postgres -l | grep bap_memory
```

### pgvector Extension Missing

```bash
# Install pgvector (Ubuntu/Debian)
sudo apt install postgresql-15-pgvector

# Install pgvector (macOS)
brew install pgvector

# Or build from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### Python Dependencies

```bash
# Reinstall all dependencies
pip install -r requirements.txt -r requirements-jobs.txt --force-reinstall

# Check installed packages
pip list | grep -E "psycopg2|pgvector|schedule"
```

### Job Execution Errors

```bash
# Run jobs with verbose output
python scripts/episodization_job.py 2>&1 | tee episodization.log
python scripts/instance_migration_job.py 2>&1 | tee migration.log

# Check permissions
chmod +x scripts/*.py

# Verify Python path
which python3
python3 --version
```

---

## File Permissions

All scripts should be executable:

```bash
chmod +x scripts/*.py
```

---

## Dependencies

### Core Dependencies (requirements.txt)
- `psycopg2-binary` - PostgreSQL adapter
- `pgvector` - Vector extension client
- `numpy` - Numerical operations
- `python-dotenv` - Environment variable management

### Job Dependencies (requirements-jobs.txt)
- `schedule` - Job scheduling
- `python-dateutil` - Date/time utilities

---

## Architecture

```
┌─────────────────────────────────────┐
│         Application                 │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│    Scripts (this directory)         │
├─────────────────────────────────────┤
│  Setup:                             │
│  • init_database.py                 │
│  • populate_data.py                 │
├─────────────────────────────────────┤
│  Lifecycle Jobs:                    │
│  • episodization_job.py (6h)        │
│  • instance_migration_job.py (24h)  │
│  • scheduler.py (orchestrator)      │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│    PostgreSQL + pgvector            │
│    (bap_memory database)            │
└─────────────────────────────────────┘
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor scheduler logs
- Check database size growth

**Weekly:**
- Review instance migration statistics
- Vacuum and analyze tables:
  ```sql
  VACUUM ANALYZE episodes;
  VACUUM ANALYZE instances;
  ```

**Monthly:**
- Review and adjust episodization windows
- Optimize vector indexes:
  ```sql
  REINDEX INDEX CONCURRENTLY idx_episodes_vector;
  ```
- Archive very old instances (>180 days)

### Database Backup

```bash
# Backup entire database
pg_dump -U postgres bap_memory > backup_$(date +%Y%m%d).sql

# Backup specific tables
pg_dump -U postgres -t episodes -t instances bap_memory > backup_memory_$(date +%Y%m%d).sql

# Restore
psql -U postgres bap_memory < backup_20260107.sql
```

---

## Support

For detailed documentation, see:
- [SETUP_GUIDE.md](../SETUP_GUIDE.md) - Complete setup instructions
- [DATABASE_SETUP_SUMMARY.md](../DATABASE_SETUP_SUMMARY.md) - Implementation summary
- [MEMORY_SYSTEM_SCHEMA.md](../MEMORY_SYSTEM_SCHEMA.md) - Schema reference

---

**Last Updated:** January 2026
**Version:** 1.0
**Status:** Production Ready ✅
