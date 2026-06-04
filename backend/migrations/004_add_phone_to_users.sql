-- Add phone field to users table for outreach email signatures
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
