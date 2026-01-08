#!/bin/bash

# BAP Memory System - Quick Start Script
# This script sets up the entire system in one go

set -e  # Exit on error

echo "============================================================"
echo "BAP Memory System - Quick Start"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python 3 found: $(python3 --version)"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "✗ PostgreSQL not found. Please install PostgreSQL 15+"
    exit 1
fi
echo "✓ PostgreSQL found: $(psql --version)"

# Check .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env 2>/dev/null || echo "# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=bap_memory" > .env
    echo "✓ .env file created"
    echo "⚠  Please edit .env with your PostgreSQL credentials"
    echo ""
    read -p "Press Enter to continue after editing .env..."
fi

echo ""
echo "============================================================"
echo "Step 1: Installing Python dependencies"
echo "============================================================"
pip3 install -r requirements.txt -q
pip3 install -r requirements-jobs.txt -q
echo "✓ Dependencies installed"

echo ""
echo "============================================================"
echo "Step 2: Initializing database"
echo "============================================================"
python3 scripts/init_database.py

echo ""
echo "============================================================"
echo "Step 3: Populating sample data (~250 entries)"
echo "============================================================"
python3 scripts/populate_data.py

echo ""
echo "============================================================"
echo "Step 4: Running initial episodization"
echo "============================================================"
python3 scripts/episodization_job.py

echo ""
echo "============================================================"
echo "✓ Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the job scheduler (runs episodization every 6 hours):"
echo "   python3 scripts/scheduler.py"
echo ""
echo "2. Or run jobs manually:"
echo "   python3 scripts/episodization_job.py      # Group messages into episodes"
echo "   python3 scripts/instance_migration_job.py # Archive old episodes"
echo ""
echo "3. Connect to database to explore:"
echo "   psql -U postgres -d bap_memory"
echo ""
echo "4. Read the setup guide for more details:"
echo "   cat SETUP_GUIDE.md"
echo ""
echo "============================================================"
