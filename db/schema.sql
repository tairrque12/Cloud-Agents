-- ============================================================
-- INKBOOK DATABASE SCHEMA
-- PostgreSQL
-- Last updated: April 30, 2026
-- ============================================================
-- Tables:
--   artists         — onboarded tattoo artists
--   clients         — people who submit booking requests
--   intakes         — every form submission that comes through
--   estimates       — pricing agent output per intake
--   schedules       — scheduling agent output per intake
--   approvals       — Miguel's approve/adjust/decline decisions
--   bookings        — confirmed appointments after approval
--   referrals       — affiliate/referral tracking
-- ============================================================


-- ============================================================
-- ARTISTS
-- Every tattoo artist onboarded to Inkbook
-- ============================================================

CREATE TABLE artists (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Identity
    name                VARCHAR(100) NOT NULL,
    email               VARCHAR(255) UNIQUE NOT NULL,
    phone               VARCHAR(20),
    instagram_handle    VARCHAR(100),

    -- Location
    city                VARCHAR(100),
    state               VARCHAR(50),
    studio_name         VARCHAR(150),

    -- Platform status
    status              VARCHAR(20) DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'suspended')),
    plan                VARCHAR(20) DEFAULT 'starter'
                        CHECK (plan IN ('starter', 'pro', 'elite')),
    is_founding_artist  BOOLEAN DEFAULT FALSE,

    -- Telegram
    telegram_chat_id    VARCHAR(50),
    telegram_bot_token  VARCHAR(200),

    -- Referral program
    referral_code       VARCHAR(20) UNIQUE,
    referred_by         UUID REFERENCES artists(id),
    affiliate_unlocked  BOOLEAN DEFAULT FALSE,
    affiliate_rate      DECIMAL(5,2) DEFAULT 20.00,

    -- Booking rules
    booking_min_days    INTEGER DEFAULT 14,
    booking_max_days    INTEGER DEFAULT 60,

    -- Timestamps
    onboarded_at        TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE artists IS
'Every tattoo artist onboarded to Inkbook. 
Each artist has their own agents configured 
around their rates, voice, and schedule.';


-- ============================================================
-- CLIENTS
-- People who submit booking requests
-- Upserted on every intake — same contact = same client
-- ============================================================

CREATE TABLE clients (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Identity
    name                VARCHAR(100) NOT NULL,
    contact             VARCHAR(255) NOT NULL UNIQUE,
    contact_type        VARCHAR(10) DEFAULT 'phone'
                        CHECK (contact_type IN ('phone', 'email')),

    -- History
    total_intakes       INTEGER DEFAULT 0,
    total_bookings      INTEGER DEFAULT 0,
    total_spent         DECIMAL(10,2) DEFAULT 0.00,
    last_intake_at      TIMESTAMP WITH TIME ZONE,
    last_booking_at     TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE clients IS
'Clients are upserted on every intake. 
Same phone or email = same client record. 
Enables repeat client tracking over time.';


-- ============================================================
-- INTAKES
-- Every form submission that comes through
-- Core table — everything else references this
-- ============================================================

CREATE TABLE intakes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Short ID shown to Miguel on Telegram card
    short_id            VARCHAR(10) UNIQUE NOT NULL,

    -- Relationships
    artist_id           UUID NOT NULL REFERENCES artists(id),
    client_id           UUID NOT NULL REFERENCES clients(id),

    -- Classification
    classification      VARCHAR(10) NOT NULL
                        CHECK (classification IN ('STRONG', 'SOFT')),
    confidence_level    VARCHAR(10)
                        CHECK (confidence_level IN ('HIGH', 'MEDIUM', 'LOW')),
    flags               TEXT[],

    -- Form data
    size_selection      VARCHAR(20) NOT NULL
                        CHECK (size_selection IN (
                            'small', 'medium', 'large', 'full_sleeve'
                        )),
    description         TEXT NOT NULL,
    placement           VARCHAR(100),
    styles              TEXT[],
    is_cover_up         BOOLEAN DEFAULT FALSE,
    cover_up_description TEXT,
    budget_range        VARCHAR(20)
                        CHECK (budget_range IN (
                            'under_200', '200_500',
                            '500_1000', '1000_plus'
                        )),
    preferred_timing    VARCHAR(20)
                        CHECK (preferred_timing IN (
                            'within_2_weeks', 'within_1_month',
                            'within_2_months', 'flexible'
                        )),
    idea_readiness      VARCHAR(20)
                        CHECK (idea_readiness IN (
                            'knows_exactly', 'needs_help'
                        )),
    reference_image_url TEXT,

    -- Guided discovery answers
    guided_meaning      TEXT,
    guided_imagery      TEXT,
    guided_style_notes  TEXT,

    -- Crew output
    raw_crew_output     TEXT,
    emotional_tone_note TEXT,

    -- Status
    status              VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN (
                            'pending', 'approved',
                            'adjusted', 'declined', 'expired'
                        ))
);

