-- Migration 004: Add interview_questions as a valid analysis_type
-- Run in Supabase SQL editor

ALTER TABLE resume_analyses
  DROP CONSTRAINT IF EXISTS resume_analyses_analysis_type_check;

ALTER TABLE resume_analyses
  ADD CONSTRAINT resume_analyses_analysis_type_check
  CHECK (analysis_type IN ('ats', 'recruiter', 'role_fit', 'readiness', 'full', 'rewrite', 'interview_questions'));
