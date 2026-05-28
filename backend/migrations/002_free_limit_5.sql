-- Increase free plan analyses limit from 3 → 5
-- Only updates free users (plan = 'free' or no active pro subscription)
-- Run once in Supabase SQL editor.

ALTER TABLE usage_quotas ALTER COLUMN analyses_limit SET DEFAULT 5;

UPDATE usage_quotas
SET analyses_limit = 5
WHERE user_id IN (
  SELECT id FROM users WHERE plan = 'free'
)
AND analyses_limit = 3;
