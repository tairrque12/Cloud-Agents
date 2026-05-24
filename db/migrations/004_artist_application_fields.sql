-- New-artist application fields (pending onboarding submissions)
-- Does not alter Miguel's existing row or active-artist defaults.

ALTER TABLE artists DROP CONSTRAINT IF EXISTS artists_status_check;
ALTER TABLE artists ADD CONSTRAINT artists_status_check
    CHECK (status IN ('active', 'inactive', 'suspended', 'pending'));

ALTER TABLE artists
    ADD COLUMN IF NOT EXISTS profile_photo_url TEXT,
    ADD COLUMN IF NOT EXISTS scheduling_tool VARCHAR(100),
    ADD COLUMN IF NOT EXISTS scheduling_tool_other TEXT,
    ADD COLUMN IF NOT EXISTS application_notes TEXT;
