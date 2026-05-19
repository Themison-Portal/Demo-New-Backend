"""
Auth Users Import Script - Import auth.users into new Supabase project

This script imports auth users from exported JSON files into the new Supabase project.
It preserves user IDs, passwords, and metadata.

Usage:
    python scripts/migration/import_auth_users.py

Environment Variables Required:
    NEW_SUPABASE_DB_URL - PostgreSQL DIRECT connection string for NEW project

Note: Must use DIRECT connection (not pooler) to access auth schema.
Get it from: Supabase Dashboard > Settings > Database > Connection string > URI

Example:
    set NEW_SUPABASE_DB_URL=postgresql://postgres:PASSWORD@db.nidpneaqxghqueniodus.supabase.co:5432/postgres
    python scripts/migration/import_auth_users.py
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import UUID

import asyncpg

# Input directory for exported data
EXPORT_DIR = Path(__file__).parent / "exported_data"


def parse_datetime(value):
    """Parse datetime from ISO string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except:
        return None


async def import_auth_users():
    """Import auth users into new Supabase project."""

    # Get connection string from environment
    db_url = os.environ.get("NEW_SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: NEW_SUPABASE_DB_URL environment variable not set")
        print("\nSet it to your NEW Supabase project's DIRECT database URL:")
        print("  set NEW_SUPABASE_DB_URL=postgresql://postgres:PASSWORD@db.nidpneaqxghqueniodus.supabase.co:5432/postgres")
        return

    # Load exported users
    users_path = EXPORT_DIR / "auth_users.json"
    if not users_path.exists():
        print(f"ERROR: {users_path} not found")
        print("Run export_auth_users.py first to export users from old project")
        return

    with open(users_path, 'r', encoding='utf-8') as f:
        users = json.load(f)

    print(f"Loaded {len(users)} users from {users_path}")

    # Load identities if exists
    identities_path = EXPORT_DIR / "auth_identities.json"
    identities = []
    if identities_path.exists():
        with open(identities_path, 'r', encoding='utf-8') as f:
            identities = json.load(f)
        print(f"Loaded {len(identities)} identities from {identities_path}")

    print(f"\nConnecting to new database...")

    try:
        conn = await asyncpg.connect(db_url)
        print("Connected successfully!\n")

        # Check existing users to avoid conflicts
        existing = await conn.fetch("SELECT id, email FROM auth.users")
        existing_ids = {str(row['id']) for row in existing}
        existing_emails = {row['email'].lower() for row in existing if row['email']}

        print(f"Found {len(existing_ids)} existing users in new database")

        # Filter out users that already exist
        users_to_import = []
        skipped_users = []
        for user in users:
            user_id = user['id']
            email = user.get('email', '').lower() if user.get('email') else None

            if user_id in existing_ids:
                skipped_users.append(f"  - {email or user_id} (ID exists)")
            elif email and email in existing_emails:
                skipped_users.append(f"  - {email} (email exists)")
            else:
                users_to_import.append(user)

        if skipped_users:
            print(f"\nSkipping {len(skipped_users)} users (already exist):")
            for msg in skipped_users[:10]:  # Show first 10
                print(msg)
            if len(skipped_users) > 10:
                print(f"  ... and {len(skipped_users) - 10} more")

        if not users_to_import:
            print("\nNo new users to import!")
            await conn.close()
            return

        print(f"\nImporting {len(users_to_import)} users...")

        # Import users
        imported = 0
        errors = []

        for user in users_to_import:
            try:
                # Prepare values with proper type handling
                user_id = UUID(user['id'])
                email = user.get('email')
                encrypted_password = user.get('encrypted_password')
                email_confirmed_at = parse_datetime(user.get('email_confirmed_at'))
                last_sign_in_at = parse_datetime(user.get('last_sign_in_at'))
                created_at = parse_datetime(user.get('created_at')) or datetime.utcnow()
                updated_at = parse_datetime(user.get('updated_at')) or datetime.utcnow()

                # raw_app_meta_data and raw_user_meta_data are JSONB
                raw_app_meta_data = user.get('raw_app_meta_data') or {}
                raw_user_meta_data = user.get('raw_user_meta_data') or {}

                # Ensure provider is set in app_meta_data
                if 'provider' not in raw_app_meta_data:
                    raw_app_meta_data['provider'] = 'email'
                if 'providers' not in raw_app_meta_data:
                    raw_app_meta_data['providers'] = ['email']

                role = user.get('role', 'authenticated')
                is_anonymous = user.get('is_anonymous', False)

                # Insert user
                await conn.execute("""
                    INSERT INTO auth.users (
                        id, instance_id, email, encrypted_password,
                        email_confirmed_at, last_sign_in_at,
                        raw_app_meta_data, raw_user_meta_data,
                        created_at, updated_at, role,
                        aud, confirmation_token, recovery_token,
                        email_change_token_new, email_change,
                        is_anonymous
                    ) VALUES (
                        $1, '00000000-0000-0000-0000-000000000000', $2, $3,
                        $4, $5,
                        $6, $7,
                        $8, $9, $10,
                        'authenticated', '', '',
                        '', '',
                        $11
                    )
                """,
                    user_id, email, encrypted_password,
                    email_confirmed_at, last_sign_in_at,
                    json.dumps(raw_app_meta_data), json.dumps(raw_user_meta_data),
                    created_at, updated_at, role,
                    is_anonymous
                )

                imported += 1
                if imported % 10 == 0:
                    print(f"  Imported {imported}/{len(users_to_import)} users...")

            except Exception as e:
                errors.append(f"  - {user.get('email', user['id'])}: {str(e)[:100]}")

        print(f"\nImported {imported} users successfully")

        if errors:
            print(f"\n{len(errors)} errors occurred:")
            for err in errors[:10]:
                print(err)
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        # Import identities (for email provider)
        if identities:
            print(f"\nImporting {len(identities)} identities...")
            identity_imported = 0

            for identity in identities:
                try:
                    # Only import if user was imported
                    user_id = identity['user_id']
                    if user_id not in [str(u['id']) for u in users_to_import]:
                        continue

                    await conn.execute("""
                        INSERT INTO auth.identities (
                            id, provider_id, user_id, identity_data,
                            provider, last_sign_in_at, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        identity['id'],
                        identity.get('provider_id', identity['user_id']),
                        UUID(identity['user_id']),
                        json.dumps(identity.get('identity_data', {})),
                        identity.get('provider', 'email'),
                        parse_datetime(identity.get('last_sign_in_at')),
                        parse_datetime(identity.get('created_at')) or datetime.utcnow(),
                        parse_datetime(identity.get('updated_at')) or datetime.utcnow()
                    )
                    identity_imported += 1
                except Exception as e:
                    pass  # Silently skip identity errors

            print(f"  Imported {identity_imported} identities")

        await conn.close()

        print("\n" + "="*50)
        print("AUTH IMPORT COMPLETE!")
        print("="*50)
        print(f"\nImported {imported} users into new Supabase project")
        print("\nUsers can now log in with their existing credentials!")
        print("\nNext: Run import_data.py to import application data")

    except asyncpg.InvalidPasswordError:
        print("ERROR: Invalid password. Make sure you're using the correct database password.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(import_auth_users())
