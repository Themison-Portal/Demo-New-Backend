-- Query existing data to find what IDs are already there
SELECT 'admin' as tbl, id::text, email as name FROM themison_admins LIMIT 5;
SELECT 'org' as tbl, id::text, name FROM organizations LIMIT 5;
SELECT 'profile' as tbl, id::text, email as name FROM profiles LIMIT 5;
SELECT 'member' as tbl, id::text, email as name FROM members LIMIT 5;
SELECT 'trial' as tbl, id::text, name FROM trials LIMIT 10;
