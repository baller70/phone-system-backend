
-- Phase 7: Enterprise Intelligence & Multi-Channel Experience
-- Database schema for advanced features

-- Multi-channel conversations tracking
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    customer_phone VARCHAR(20) NOT NULL,
    channel VARCHAR(20) NOT NULL,  -- 'phone', 'whatsapp', 'sms', 'web_chat'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    messages JSON,  -- All messages in conversation
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'completed', 'abandoned'
    language VARCHAR(5) DEFAULT 'en',  -- 'en', 'es', 'fr', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer (customer_phone),
    INDEX idx_channel (channel),
    INDEX idx_status (status)
);

-- Voice broadcast campaigns
CREATE TABLE IF NOT EXISTS broadcast_campaigns (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    target_segment VARCHAR(100),  -- 'all', 'vip', 'inactive', etc.
    scheduled_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL,
    total_calls INT DEFAULT 0,
    answered_calls INT DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scheduled (scheduled_at),
    INDEX idx_segment (target_segment)
);

-- ML demand forecasts
CREATE TABLE IF NOT EXISTS demand_forecasts (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    facility_id INT NULL,
    forecast_date DATE NOT NULL,
    forecast_hour INT NULL,
    predicted_bookings DECIMAL(5,2) NOT NULL,
    confidence_lower DECIMAL(5,2),
    confidence_upper DECIMAL(5,2),
    actual_bookings INT NULL,  -- Filled after the fact
    model_type VARCHAR(50) DEFAULT 'prophet',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_forecast (facility_id, forecast_date, forecast_hour),
    INDEX idx_forecast_date (forecast_date),
    INDEX idx_facility (facility_id)
);

-- Dynamic pricing records
CREATE TABLE IF NOT EXISTS dynamic_prices (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    facility_id INT NOT NULL,
    date DATE NOT NULL,
    hour INT NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    dynamic_price DECIMAL(10,2) NOT NULL,
    demand_level VARCHAR(20),  -- 'low', 'medium', 'high', 'surge'
    discount_percent DECIMAL(5,2) DEFAULT 0,
    adjustments JSON,  -- List of pricing adjustments applied
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_facility_date (facility_id, date),
    INDEX idx_demand (demand_level)
);

-- Customer churn predictions
CREATE TABLE IF NOT EXISTS churn_predictions (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    customer_phone VARCHAR(20) NOT NULL,
    churn_probability DECIMAL(5,2) NOT NULL,  -- 0-100%
    risk_level VARCHAR(20),  -- 'low', 'medium', 'high'
    last_booking_date DATE,
    days_since_last_booking INT,
    total_bookings INT DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    risk_factors JSON,  -- List of risk factors
    retention_action VARCHAR(100),  -- Suggested retention action
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_customer (customer_phone),
    INDEX idx_risk (risk_level),
    INDEX idx_probability (churn_probability)
);

-- Custom reports
CREATE TABLE IF NOT EXISTS saved_reports (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    query_config JSON NOT NULL,  -- Report configuration
    schedule VARCHAR(50),  -- 'daily', 'weekly', 'monthly', NULL
    email_recipients JSON,  -- Array of email addresses
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP NULL,
    INDEX idx_schedule (schedule)
);

-- Integration credentials (encrypted)
CREATE TABLE IF NOT EXISTS integration_credentials (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    service_name VARCHAR(100) NOT NULL,  -- 'salesforce', 'quickbooks', etc.
    credentials JSON NOT NULL,  -- Encrypted OAuth tokens/API keys
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'expired', 'error'
    last_sync_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_service (service_name),
    INDEX idx_status (status)
);

-- Customer language preferences
CREATE TABLE IF NOT EXISTS customer_languages (
    customer_phone VARCHAR(20) PRIMARY KEY,
    preferred_language VARCHAR(5) NOT NULL DEFAULT 'en',
    detected_languages VARCHAR(100),  -- Comma-separated list
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_language (preferred_language)
);

-- SMS/WhatsApp message log
CREATE TABLE IF NOT EXISTS message_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    customer_phone VARCHAR(20) NOT NULL,
    message_type VARCHAR(20) NOT NULL,  -- 'sms', 'whatsapp', 'email'
    direction VARCHAR(10) NOT NULL,  -- 'inbound', 'outbound'
    message_body TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'sent', 'delivered', 'failed'
    external_id VARCHAR(100),  -- Twilio message SID, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer (customer_phone),
    INDEX idx_type (message_type),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);

-- Analytics snapshots (for faster dashboard loading)
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    snapshot_date DATE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,2),
    metadata JSON,  -- Additional context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_snapshot (snapshot_date, metric_name),
    INDEX idx_metric (metric_name),
    INDEX idx_date (snapshot_date)
);

-- Update bookings table to add channel column if it doesn't exist
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'phone';
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'en';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_bookings_channel ON bookings(channel);
CREATE INDEX IF NOT EXISTS idx_bookings_language ON bookings(language);
CREATE INDEX IF NOT EXISTS idx_bookings_created ON bookings(created_at);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
