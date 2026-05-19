"""
Data Import Script - Import all data into new Supabase project

This script imports application data from exported JSON files into
the new Supabase project. It handles foreign key dependencies by
importing tables in the correct order.

Usage:
    python scripts/migration/import_data.py

Environment Variables Required:
    NEW_SUPABASE_DB_URL - PostgreSQL connection string for NEW project

Note: Auth users must be imported FIRST (run import_auth_users.py)

Example:
    set NEW_SUPABASE_DB_URL=postgresql://postgres.nidpneaqxghqueniodus:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
    python scripts/migration/import_data.py
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

import asyncpg

# Input directory for exported data
EXPORT_DIR = Path(__file__).parent / "exported_data"

# Tables to import in dependency order (matches export order)
TABLES_TO_IMPORT = [
    "organizations",
    "profiles",
    "organization_members",
    "clinical_trials",
    "trial_team_members",
    "patients",
    "trial_documents",
    "document_chunks_docling",
    "chat_sessions",
    "chat_messages",
    "chat_document_links",
    "semantic_cache_responses",
]


def convert_value(value: Any, column_type: str) -> Any:
    """Convert JSON value to appropriate PostgreSQL type."""
    if value is None:
        return None

    if 'uuid' in column_type.lower():
        return UUID(value) if isinstance(value, str) else value

    if 'timestamp' in column_type.lower() or 'date' in column_type.lower():
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return None
        return value

    if 'json' in column_type.lower():
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    if 'vector' in column_type.lower():
        # Handle vector embeddings
        if isinstance(value, list):
            return value
        return None

    if 'boolean' in column_type.lower():
        return bool(value)

    if 'integer' in column_type.lower() or 'bigint' in column_type.lower():
        return int(value) if value is not None else None

    return value


async def get_table_columns(conn: asyncpg.Connection, table_name: str) -> Dict[str, str]:
    """Get column names and types for a table."""
    query = """
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position
    """
    rows = await conn.fetch(query, table_name)
    return {row['column_name']: row['udt_name'] for row in rows}


async def import_table(conn: asyncpg.Connection, table_name: str, data: List[Dict]) -> tuple:
    """Import data into a table. Returns (imported_count, skipped_count, error_count)."""
    if not data:
        return 0, 0, 0

    # Get table columns
    columns_info = await get_table_columns(conn, table_name)
    if not columns_info:
        print(f"    WARNING: Table {table_name} not found - skipping")
        return 0, len(data), 0

    imported = 0
    skipped = 0
    errors = 0

    for row in data:
        try:
            # Filter to only columns that exist in the target table
            # and are present in the data
            available_columns = [col for col in row.keys() if col in columns_info]

            if not available_columns:
                skipped += 1
                continue

            # Build INSERT statement
            columns = ', '.join(f'"{col}"' for col in available_columns)
            placeholders = ', '.join(f'${i+1}' for i in range(len(available_columns)))

            # Convert values
            values = []
            for col in available_columns:
                col_type = columns_info.get(col, 'text')
                values.append(convert_value(row[col], col_type))

            # Insert with ON CONFLICT DO NOTHING to handle duplicates
            insert_sql = f"""
                INSERT INTO "{table_name}" ({columns})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """

            result = await conn.execute(insert_sql, *values)

            if 'INSERT 0 1' in result:
                imported += 1
            else:
                skipped += 1  # Duplicate or conflict

        except Exception as e:
            errors += 1
            if errors <= 3:  # Only show first 3 errors per table
                print(f"    Error importing row: {str(e)[:100]}")

    return imported, skipped, errors


async def import_all_data():
    """Import all data into new Supabase project."""

    # Get connection string from environment
    db_url = os.environ.get("NEW_SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: NEW_SUPABASE_DB_URL environment variable not set")
        print("\nSet it to your NEW Supabase project's database URL:")
        print("  set NEW_SUPABASE_DB_URL=postgresql://postgres.nidpneaqxghqueniodus:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")
        return

    # Check export directory
    if not EXPORT_DIR.exists():
        print(f"ERROR: Export directory not found: {EXPORT_DIR}")
        print("Run export_data.py first to export data from old project")
        return

    # Check for metadata file
    metadata_path = EXPORT_DIR / "_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        print(f"Loading export from: {metadata.get('exported_at', 'unknown date')}")
        print(f"Source project: {metadata.get('source_project', 'unknown')}\n")

    print(f"Connecting to new database...")

    try:
        conn = await asyncpg.connect(db_url)
        print("Connected successfully!\n")

        total_imported = 0
        total_skipped = 0
        total_errors = 0

        print("Importing tables in dependency order...\n")

        for table_name in TABLES_TO_IMPORT:
            file_path = EXPORT_DIR / f"{table_name}.json"

            if not file_path.exists():
                print(f"  {table_name}: No data file found - skipping")
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not data:
                print(f"  {table_name}: Empty - skipping")
                continue

            print(f"  {table_name}: Importing {len(data)} rows...")
            imported, skipped, errors = await import_table(conn, table_name, data)

            print(f"    -> Imported: {imported}, Skipped: {skipped}, Errors: {errors}")

            total_imported += imported
            total_skipped += skipped
            total_errors += errors

        await conn.close()

        print("\n" + "="*50)
        print("DATA IMPORT COMPLETE!")
        print("="*50)
        print(f"\nTotal imported: {total_imported}")
        print(f"Total skipped (duplicates): {total_skipped}")
        print(f"Total errors: {total_errors}")

        if total_errors > 0:
            print("\nSome errors occurred. Review the output above.")
            print("Common issues:")
            print("  - Foreign key violations (import auth users first)")
            print("  - Data type mismatches")
            print("  - Missing columns in new schema")

        print("\nNext steps:")
        print("1. Run the embedding schema migrations (if not already done)")
        print("2. Update tsvector columns: UPDATE document_chunks_docling SET content_tsv = to_tsvector('english', content);")
        print("3. Test your application!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(import_all_data())
