-- Multi-artist onboarding: slug, profile, and per-artist pricing config
-- Run against existing Inkbook databases after 001

ALTER TABLE artists
    ADD COLUMN IF NOT EXISTS slug VARCHAR(50) UNIQUE,
    ADD COLUMN IF NOT EXISTS bio_short TEXT,
    ADD COLUMN IF NOT EXISTS specialties TEXT[],
    ADD COLUMN IF NOT EXISTS pricing_config JSONB,
    ADD COLUMN IF NOT EXISTS admin_secret VARCHAR(64);

-- Backfill Miguel (founding artist)
UPDATE artists
SET
    slug = 'miguel',
    bio_short = 'Black and grey realism specialist based in the Austin, TX area.',
    specialties = ARRAY['realism', 'blackwork', 'portraits'],
    pricing_config = '{
        "small": {"min": 100, "max": 300, "deposit": 50},
        "half_day": {"min": 400, "max": 600, "deposit": 100},
        "full_day": {"min": 800, "max": 1000, "deposit": 100},
        "full_sleeve": {"min": 800, "max": 1000, "deposit": 100}
    }'::jsonb,
    admin_secret = 'm1g'
WHERE name = 'Miguel' AND slug IS NULL;

-- Slug required for new artists going forward (existing rows backfilled above)
ALTER TABLE artists
    ALTER COLUMN slug SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_artists_slug ON artists (slug);
