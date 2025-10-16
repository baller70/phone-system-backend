
-- Phase 9: Intelligence & Customer Experience Tables
-- Call Recordings, Transcriptions, Intelligence, Notifications, Customer Portal

-- Call Recordings Table
CREATE TABLE IF NOT EXISTS call_recordings (
    id SERIAL PRIMARY KEY,
    call_uuid TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    recording_url TEXT,
    file_size BIGINT DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    format TEXT DEFAULT 'mp3',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Call Transcriptions Table
CREATE TABLE IF NOT EXISTS call_transcriptions (
    id SERIAL PRIMARY KEY,
    call_uuid TEXT UNIQUE NOT NULL,
    transcription_text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    char_count INTEGER DEFAULT 0,
    language TEXT DEFAULT 'en-US',
    confidence_score REAL DEFAULT 0,
    audio_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_uuid) REFERENCES call_recordings(call_uuid) ON DELETE CASCADE
);

-- Call Intelligence Table (AI Analysis)
CREATE TABLE IF NOT EXISTS call_intelligence (
    id SERIAL PRIMARY KEY,
    call_uuid TEXT UNIQUE NOT NULL,
    call_score INTEGER DEFAULT 0,
    success_indicators TEXT,
    problem_indicators TEXT,
    upsell_opportunities TEXT,
    key_phrases TEXT,
    insights TEXT,
    sentiment_overall TEXT DEFAULT 'neutral',
    sentiment_score REAL DEFAULT 0,
    escalation_recommended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications Log Table
CREATE TABLE IF NOT EXISTS notifications_log (
    id SERIAL PRIMARY KEY,
    booking_id TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    notification_type TEXT NOT NULL,
    channel TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Notifications Table
CREATE TABLE IF NOT EXISTS scheduled_notifications (
    id SERIAL PRIMARY KEY,
    booking_id TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    booking_data JSONB,
    status TEXT DEFAULT 'pending',
    sent_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer Portal Users Table
CREATE TABLE IF NOT EXISTS customer_portal_users (
    id SERIAL PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    verification_token TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    reset_token TEXT,
    reset_token_expires TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer Bookings View (for portal)
CREATE TABLE IF NOT EXISTS customer_booking_history (
    id SERIAL PRIMARY KEY,
    customer_phone TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    facility_type TEXT NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    duration_hours REAL NOT NULL,
    price REAL,
    status TEXT DEFAULT 'confirmed',
    created_via TEXT DEFAULT 'phone',
    can_cancel BOOLEAN DEFAULT TRUE,
    can_reschedule BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email Templates Table
CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,
    template_name TEXT UNIQUE NOT NULL,
    template_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    html_content TEXT NOT NULL,
    variables TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_call_transcriptions_call_uuid ON call_transcriptions(call_uuid);
CREATE INDEX IF NOT EXISTS idx_call_intelligence_call_uuid ON call_intelligence(call_uuid);
CREATE INDEX IF NOT EXISTS idx_call_intelligence_score ON call_intelligence(call_score);
CREATE INDEX IF NOT EXISTS idx_notifications_booking_id ON notifications_log(booking_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications_log(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_time ON scheduled_notifications(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_status ON scheduled_notifications(status);
CREATE INDEX IF NOT EXISTS idx_customer_portal_phone ON customer_portal_users(phone);
CREATE INDEX IF NOT EXISTS idx_customer_portal_email ON customer_portal_users(email);
CREATE INDEX IF NOT EXISTS idx_customer_bookings_phone ON customer_booking_history(customer_phone);
CREATE INDEX IF NOT EXISTS idx_customer_bookings_date ON customer_booking_history(booking_date);
