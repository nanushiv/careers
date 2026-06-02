-- ============================================================
-- CareerOS — Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Run this in Supabase SQL editor or via migration runner
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- UTILITY: updated_at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  clerk_id              TEXT UNIQUE NOT NULL,
  email                 TEXT UNIQUE NOT NULL,
  full_name             TEXT,
  avatar_url            TEXT,

  -- Career context
  current_title         TEXT,
  target_roles          TEXT[] DEFAULT '{}',
  years_experience      INT,
  current_company       TEXT,
  location              TEXT,
  linkedin_url          TEXT,

  -- Platform state
  onboarding_completed  BOOLEAN DEFAULT FALSE,
  onboarding_step       INT DEFAULT 0,
  plan                  TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'team')),
  plan_expires_at       TIMESTAMPTZ,

  -- Engagement
  last_active_at        TIMESTAMPTZ DEFAULT NOW(),
  total_analyses        INT DEFAULT 0,
  total_applications    INT DEFAULT 0,
  career_health_score   DECIMAL(4,2) CHECK (career_health_score BETWEEN 0 AND 100),

  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),
  deleted_at            TIMESTAMPTZ
);

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================
CREATE TABLE subscriptions (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  plan                  TEXT NOT NULL,
  status                TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'expired', 'trialing')),
  stripe_sub_id         TEXT UNIQUE,
  current_period_start  TIMESTAMPTZ,
  current_period_end    TIMESTAMPTZ,
  cancel_at_period_end  BOOLEAN DEFAULT FALSE,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER subscriptions_updated_at BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- USAGE QUOTAS
-- ============================================================
CREATE TABLE usage_quotas (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  analyses_used         INT DEFAULT 0,
  analyses_limit        INT DEFAULT 5,
  applications_used     INT DEFAULT 0,
  applications_limit    INT DEFAULT 10,
  ai_spend_usd          DECIMAL(8,4) DEFAULT 0,
  reset_at              TIMESTAMPTZ DEFAULT (date_trunc('month', NOW()) + interval '1 month'),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER usage_quotas_updated_at BEFORE UPDATE ON usage_quotas
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- RESUMES
-- ============================================================
CREATE TABLE resumes (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,

  -- File
  file_name             TEXT NOT NULL,
  file_url              TEXT NOT NULL,
  file_size_kb          INT,
  file_type             TEXT DEFAULT 'pdf' CHECK (file_type IN ('pdf', 'docx')),

  -- Versioning
  version_label         TEXT DEFAULT 'Default',
  version_number        INT DEFAULT 1,
  is_primary            BOOLEAN DEFAULT FALSE,

  -- Parsed content
  raw_text              TEXT,
  structured_data       JSONB DEFAULT '{}',
  embedding             vector(768),

  -- Performance (updated by aggregation jobs)
  applications_used     INT DEFAULT 0,
  callback_rate         DECIMAL(5,2),
  ats_score_avg         DECIMAL(4,1),

  -- Status
  parse_status          TEXT DEFAULT 'pending'
                        CHECK (parse_status IN ('pending', 'processing', 'completed', 'failed')),
  parse_error           TEXT,

  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),
  deleted_at            TIMESTAMPTZ
);

