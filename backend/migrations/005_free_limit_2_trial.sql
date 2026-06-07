-- Change free plan from 5 analyses → 2 (trial model for India market)
-- Users get 2 free AI analyses, then must upgrade to Pro

ALTER TABLE usage_quotas ALTER COLUMN analyses_limit SET DEFAULT 2;

UPDATE usage_quotas
SET analyses_limit = 2
WHERE user_id IN (
  SELECT id FROM users WHERE plan = 'free'
)
AND analyses_limit <= 5;
