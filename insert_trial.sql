-- Insert the 5555 test trials using the REAL organization ID already in production DB
-- org_id = 10000000-0000-0000-0000-000000000001 (Themison Dev Org)

INSERT INTO trials (id, name, description, phase, location, sponsor, status, organization_id)
VALUES
  ('55555555-5555-5555-5555-555555555555', 'Oncology Phase III',
   'Randomized double-blind study of Drug X vs placebo in advanced NSCLC',
   'Phase 3', 'New York, USA', 'Acme Pharma', 'active',
   '10000000-0000-0000-0000-000000000001'),
  ('55555555-5555-5555-5555-555555555556', 'Cardiology Phase II',
   'Open-label study of Drug Y in heart failure patients',
   'Phase 2', 'London, UK', 'Acme Pharma', 'planning',
   '10000000-0000-0000-0000-000000000001'),
  ('55555555-5555-5555-5555-555555555557', 'Neurology Phase I',
   'First-in-human dose-escalation study of Drug Z',
   'Phase 1', 'Berlin, Germany', 'Acme Pharma', 'planning',
   '10000000-0000-0000-0000-000000000001')
ON CONFLICT (id) DO NOTHING;

-- Confirm they are now in the DB
SELECT id, name, status FROM trials;