COMMENT ON TABLE intakes IS
'Every booking request submitted through Inkbook.
The short_id maps to what Miguel sees on his Telegram card.
Raw crew output stored for debugging and eval purposes.';


-- ============================================================
-- ESTIMATES
-- Pricing agent output for each intake
-- ============================================================

CREATE TABLE estimates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Relationship
    intake_id           UUID NOT NULL REFERENCES intakes(id),

    -- Session classification
    session_type        VARCHAR(20) NOT NULL
                        CHECK (session_type IN (
                            'small', 'half_day',
                            'full_day', 'full_sleeve'
                        )),
    session_type_confidence VARCHAR(10)
                        CHECK (session_type_confidence IN (
                            'HIGH', 'MEDIUM', 'LOW'
                        )),

    -- Pricing
    price_min           DECIMAL(10,2) NOT NULL,
    price_max           DECIMAL(10,2) NOT NULL,
    deposit_amount      DECIMAL(10,2) NOT NULL,
    duration_estimate   VARCHAR(50),

    -- Agent output
    personalized_note   TEXT,
    disclaimer_included BOOLEAN DEFAULT TRUE,
    pricing_flags       TEXT[],

    -- Cover up
    is_cover_up_flagged BOOLEAN DEFAULT FALSE,
    cover_up_note       TEXT
);

COMMENT ON TABLE estimates IS
'Pricing agent output per intake.
Price range stored as min and max for flexible querying.
Disclaimer inclusion tracked for compliance.';


-- ============================================================
-- SCHEDULES
-- Scheduling agent output for each intake
-- ============================================================

CREATE TABLE schedules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Relationship
    intake_id           UUID NOT NULL REFERENCES intakes(id),

    -- Offered dates — stored as array
    -- Miguel confirms exact time after approval
    offered_dates       DATE[] NOT NULL,

    -- Day capacity
    day_capacity_rule   VARCHAR(20)
                        CHECK (day_capacity_rule IN (
                            'full_day_block',
                            'single_booking',
                            'multiple_possible'
                        )),
    capacity_flag       TEXT,

    -- Calendar source
    calendar_source     VARCHAR(30) DEFAULT 'manual'
                        CHECK (calendar_source IN (
                            'manual', 'google_calendar'
                        )),

    -- Selected date — filled when client picks one
    selected_date       DATE,
    confirmed_time      TIME
);

COMMENT ON TABLE schedules IS
'Scheduling agent output per intake.
Offered dates stored as array — up to three options.
Selected date and confirmed time filled after approval.
Times are never included in agent output — Miguel confirms personally.';


-- ============================================================
-- APPROVALS
-- Miguel's decision on every intake
-- ============================================================

CREATE TABLE approvals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Relationship
    intake_id           UUID NOT NULL REFERENCES intakes(id),
    artist_id           UUID NOT NULL REFERENCES artists(id),

    -- Decision
    decision            VARCHAR(10) NOT NULL
                        CHECK (decision IN (
                            'approved', 'adjusted', 'declined'
                        )),
    decided_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- If adjusted — what changed
    adjusted_price      VARCHAR(50),
    adjusted_dates      TEXT,
    adjusted_message    TEXT,

    -- Response sent to client
    client_message_sent TEXT,
    message_sent_at     TIMESTAMP WITH TIME ZONE,

    -- Channel used to notify client
    notification_channel VARCHAR(20) DEFAULT 'sms'
                        CHECK (notification_channel IN (
                            'sms', 'email', 'manual'
                        ))
);

COMMENT ON TABLE approvals IS
'Every approval decision Miguel makes via Telegram.
Adjusted fields track what Miguel changed before sending.
Full client message stored for audit trail.';


-- ============================================================
-- BOOKINGS
-- Confirmed appointments after approval and deposit
-- ============================================================

