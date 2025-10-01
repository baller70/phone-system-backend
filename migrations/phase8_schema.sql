
-- ============================================
-- PHASE 8: Enterprise Scale & Revenue Acceleration
-- Database Migration Schema
-- ============================================

-- ============================================
-- 1. PAYMENTS & SUBSCRIPTIONS
-- ============================================

CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(36) PRIMARY KEY,
    booking_id VARCHAR(36),
    customer_phone VARCHAR(20),
    amount DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    payment_type VARCHAR(20),        -- 'deposit', 'full', 'balance', 'subscription'
    payment_method VARCHAR(50),      -- 'card', 'bank_transfer', 'wallet'
    stripe_payment_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    status VARCHAR(20),              -- 'pending', 'completed', 'failed', 'refunded'
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_phone);
CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at);

CREATE TABLE IF NOT EXISTS refunds (
    id VARCHAR(36) PRIMARY KEY,
    payment_id VARCHAR(36),
    booking_id VARCHAR(36),
    amount DECIMAL(10,2),
    reason TEXT,
    stripe_refund_id VARCHAR(100),
    status VARCHAR(20),              -- 'pending', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_id) REFERENCES payments(id)
);

CREATE INDEX IF NOT EXISTS idx_refunds_payment ON refunds(payment_id);
CREATE INDEX IF NOT EXISTS idx_refunds_booking ON refunds(booking_id);

CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    customer_phone VARCHAR(20),
    plan_name VARCHAR(100),
    stripe_subscription_id VARCHAR(100),
    status VARCHAR(20),              -- 'active', 'cancelled', 'past_due', 'paused'
    amount DECIMAL(10,2),
    interval VARCHAR(20),            -- 'monthly', 'yearly'
    current_period_start DATE,
    current_period_end DATE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_phone);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

-- ============================================
-- 2. MULTI-TENANT / WHITE-LABEL
-- ============================================

CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    subdomain VARCHAR(100) UNIQUE,   -- 'acme.yoursystem.com'
    custom_domain VARCHAR(200),      -- 'booking.acmesports.com'
    phone_number VARCHAR(20),
    branding JSON,                   -- {logo, primaryColor, secondaryColor, font}
    subscription_plan VARCHAR(50),   -- 'basic', 'pro', 'enterprise'
    subscription_status VARCHAR(20), -- 'active', 'suspended', 'cancelled', 'trial'
    monthly_booking_limit INT DEFAULT 500,
    current_bookings_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trial_ends_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenants_subdomain ON tenants(subdomain);
CREATE INDEX IF NOT EXISTS idx_tenants_custom_domain ON tenants(custom_domain);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(subscription_status);

