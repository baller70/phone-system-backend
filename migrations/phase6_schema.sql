
-- Phase 6: Advanced Booking Intelligence & Customer Experience Database Schema
-- Run this after deployment to add Phase 6 tables

-- Recurring Bookings Table
CREATE TABLE IF NOT EXISTS recurring_bookings (
    id SERIAL PRIMARY KEY,
    customer_phone VARCHAR(20) NOT NULL,
    customer_email VARCHAR(255),
    customer_name VARCHAR(255),
    facility_type VARCHAR(100) NOT NULL,
    day_of_week INT NOT NULL,  -- 0=Monday, 6=Sunday
    time_slot TIME NOT NULL,
    duration_hours FLOAT NOT NULL,
    frequency VARCHAR(20) NOT NULL,  -- 'weekly', 'biweekly', 'monthly'
    start_date DATE NOT NULL,
    end_date DATE,
    next_booking_date DATE,
    is_active BOOLEAN DEFAULT true,
    calcom_event_type_id INT,
    price_per_booking FLOAT,
    total_bookings_created INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recurring_bookings_phone ON recurring_bookings(customer_phone);
CREATE INDEX idx_recurring_bookings_next_date ON recurring_bookings(next_booking_date);
CREATE INDEX idx_recurring_bookings_active ON recurring_bookings(is_active);

-- Waitlist Table
CREATE TABLE IF NOT EXISTS waitlist (
    id SERIAL PRIMARY KEY,
    customer_phone VARCHAR(20) NOT NULL,
    customer_email VARCHAR(255),
    customer_name VARCHAR(255),
    facility_type VARCHAR(100) NOT NULL,
    requested_date DATE NOT NULL,
    requested_time TIME NOT NULL,
    duration_hours FLOAT NOT NULL,
    priority INT DEFAULT 0,  -- FIFO: lower number = higher priority
    notified_at TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'waiting',  -- 'waiting', 'notified', 'booked', 'expired'
    notification_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_waitlist_status ON waitlist(status);
CREATE INDEX idx_waitlist_facility_date ON waitlist(facility_type, requested_date);
CREATE INDEX idx_waitlist_priority ON waitlist(priority);

-- Customer Tiers & Loyalty
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'standard',  -- 'standard', 'vip', 'platinum'
    total_bookings INT DEFAULT 0,
    total_spent_dollars FLOAT DEFAULT 0,
    loyalty_points INT DEFAULT 0,
    preferences JSONB DEFAULT '{}',
    voice_print TEXT,  -- Base64 encoded voice features
    communication_preference VARCHAR(20) DEFAULT 'sms',  -- 'sms', 'email', 'both'
    favorite_facility VARCHAR(100),
    preferred_time_slot VARCHAR(20),  -- 'morning', 'afternoon', 'evening'
    average_duration_hours FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_booking_at TIMESTAMP,
    vip_since TIMESTAMP
);

CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_tier ON customers(tier);
CREATE INDEX idx_customers_points ON customers(loyalty_points);

-- Loyalty Transactions
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    customer_phone VARCHAR(20) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,  -- 'earned', 'redeemed', 'bonus', 'expired'
    points INT NOT NULL,
    description TEXT,
    booking_id VARCHAR(100),
    balance_after INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_loyalty_transactions_customer ON loyalty_transactions(customer_id);
CREATE INDEX idx_loyalty_transactions_phone ON loyalty_transactions(customer_phone);
CREATE INDEX idx_loyalty_transactions_type ON loyalty_transactions(transaction_type);

-- Peak Time Analytics
CREATE TABLE IF NOT EXISTS booking_analytics (
    id SERIAL PRIMARY KEY,
    facility_type VARCHAR(100) NOT NULL,
    day_of_week INT NOT NULL,  -- 0=Monday, 6=Sunday
    hour INT NOT NULL,  -- 0-23
    booking_count INT DEFAULT 0,
    revenue_dollars FLOAT DEFAULT 0,
    average_duration_hours FLOAT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(facility_type, day_of_week, hour)
);

CREATE INDEX idx_analytics_facility ON booking_analytics(facility_type);
CREATE INDEX idx_analytics_day_hour ON booking_analytics(day_of_week, hour);

-- Emergency Bookings
CREATE TABLE IF NOT EXISTS emergency_bookings (
    id SERIAL PRIMARY KEY,
    conversation_uuid VARCHAR(100) UNIQUE,
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    facility_type VARCHAR(100) NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    urgency_level VARCHAR(20) DEFAULT 'high',  -- 'high', 'critical'
    reason TEXT,
    staff_notified BOOLEAN DEFAULT false,
    staff_notification_sent_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'confirmed', 'resolved'
    calcom_booking_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX idx_emergency_bookings_status ON emergency_bookings(status);
CREATE INDEX idx_emergency_bookings_date ON emergency_bookings(booking_date);

-- Rebooking Campaigns
CREATE TABLE IF NOT EXISTS rebooking_campaigns (
    id SERIAL PRIMARY KEY,
    customer_phone VARCHAR(20) NOT NULL,
    customer_email VARCHAR(255),
    customer_name VARCHAR(255),
    last_booking_id VARCHAR(100),
    last_booking_date DATE,
    last_facility_type VARCHAR(100),
    campaign_type VARCHAR(20) DEFAULT 'standard',  -- 'standard', 'vip', 'win-back'
    outbound_call_scheduled_at TIMESTAMP,
    outbound_call_made_at TIMESTAMP,
    call_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'failed', 'booked'
    rebooked BOOLEAN DEFAULT false,
    new_booking_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rebooking_campaigns_phone ON rebooking_campaigns(customer_phone);
CREATE INDEX idx_rebooking_campaigns_status ON rebooking_campaigns(call_status);
CREATE INDEX idx_rebooking_campaigns_scheduled ON rebooking_campaigns(outbound_call_scheduled_at);

-- Email Log (for tracking)
CREATE TABLE IF NOT EXISTS email_log (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_phone VARCHAR(20),
    email_type VARCHAR(50) NOT NULL,  -- 'booking_confirmation', 'cancellation', 'modification', 'recurring_schedule'
    subject TEXT,
    booking_id VARCHAR(100),
    sendgrid_message_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'sent',  -- 'sent', 'delivered', 'failed', 'bounced'
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_log_recipient ON email_log(recipient_email);
CREATE INDEX idx_email_log_booking ON email_log(booking_id);
CREATE INDEX idx_email_log_type ON email_log(email_type);

-- Group Bookings Tracking (extended info)
CREATE TABLE IF NOT EXISTS group_bookings (
    id SERIAL PRIMARY KEY,
    calcom_booking_id VARCHAR(100) UNIQUE NOT NULL,
    conversation_uuid VARCHAR(100),
    customer_phone VARCHAR(20) NOT NULL,
    coordinator_name VARCHAR(255),
    coordinator_email VARCHAR(255),
    facility_type VARCHAR(100) NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    group_size INT NOT NULL,
    base_price FLOAT,
    group_multiplier FLOAT,
    total_price FLOAT,
    special_requirements TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_group_bookings_phone ON group_bookings(customer_phone);
CREATE INDEX idx_group_bookings_calcom ON group_bookings(calcom_booking_id);
CREATE INDEX idx_group_bookings_date ON group_bookings(booking_date);
