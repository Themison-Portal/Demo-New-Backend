"""
Data Export Script - Export all data from old Supabase project

This script exports all application data from the old Supabase project
to JSON files that can be imported into the new project.

Usage:
    python scripts/migration/export_data.py

Environment Variables Required:
    OLD_SUPABASE_DB_URL - PostgreSQL connection string for OLD project

Example:
    set OLD_SUPABASE_DB_URL=postgresql://postgres.gpfyejxokywdkudkeywv:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
    python scripts/migration/export_data.py
"""

import asyncio
import json
import os
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import asyncpg

# Output directory for exported data
EXPORT_DIR = Path(__file__).parent / "exported_data"

# Tables to export in dependency order (parent tables first)
TABLES_TO_EXPORT = [
    # Core tables (no foreign keys to other app tables)
    "organizations",
    "profiles",  # Users table (references auth.users)

    # Organization-related
    "organization_members",

    # Trials
    "clinical_trials",
    "trial_team_members",

    # Patients
    "patients",

    # Documents
    "trial_documents",
    "document_chunks_docling",

    # Chat
    "chat_sessions",
    "chat_messages",
    "chat_document_links",

    # Cache (optional - can be regenerated)
    "semantic_cache_responses",
]


def json_serializer(obj):
    """Custom JSON serializer for non-standard types."""
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, dict, list)):
        # Handle numpy arrays or other iterables
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


async def export_table(conn: asyncpg.Connection, table_name: str) -> list:
    """Export all rows from a table."""
    try:
        # Get all rows
        rows = await conn.fetch(f'SELECT * FROM "{table_name}"')

        # Convert to list of dicts
        data = [dict(row) for row in rows]

        print(f"  Exported {len(data)} rows from {table_name}")
        return data
    except asyncpg.UndefinedTableError:
        print(f"  Table {table_name} does not exist - skipping")
        return []
    except Exception as e:
        print(f"  Error exporting {table_name}: {e}")
        return []


async def export_all_data():
    """Export all data from old Supabase project."""

    # Get connection string from environment
    db_url = os.environ.get("OLD_SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: OLD_SUPABASE_DB_URL environment variable not set")
        print("\nSet it to your OLD Supabase project's database URL:")
        print("  set OLD_SUPABASE_DB_URL=postgresql://postgres.gpfyejxokywdkudkeywv:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")
        return

    # Create export directory
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to old database...")
    print(f"Export directory: {EXPORT_DIR}")

    try:
        conn = await asyncpg.connect(db_url)
        print("Connected successfully!\n")

        export_data = {}
        export_metadata = {
            "exported_at": datetime.utcnow().isoformat(),
            "source_project": "gpfyejxokywdkudkeywv",
            "tables": {}
        }

        print("Exporting tables...")
        for table in TABLES_TO_EXPORT:
            data = await export_table(conn, table)
            export_data[table] = data
            export_metadata["tables"][table] = len(data)

        # Save each table to separate JSON file
        print("\nSaving to files...")
        for table, data in export_data.items():
            if data:  # Only save if there's data
                file_path = EXPORT_DIR / f"{table}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, default=json_serializer, indent=2, ensure_ascii=False)
                print(f"  Saved {file_path.name}")

        # Save metadata
        metadata_path = EXPORT_DIR / "_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(export_metadata, f, indent=2)
        print(f"  Saved _metadata.json")

        await conn.close()

        print("\n" + "="*50)
        print("EXPORT COMPLETE!")
        print("="*50)
        print(f"\nExported data saved to: {EXPORT_DIR}")
        print("\nNext steps:")
        print("1. Review exported JSON files")
        print("2. Run export_auth_users.py to export auth users")
        print("3. Run import_data.py to import into new project")

    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(export_all_data())