CREATE TABLE IF NOT EXISTS tenant_settings (
    tenant_id VARCHAR(36) PRIMARY KEY,
    business_hours JSON,
    pricing_rules JSON,
    sms_credentials JSON,
    whatsapp_credentials JSON,
    stripe_credentials JSON,
    email_settings JSON,
    features_enabled JSON,           -- {'dynamic_pricing': true, 'ml_forecasting': false}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tenant_usage (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36),
    month DATE,
    total_calls INT DEFAULT 0,
    total_bookings INT DEFAULT 0,
    total_sms_sent INT DEFAULT 0,
    total_whatsapp_sent INT DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    api_calls INT DEFAULT 0,
    storage_gb DECIMAL(8,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tenant_usage_tenant ON tenant_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_usage_month ON tenant_usage(month);

-- ============================================
-- 3. VOICE ANALYTICS & CALL QUALITY
-- ============================================

CREATE TABLE IF NOT EXISTS call_analytics (
    id VARCHAR(36) PRIMARY KEY,
    call_id VARCHAR(36),
    customer_phone VARCHAR(20),
    duration_seconds INT,
    sentiment_score DECIMAL(5,2),    -- -1.0 to 1.0
    quality_score DECIMAL(5,2),      -- 0-100
    emotions JSON,                   -- {'frustrated': 0.3, 'happy': 0.6}
    keywords JSON,
    topics JSON,
    ai_accuracy DECIMAL(5,2),
    response_time_avg_ms INT,
    booking_success BOOLEAN,
    escalated BOOLEAN,
    competitor_mentioned BOOLEAN,
    upsell_opportunities JSON,
    audio_quality DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_call_analytics_call ON call_analytics(call_id);
CREATE INDEX IF NOT EXISTS idx_call_analytics_customer ON call_analytics(customer_phone);
CREATE INDEX IF NOT EXISTS idx_call_analytics_date ON call_analytics(created_at);

CREATE TABLE IF NOT EXISTS conversation_quality_metrics (
    id VARCHAR(36) PRIMARY KEY,
    date DATE,
    total_calls INT DEFAULT 0,
    avg_sentiment DECIMAL(5,2),
    avg_quality_score DECIMAL(5,2),
    booking_conversion_rate DECIMAL(5,2),
    avg_response_time_ms INT,
    escalation_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quality_metrics_date ON conversation_quality_metrics(date);

-- ============================================
-- 4. MARKETING CAMPAIGNS
-- ============================================

CREATE TABLE IF NOT EXISTS marketing_campaigns (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200),
    campaign_type VARCHAR(50),       -- 'win_back', 'birthday', 'referral', 'abandoned_booking'
    target_segment VARCHAR(100),     -- 'inactive', 'vip', 'new', 'all'
    channels JSON,                   -- ['sms', 'email', 'whatsapp']
    message_template TEXT,
    discount_code VARCHAR(50),
    discount_percent DECIMAL(5,2),
    start_date DATE,
    end_date DATE,
    status VARCHAR(20),              -- 'draft', 'scheduled', 'active', 'completed', 'paused'
    sent_count INT DEFAULT 0,
    open_count INT DEFAULT 0,
    click_count INT DEFAULT 0,
    conversion_count INT DEFAULT 0,
    revenue_generated DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON marketing_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_type ON marketing_campaigns(campaign_type);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON marketing_campaigns(start_date, end_date);

CREATE TABLE IF NOT EXISTS campaign_recipients (
    id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36),
    customer_phone VARCHAR(20),
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    converted_at TIMESTAMP,
    booking_id VARCHAR(36),
    FOREIGN KEY (campaign_id) REFERENCES marketing_campaigns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign ON campaign_recipients(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_customer ON campaign_recipients(customer_phone);

-- ============================================
-- 5. CHURN PREVENTION & PREDICTION
-- ============================================

CREATE TABLE IF NOT EXISTS churn_predictions (
    id VARCHAR(36) PRIMARY KEY,
    customer_phone VARCHAR(20),
    churn_risk_score DECIMAL(5,2),   -- 0-100
    churn_probability DECIMAL(5,2),  -- 0-1
    risk_level VARCHAR(20),          -- 'low', 'medium', 'high', 'critical'
    factors JSON,                    -- ['booking_frequency_drop', 'negative_sentiment']
    recommended_actions JSON,
    predicted_churn_date DATE,
    prevention_campaign_id VARCHAR(36),
    actual_churned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_churn_customer ON churn_predictions(customer_phone);
CREATE INDEX IF NOT EXISTS idx_churn_risk_level ON churn_predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_churn_predicted_date ON churn_predictions(predicted_churn_date);

-- ============================================
-- 6. WEATHER INTEGRATION
-- ============================================

CREATE TABLE IF NOT EXISTS weather_data (
    id VARCHAR(36) PRIMARY KEY,
    date DATE,
    hour INT,
    temperature DECIMAL(5,2),
    condition VARCHAR(50),           -- 'sunny', 'rain', 'snow', 'cloudy', 'storm'
    precipitation_chance DECIMAL(5,2),
    wind_speed DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weather_date_hour ON weather_data(date, hour);

CREATE TABLE IF NOT EXISTS weather_impacts (
    id VARCHAR(36) PRIMARY KEY,
    date DATE,
    condition VARCHAR(50),
    outdoor_bookings_change DECIMAL(5,2),  -- % change
    indoor_bookings_change DECIMAL(5,2),
    revenue_impact DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weather_impacts_date ON weather_impacts(date);

-- ============================================
-- 7. UPSELLING & CROSS-SELLING
-- ============================================

CREATE TABLE IF NOT EXISTS upsell_opportunities (
    id VARCHAR(36) PRIMARY KEY,
    booking_id VARCHAR(36),
    call_id VARCHAR(36),
    upsell_type VARCHAR(50),         -- 'short_booking', 'frequent_customer', 'group_booking', 'premium_time'
    original_value DECIMAL(10,2),
    upsell_value DECIMAL(10,2),
    offer_presented BOOLEAN DEFAULT FALSE,
    accepted BOOLEAN DEFAULT FALSE,
    declined_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upsell_booking ON upsell_opportunities(booking_id);
CREATE INDEX IF NOT EXISTS idx_upsell_call ON upsell_opportunities(call_id);
CREATE INDEX IF NOT EXISTS idx_upsell_type ON upsell_opportunities(upsell_type);

CREATE TABLE IF NOT EXISTS upsell_performance (
    id VARCHAR(36) PRIMARY KEY,
    date DATE,
    upsell_type VARCHAR(50),
    total_offers INT DEFAULT 0,
    accepted_count INT DEFAULT 0,
    conversion_rate DECIMAL(5,2),
    total_revenue DECIMAL(10,2) DEFAULT 0,
    avg_upsell_value DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upsell_performance_date ON upsell_performance(date);
CREATE INDEX IF NOT EXISTS idx_upsell_performance_type ON upsell_performance(upsell_type);

-- ============================================
-- 8. SECURITY & AUDIT
-- ============================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id VARCHAR(36),
    ip_address VARCHAR(45),
    user_agent TEXT,
    changes JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

CREATE TABLE IF NOT EXISTS user_roles (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    role VARCHAR(50),                -- 'admin', 'manager', 'agent', 'viewer'
    permissions JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role);

-- ============================================
-- 9. ADVANCED CRM
-- ============================================

CREATE TABLE IF NOT EXISTS customer_profiles (
    customer_phone VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200),
    date_of_birth DATE,
    address TEXT,
    profile_picture VARCHAR(500),
    preferred_sports JSON,
    preferred_times JSON,
    vip_tier VARCHAR(20),
    loyalty_points INT DEFAULT 0,
    lifetime_value DECIMAL(10,2) DEFAULT 0,
    total_bookings INT DEFAULT 0,
    tags JSON,
    custom_fields JSON,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_profiles_email ON customer_profiles(email);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_vip_tier ON customer_profiles(vip_tier);

CREATE TABLE IF NOT EXISTS interaction_history (
    id VARCHAR(36) PRIMARY KEY,
    customer_phone VARCHAR(20),
    interaction_type VARCHAR(50),    -- 'call', 'sms', 'whatsapp', 'email', 'booking'
    summary TEXT,
    sentiment VARCHAR(20),
    outcome VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_interaction_customer ON interaction_history(customer_phone);
CREATE INDEX IF NOT EXISTS idx_interaction_type ON interaction_history(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interaction_created ON interaction_history(created_at);

-- ============================================
-- 10. REFERRALS & REWARDS
-- ============================================

CREATE TABLE IF NOT EXISTS referrals (
    id VARCHAR(36) PRIMARY KEY,
    referrer_phone VARCHAR(20),
    referee_phone VARCHAR(20),
    referral_code VARCHAR(20) UNIQUE,
    status VARCHAR(20),              -- 'pending', 'completed', 'rewarded', 'expired'
    referrer_reward DECIMAL(10,2),
    referee_reward DECIMAL(10,2),
    referee_first_booking_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_phone);
CREATE INDEX IF NOT EXISTS idx_referrals_referee ON referrals(referee_phone);
CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);

CREATE TABLE IF NOT EXISTS referral_rewards (
    id VARCHAR(36) PRIMARY KEY,
    referral_id VARCHAR(36),
    customer_phone VARCHAR(20),
    reward_amount DECIMAL(10,2),
    reward_type VARCHAR(50),         -- 'credit', 'discount', 'free_session'
    distributed BOOLEAN DEFAULT FALSE,
    distributed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referral_id) REFERENCES referrals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_referral_rewards_referral ON referral_rewards(referral_id);
CREATE INDEX IF NOT EXISTS idx_referral_rewards_customer ON referral_rewards(customer_phone);

-- ============================================
-- 11. BUSINESS INTELLIGENCE
-- ============================================

CREATE TABLE IF NOT EXISTS revenue_forecasts (
    id VARCHAR(36) PRIMARY KEY,
    forecast_date DATE,
    forecast_type VARCHAR(50),       -- 'daily', 'weekly', 'monthly'
    predicted_revenue DECIMAL(10,2),
    confidence_lower DECIMAL(10,2),
    confidence_upper DECIMAL(10,2),
    actual_revenue DECIMAL(10,2),
    accuracy_percent DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_revenue_forecasts_date ON revenue_forecasts(forecast_date);
CREATE INDEX IF NOT EXISTS idx_revenue_forecasts_type ON revenue_forecasts(forecast_type);

CREATE TABLE IF NOT EXISTS customer_ltv (
    customer_phone VARCHAR(20) PRIMARY KEY,
    current_ltv DECIMAL(10,2),
    predicted_ltv DECIMAL(10,2),
    acquisition_cost DECIMAL(10,2),
    roi_ratio DECIMAL(5,2),
    cohort VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_ltv_cohort ON customer_ltv(cohort);

-- ============================================
-- 12. NOTIFICATION PREFERENCES
-- ============================================

CREATE TABLE IF NOT EXISTS notification_preferences (
    customer_phone VARCHAR(20) PRIMARY KEY,
    sms_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    whatsapp_enabled BOOLEAN DEFAULT TRUE,
    push_enabled BOOLEAN DEFAULT TRUE,
    booking_confirmations BOOLEAN DEFAULT TRUE,
    booking_reminders BOOLEAN DEFAULT TRUE,
    marketing_messages BOOLEAN DEFAULT TRUE,
    do_not_disturb_start TIME,
    do_not_disturb_end TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SCHEMA VERSION TRACKING
-- ============================================

INSERT INTO schema_migrations (version, description, created_at)
VALUES ('8.0.0', 'Phase 8: Enterprise Scale & Revenue Acceleration', CURRENT_TIMESTAMP);

-- ============================================
-- END OF PHASE 8 SCHEMA
-- ============================================
