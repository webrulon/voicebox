"""
Database migration script to add engine and model_type columns to generations table.

Run this once to update existing databases:
    python -m backend.migrations.add_engine_field
"""

import sqlite3
import os
from pathlib import Path


def migrate():
    """Add engine and model_type columns to generations table if they don't exist."""
    # Get data directory
    data_dir = os.environ.get("VOICEBOX_DATA_DIR")
    if data_dir:
        db_path = Path(data_dir) / "voicebox.db"
    else:
        db_path = Path.cwd() / "data" / "voicebox.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}, skipping migration")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(generations)")
    columns = [row[1] for row in cursor.fetchall()]

    columns_added = []

    # Add engine column if it doesn't exist
    if 'engine' not in columns:
        print("Adding engine column to generations table...")
        cursor.execute("ALTER TABLE generations ADD COLUMN engine TEXT")
        columns_added.append('engine')
    else:
        print("engine column already exists, skipping")

    # Add model_type column if it doesn't exist
    if 'model_type' not in columns:
        print("Adding model_type column to generations table...")
        cursor.execute("ALTER TABLE generations ADD COLUMN model_type TEXT")
        columns_added.append('model_type')
    else:
        print("model_type column already exists, skipping")

    if columns_added:
        conn.commit()
        print(f"Migration completed successfully! Added columns: {', '.join(columns_added)}")
    else:
        print("Migration completed successfully! All columns already exist.")

    conn.close()


if __name__ == "__main__":
    migrate()
