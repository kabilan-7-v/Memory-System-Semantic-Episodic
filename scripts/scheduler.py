#!/usr/bin/env python3
"""
Job Scheduler
Schedules and runs episodization (every 6 hours) and instance migration (daily) jobs.
Can be run as a daemon or via cron.
"""
import os
import sys
from pathlib import Path
import schedule
import time
from datetime import datetime
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Get absolute paths to job scripts
SCRIPT_DIR = Path(__file__).parent
EPISODIZATION_SCRIPT = SCRIPT_DIR / 'episodization_job.py'
MIGRATION_SCRIPT = SCRIPT_DIR / 'instance_migration_job.py'

def run_episodization_job():
    """Run episodization job."""
    print("\n" + "=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running Episodization Job")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(EPISODIZATION_SCRIPT)],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"✗ Episodization job failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
    except Exception as e:
        print(f"✗ Error running episodization job: {e}")

def run_migration_job():
    """Run instance migration job."""
    print("\n" + "=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running Instance Migration Job")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(MIGRATION_SCRIPT)],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"✗ Migration job failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
    except Exception as e:
        print(f"✗ Error running migration job: {e}")

def print_schedule_info():
    """Print current schedule information."""
    print("=" * 60)
    print("BAP Memory System - Job Scheduler")
    print("=" * 60)
    print("\nScheduled Jobs:")
    print("  • Episodization: Every 6 hours")
    print("  • Instance Migration: Every day at 02:00")
    print("\nNext scheduled runs:")
    for job in schedule.jobs:
        print(f"  • {job}")
    print("\nPress Ctrl+C to stop the scheduler")
    print("=" * 60)

def main():
    """Main scheduler function."""
    print_schedule_info()
    
    # Schedule jobs
    # Episodization: Every 6 hours
    schedule.every(6).hours.do(run_episodization_job)
    
    # Instance Migration: Daily at 2 AM
    schedule.every().day.at("02:00").do(run_migration_job)
    
    # Run episodization immediately on startup
    print("\nRunning initial episodization job...")
    run_episodization_job()
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\n✓ Scheduler stopped by user")
        sys.exit(0)

if __name__ == '__main__':
    main()
