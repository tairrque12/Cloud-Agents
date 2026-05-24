-- Artist availability config for new onboarded artists (JSON schedule rules)
-- Safe to run on production — adds nullable column only

ALTER TABLE artists
    ADD COLUMN IF NOT EXISTS availability_config JSONB;

COMMENT ON COLUMN artists.availability_config IS
'Weekly schedule, hours, session limits, and blocked dates for AI date suggestions.';