CREATE TABLE bookings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Relationships
    intake_id           UUID NOT NULL REFERENCES intakes(id),
    artist_id           UUID NOT NULL REFERENCES artists(id),
    client_id           UUID NOT NULL REFERENCES clients(id),
    approval_id         UUID NOT NULL REFERENCES approvals(id),

    -- Appointment
    appointment_date    DATE NOT NULL,
    appointment_time    TIME,
    session_type        VARCHAR(20) NOT NULL,
    duration_estimate   VARCHAR(50),

    -- Pricing
    quoted_price_min    DECIMAL(10,2),
    quoted_price_max    DECIMAL(10,2),
    final_price         DECIMAL(10,2),
    deposit_amount      DECIMAL(10,2),

    -- Deposit payment
    deposit_paid        BOOLEAN DEFAULT FALSE,
    deposit_paid_at     TIMESTAMP WITH TIME ZONE,
    stripe_payment_id   VARCHAR(200),
    deposit_link        TEXT,

    -- Status
    status              VARCHAR(20) DEFAULT 'deposit_pending'
                        CHECK (status IN (
                            'deposit_pending',
                            'confirmed',
                            'completed',
                            'cancelled',
                            'no_show'
                        )),

    -- Completion
    completed_at        TIMESTAMP WITH TIME ZONE,
    final_price_charged DECIMAL(10,2),
    artist_notes        TEXT
);

COMMENT ON TABLE bookings IS
'Confirmed appointments. Created after Miguel approves 
and client pays deposit. Status tracks the full lifecycle 
from deposit pending through completion.';


-- ============================================================
-- REFERRALS
-- Affiliate and referral tracking
-- ============================================================

CREATE TABLE referrals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Who referred whom
    referrer_id         UUID NOT NULL REFERENCES artists(id),
    referred_artist_id  UUID NOT NULL REFERENCES artists(id),

    -- Status
    status              VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN (
                            'pending',
                            'active',
                            'paid',
                            'churned'
                        )),

    -- Commission
    commission_rate     DECIMAL(5,2) NOT NULL,
    commission_type     VARCHAR(20) DEFAULT 'percentage'
                        CHECK (commission_type IN (
                            'percentage', 'flat'
                        )),

    -- Payout tracking
    total_earned        DECIMAL(10,2) DEFAULT 0.00,
    total_paid_out      DECIMAL(10,2) DEFAULT 0.00,
    last_payout_at      TIMESTAMP WITH TIME ZONE,

    -- Expiry
    expires_at          TIMESTAMP WITH TIME ZONE,
    is_lifetime         BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE referrals IS
'Tracks artist referral relationships and commission earnings.
Commission rate set at time of referral based on artist tier.
Lifetime flag set for power referrers with 5+ active referrals.';


-- ============================================================
-- INDEXES
-- Optimized for the most common query patterns
-- ============================================================

-- Intakes — most queried by artist and status
CREATE INDEX idx_intakes_artist_id
    ON intakes(artist_id);

CREATE INDEX idx_intakes_client_id
    ON intakes(client_id);

CREATE INDEX idx_intakes_status
    ON intakes(status);

CREATE INDEX idx_intakes_short_id
    ON intakes(short_id);

CREATE INDEX idx_intakes_created_at
    ON intakes(created_at DESC);

-- Bookings — queried by artist, client, date, status
CREATE INDEX idx_bookings_artist_id
    ON bookings(artist_id);

CREATE INDEX idx_bookings_client_id
    ON bookings(client_id);

CREATE INDEX idx_bookings_appointment_date
    ON bookings(appointment_date);

CREATE INDEX idx_bookings_status
    ON bookings(status);

-- Approvals — queried by intake and artist
CREATE INDEX idx_approvals_intake_id
    ON approvals(intake_id);

CREATE INDEX idx_approvals_artist_id
    ON approvals(artist_id);

-- Referrals — queried by referrer
CREATE INDEX idx_referrals_referrer_id
    ON referrals(referrer_id);

CREATE INDEX idx_referrals_referred_artist_id
    ON referrals(referred_artist_id);


-- ============================================================
-- UPDATED_AT TRIGGER
-- Auto-updates updated_at on every row change
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER artists_updated_at
    BEFORE UPDATE ON artists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER intakes_updated_at
    BEFORE UPDATE ON intakes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER bookings_updated_at
    BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- SEED DATA — Miguel
-- Insert Miguel as the founding artist
-- Update with real values before production
-- ============================================================

INSERT INTO artists (
    name,
    email,
    instagram_handle,
    city,
    state,
    studio_name,
    status,
    plan,
    is_founding_artist,
    telegram_chat_id,
    referral_code,
    affiliate_unlocked,
    affiliate_rate,
    booking_min_days,
    booking_max_days,
    onboarded_at
) VALUES (
    'Miguel',
    'miguel@placeholder.com',
    'txsmichaell_',
    'Round Rock',
    'TX',
    'Independent',
    'active',
    'pro',
    TRUE,
    '5864198350',
    'MIGUEL2026',
    TRUE,
    25.00,
    14,
    60,
    NOW()
);