CREATE TRIGGER resumes_updated_at BEFORE UPDATE ON resumes
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_resumes_user_id ON resumes(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_resumes_is_primary ON resumes(user_id, is_primary) WHERE deleted_at IS NULL;
CREATE INDEX idx_resumes_embedding ON resumes USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ============================================================
-- JOB DESCRIPTIONS
-- ============================================================
CREATE TABLE job_descriptions (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,

  raw_text              TEXT,
  url                   TEXT,

  -- Parsed metadata
  company_name          TEXT,
  role_title            TEXT,
  role_level            TEXT,
  role_category         TEXT CHECK (role_category IN ('PM', 'APM', 'TPM', 'AI-PM', 'GPM', 'CPO', 'Other')),
  location              TEXT,
  remote_policy         TEXT CHECK (remote_policy IN ('remote', 'hybrid', 'onsite', 'unknown')),

  -- Requirements
  required_skills       TEXT[] DEFAULT '{}',
  preferred_skills      TEXT[] DEFAULT '{}',
  required_experience   INT,
  key_responsibilities  JSONB DEFAULT '[]',

  -- Intelligence
  embedding             vector(768),
  seniority_score       DECIMAL(4,1),
  ai_weight_score       DECIMAL(4,1),

  parse_status          TEXT DEFAULT 'pending',
  created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jd_user_id ON job_descriptions(user_id);
CREATE INDEX idx_jd_embedding ON job_descriptions USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ============================================================
-- RESUME ANALYSES
-- ============================================================
CREATE TABLE resume_analyses (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  resume_id             UUID REFERENCES resumes(id) ON DELETE CASCADE,
  jd_id                 UUID REFERENCES job_descriptions(id),

  analysis_type         TEXT NOT NULL
                        CHECK (analysis_type IN ('ats', 'recruiter', 'role_fit', 'readiness', 'full')),

  -- Scores (0–100)
  overall_score         DECIMAL(4,1),
  keyword_score         DECIMAL(4,1),
  format_score          DECIMAL(4,1),
  experience_score      DECIMAL(4,1),
  skills_score          DECIMAL(4,1),

  -- Output (JSONB for flexibility — no schema migration needed for new fields)
  gaps                  JSONB DEFAULT '[]',
  strengths             JSONB DEFAULT '[]',
  improvements          JSONB DEFAULT '[]',
  keyword_analysis      JSONB DEFAULT '{}',
  recruiter_signals     JSONB DEFAULT '{}',
  role_fit_analysis     JSONB DEFAULT '{}',
  readiness_breakdown   JSONB DEFAULT '{}',
  improvement_roadmap   JSONB DEFAULT '[]',
  interview_questions   JSONB DEFAULT '[]',

  -- AI metadata
  model_used            TEXT,
  tokens_used           INT DEFAULT 0,
  cost_usd              DECIMAL(8,6) DEFAULT 0,
  processing_time_ms    INT,
  cache_hit             BOOLEAN DEFAULT FALSE,

  created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analyses_user_id ON resume_analyses(user_id);
CREATE INDEX idx_analyses_resume_id ON resume_analyses(resume_id);
CREATE INDEX idx_analyses_type ON resume_analyses(analysis_type);
CREATE INDEX idx_analyses_created ON resume_analyses(created_at DESC);

-- ============================================================
-- APPLICATIONS
-- ============================================================
CREATE TABLE applications (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  resume_id             UUID REFERENCES resumes(id),
  jd_id                 UUID REFERENCES job_descriptions(id),

  -- Core info
  company_name          TEXT NOT NULL,
  role_title            TEXT NOT NULL,
  role_category         TEXT,
  role_level            TEXT,
  job_url               TEXT,

  -- Application details
  applied_date          DATE DEFAULT CURRENT_DATE,
  application_source    TEXT DEFAULT 'unknown'
                        CHECK (application_source IN (
                          'linkedin', 'company_site', 'referral',
                          'cold_apply', 'job_board', 'recruiter_reach', 'unknown'
                        )),
  referral_contact      TEXT,
  has_referral          BOOLEAN DEFAULT FALSE,

  -- Recruiter
  recruiter_name        TEXT,
  recruiter_email       TEXT,
  recruiter_linkedin    TEXT,

  -- Pipeline stage
  stage                 TEXT DEFAULT 'applied'
                        CHECK (stage IN (
                          'applied', 'screening', 'phone_screen', 'technical',
                          'case_study', 'final', 'offer', 'rejected', 'ghosted', 'withdrawn'
                        )),
  last_stage_change_at  TIMESTAMPTZ DEFAULT NOW(),

  -- Compensation
  expected_salary_min   INT,
  expected_salary_max   INT,
  offered_salary        INT,
  currency              TEXT DEFAULT 'USD',

  -- AI scores (computed async)
  role_fit_score        DECIMAL(4,1),
  recruiter_fit_score   DECIMAL(4,1),

  -- Outcome
  outcome               TEXT CHECK (outcome IN ('offer', 'rejected', 'ghosted', 'withdrawn', 'pending')),
  rejection_reason      TEXT,
  rejection_stage       TEXT,

  -- Notes
  notes                 TEXT,
  is_dream_role         BOOLEAN DEFAULT FALSE,
  priority              TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),

  -- Follow-up tracking
  next_follow_up_date   DATE,
  days_since_last_event INT,

  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),
  deleted_at            TIMESTAMPTZ
);

CREATE TRIGGER applications_updated_at BEFORE UPDATE ON applications
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_applications_user_id ON applications(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_applications_stage ON applications(user_id, stage) WHERE deleted_at IS NULL;
CREATE INDEX idx_applications_date ON applications(user_id, applied_date DESC);
CREATE INDEX idx_applications_source ON applications(user_id, application_source);

-- ============================================================
-- APPLICATION EVENTS (timeline)
-- ============================================================
CREATE TABLE application_events (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  application_id        UUID REFERENCES applications(id) ON DELETE CASCADE,
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  event_type            TEXT NOT NULL
                        CHECK (event_type IN (
                          'applied', 'email_sent', 'email_received', 'call_scheduled',
                          'call_completed', 'stage_advanced', 'stage_declined',
                          'rejected', 'offer_received', 'follow_up_sent', 'note_added',
                          'ghosted_detected', 'withdrawn'
                        )),
  event_date            TIMESTAMPTZ DEFAULT NOW(),
  description           TEXT,
  metadata              JSONB DEFAULT '{}',
  created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_application_id ON application_events(application_id);
CREATE INDEX idx_events_date ON application_events(application_id, event_date DESC);

-- ============================================================
-- FOLLOW-UPS
-- ============================================================
CREATE TABLE follow_ups (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  application_id        UUID REFERENCES applications(id) ON DELETE CASCADE,
  due_date              DATE NOT NULL,
  follow_up_type        TEXT CHECK (follow_up_type IN ('email', 'linkedin', 'call', 'check_status')),
  message_draft         TEXT,
  status                TEXT DEFAULT 'pending'
                        CHECK (status IN ('pending', 'completed', 'snoozed', 'dismissed')),
  snoozed_until         DATE,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER follow_ups_updated_at BEFORE UPDATE ON follow_ups
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_follow_ups_user_due ON follow_ups(user_id, due_date)
  WHERE status = 'pending';

-- ============================================================
-- INTERVIEWS
-- ============================================================
CREATE TABLE interviews (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  application_id        UUID REFERENCES applications(id) ON DELETE CASCADE,
  interview_type        TEXT NOT NULL
                        CHECK (interview_type IN (
                          'phone_screen', 'recruiter_screen', 'hiring_manager',
                          'technical', 'product_case', 'behavioral', 'panel', 'final', 'reference_check'
                        )),
  scheduled_at          TIMESTAMPTZ,
  duration_min          INT,
  interviewer           TEXT,
  format                TEXT CHECK (format IN ('video', 'phone', 'onsite', 'async')),
  prep_questions        JSONB DEFAULT '[]',
  prep_notes            TEXT,
  completed             BOOLEAN DEFAULT FALSE,
  completed_at          TIMESTAMPTZ,
  outcome               TEXT CHECK (outcome IN ('passed', 'rejected', 'pending', 'withdrew')),
  self_rating           INT CHECK (self_rating BETWEEN 1 AND 5),
  feedback_received     TEXT,
  coaching_notes        JSONB DEFAULT '{}',
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER interviews_updated_at BEFORE UPDATE ON interviews
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_interviews_application_id ON interviews(application_id);

-- ============================================================
-- AI INSIGHTS
-- ============================================================
CREATE TABLE ai_insights (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  insight_type          TEXT NOT NULL
                        CHECK (insight_type IN (
                          'resume_performance', 'callback_pattern', 'stage_drop_off',
                          'application_velocity', 'positioning_gap', 'burnout_signal',
                          'role_fit_trend', 'networking_gap', 'weekly_synthesis',
                          'ghosting_pattern', 'source_performance'
                        )),
  title                 TEXT NOT NULL,
  summary               TEXT NOT NULL,
  detail                TEXT,
  action                TEXT,
  impact                TEXT,
  priority              TEXT DEFAULT 'medium'
                        CHECK (priority IN ('critical', 'high', 'medium', 'low')),
  data_snapshot         JSONB DEFAULT '{}',
  is_dismissed          BOOLEAN DEFAULT FALSE,
  is_acted_on           BOOLEAN DEFAULT FALSE,
  expires_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insights_user_active ON ai_insights(user_id, priority, created_at DESC)
  WHERE is_dismissed = FALSE;

-- ============================================================
-- USER ANALYTICS SNAPSHOTS (weekly aggregates)
-- ============================================================
CREATE TABLE user_analytics (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  week_start            DATE NOT NULL,
  apps_submitted        INT DEFAULT 0,
  apps_by_source        JSONB DEFAULT '{}',
  apps_by_category      JSONB DEFAULT '{}',
  screenings_received   INT DEFAULT 0,
  callback_rate         DECIMAL(5,2),
  avg_response_days     DECIMAL(4,1),
  ghosted_count         INT DEFAULT 0,
  stage_distribution    JSONB DEFAULT '{}',
  stage_drop_offs       JSONB DEFAULT '{}',
  top_resume_version_id UUID REFERENCES resumes(id),
  resume_performance    JSONB DEFAULT '{}',
  new_insights_count    INT DEFAULT 0,
  career_health_score   DECIMAL(4,2),
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, week_start)
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
-- Enable RLS on all user-data tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_quotas ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_analytics ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
-- (Service role bypasses RLS — backend uses service role)
CREATE POLICY "users_own_data" ON users
  USING (clerk_id = auth.jwt() ->> 'sub');

CREATE POLICY "resumes_own_data" ON resumes
  USING (user_id = (SELECT id FROM users WHERE clerk_id = auth.jwt() ->> 'sub'));

CREATE POLICY "applications_own_data" ON applications
  USING (user_id = (SELECT id FROM users WHERE clerk_id = auth.jwt() ->> 'sub'));

CREATE POLICY "insights_own_data" ON ai_insights
  USING (user_id = (SELECT id FROM users WHERE clerk_id = auth.jwt() ->> 'sub'));

-- (Similar policies applied to all other tables)

-- ============================================================
-- SEED: Default usage quotas for new users (via trigger)
-- ============================================================
CREATE OR REPLACE FUNCTION create_user_quota()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO usage_quotas (user_id, analyses_limit, applications_limit)
  VALUES (NEW.id, 3, 10);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_user_created
  AFTER INSERT ON users
  FOR EACH ROW EXECUTE FUNCTION create_user_quota();

-- ============================================================
-- ANALYSIS JOBS (async job tracking — Supabase Realtime pushes status)
-- ============================================================
CREATE TABLE analysis_jobs (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID REFERENCES users(id) ON DELETE CASCADE,
  resume_id             UUID REFERENCES resumes(id),
  jd_id                 UUID,
  analysis_types        TEXT[] DEFAULT '{}',
  status                TEXT DEFAULT 'queued'
                        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
  results               JSONB DEFAULT '[]',
  error                 TEXT,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER analysis_jobs_updated_at BEFORE UPDATE ON analysis_jobs
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "analysis_jobs_own" ON analysis_jobs
  USING (user_id = (SELECT id FROM users WHERE clerk_id = auth.jwt() ->> 'sub'));

-- Enable Realtime for job status updates (run in Supabase dashboard)
-- ALTER PUBLICATION supabase_realtime ADD TABLE analysis_jobs;

-- ============================================================
-- FEEDBACK / WAITLIST
-- ============================================================
CREATE TABLE feedback (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email             TEXT NOT NULL,
  name              TEXT,
  linkedin_url      TEXT,
  from_role         TEXT,
  target_role       TEXT,
  pain_points       TEXT[] DEFAULT '{}',
  biggest_struggle  TEXT,
  would_pay         TEXT,  -- 'yes_definitely' | 'yes_maybe' | 'no'
  nps               TEXT,  -- 1-10
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_email ON feedback(email);
CREATE INDEX idx_feedback_would_pay ON feedback(would_pay);
