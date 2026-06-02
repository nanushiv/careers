-- Migration 003: Auto-fix resume rewrite feature
-- Adds rewrite analysis type and columns to resume_analyses

-- Extend analysis_type CHECK constraint to include 'rewrite'
ALTER TABLE resume_analyses
  DROP CONSTRAINT IF EXISTS resume_analyses_analysis_type_check;

ALTER TABLE resume_analyses
  ADD CONSTRAINT resume_analyses_analysis_type_check
  CHECK (analysis_type IN ('ats', 'recruiter', 'role_fit', 'readiness', 'full', 'rewrite'));

-- Add columns for rewrite output
ALTER TABLE resume_analyses
  ADD COLUMN IF NOT EXISTS improved_resume_url TEXT,
  ADD COLUMN IF NOT EXISTS improved_pdf_url TEXT,
  ADD COLUMN IF NOT EXISTS rewrite_status TEXT DEFAULT 'pending'
    CHECK (rewrite_status IN ('pending', 'processing', 'completed', 'failed'));
