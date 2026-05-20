# Legacy SQL Migrations

These are the original raw SQL migration files from the old platform.
They are kept here for reference and historical context only.

Going forward all DB changes are managed by Alembic:
- Migration files live in `alembic/versions/`
- Run migrations with: `alembic -c alembic.ini upgrade head`
- Never run these SQL files directly on the new platform DB
