"""
Auth Users Export Script - Export auth.users from old Supabase project

This script exports auth users from the old Supabase project.
Supabase auth users are stored in the `auth` schema which requires
special handling.

Usage:
    python scripts/migration/export_auth_users.py

Environment Variables Required:
    OLD_SUPABASE_DB_URL - PostgreSQL connection string for OLD project

Note: You need the database password (not pooler password) to access auth schema.
Get it from: Supabase Dashboard > Settings > Database > Connection string > URI

Example:
    $env:OLD_SUPABASE_DB_URL = "postgresql://postgres:PASSWORD@db.gpfyejxokywdkudkeywv.supabase.co:5432/postgres"
    python scripts/migration/export_auth_users.py
"""

import json
import os
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import psycopg2
from psycopg2.extras import RealDictCursor

# Output directory for exported data
EXPORT_DIR = Path(__file__).parent / "exported_data"


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
    if isinstance(obj, memoryview):
        return bytes(obj).hex()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def export_auth_users():
    """Export auth users from old Supabase project."""

    # Get connection string from environment
    db_url = os.environ.get("OLD_SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: OLD_SUPABASE_DB_URL environment variable not set")
        print("\nSet it to your OLD Supabase project's DIRECT database URL (not pooler):")
        print('  $env:OLD_SUPABASE_DB_URL = "postgresql://postgres:PASSWORD@db.gpfyejxokywdkudkeywv.supabase.co:5432/postgres"')
        print("\nGet the password from: Supabase Dashboard > Settings > Database > Connection string")
        return

    # Create export directory
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Debug: show what we're connecting to
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database: {parsed.path}")
    print(f"Connecting to old database (auth schema)...")

    try:
        # Use psycopg2 which handles IPv6 better on Windows
        conn = psycopg2.connect(db_url)
        print("Connected successfully!\n")

        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Export auth.users table
        print("Exporting auth.users...")
        users_query = """
            SELECT
                id,
                email,
                encrypted_password,
                email_confirmed_at,
                invited_at,
                confirmation_token,
                confirmation_sent_at,
                recovery_token,
                recovery_sent_at,
                email_change_token_new,
                email_change,
                email_change_sent_at,
                last_sign_in_at,
                raw_app_meta_data,
                raw_user_meta_data,
                is_super_admin,
                created_at,
                updated_at,
                phone,
                phone_confirmed_at,
                phone_change,
                phone_change_token,
                phone_change_sent_at,
                email_change_token_current,
                email_change_confirm_status,
                banned_until,
                reauthentication_token,
                reauthentication_sent_at,
                is_sso_user,
                deleted_at,
                role,
                is_anonymous
            FROM auth.users
            WHERE deleted_at IS NULL
        """

        try:
            cur.execute(users_query)
            users_data = [dict(row) for row in cur.fetchall()]
            print(f"  Found {len(users_data)} users")
        except psycopg2.errors.UndefinedTable:
            print("  ERROR: Cannot access auth.users table. Make sure you're using direct connection (not pooler).")
            users_data = []
        except psycopg2.errors.InsufficientPrivilege:
            print("  ERROR: Insufficient privileges to access auth schema.")
            print("  Make sure you're using the database password, not the service role key.")
            users_data = []

        # Export auth.identities (for OAuth providers)
        print("Exporting auth.identities...")
        try:
            identities_query = """
                SELECT
                    id,
                    provider_id,
                    user_id,
                    identity_data,
                    provider,
                    last_sign_in_at,
                    created_at,
                    updated_at
                FROM auth.identities
            """
            cur.execute(identities_query)
            identities_data = [dict(row) for row in cur.fetchall()]
            print(f"  Found {len(identities_data)} identities")
        except Exception as e:
            print(f"  Warning: Could not export identities: {e}")
            identities_data = []

        cur.close()
        conn.close()

        # Save to files
        print("\nSaving to files...")

        if users_data:
            users_path = EXPORT_DIR / "auth_users.json"
            with open(users_path, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, default=json_serializer, indent=2, ensure_ascii=False)
            print(f"  Saved auth_users.json ({len(users_data)} users)")

        if identities_data:
            identities_path = EXPORT_DIR / "auth_identities.json"
            with open(identities_path, 'w', encoding='utf-8') as f:
                json.dump(identities_data, f, default=json_serializer, indent=2, ensure_ascii=False)
            print(f"  Saved auth_identities.json ({len(identities_data)} identities)")

        print("\n" + "="*50)
        print("AUTH EXPORT COMPLETE!")
        print("="*50)

        if users_data:
            print(f"\nExported {len(users_data)} auth users")
            print("\nIMPORTANT NOTES:")
            print("1. User passwords are hashed - users will keep their existing passwords")
            print("2. OAuth identities are exported separately")
            print("3. Run import_auth_users.py to import into new project")
        else:
            print("\nNo users exported. Check your connection string and permissions.")

    except psycopg2.OperationalError as e:
        if "could not translate host name" in str(e) or "getaddrinfo" in str(e):
            print(f"ERROR: Cannot resolve hostname. Your network may not support IPv6.")
            print("\nTry these alternatives:")
            print("1. Use the Supabase pooler connection (but you'll need to export via SQL Editor)")
            print("2. Connect from a different network that supports IPv6")
            print("3. Use Supabase CLI: npx supabase db dump --db-url <url> > backup.sql")
        else:
            print(f"ERROR: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    export_auth_users()
