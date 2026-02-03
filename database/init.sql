-- ============================================
-- SENTINEL STREAM DATABASE SCHEMA
-- Enterprise Fraud Detection Platform
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'analyst',  -- admin, analyst, viewer
    department VARCHAR(100),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Insert default admin user (password: admin123)
INSERT INTO users (email, password_hash, full_name, role, department) VALUES
('admin@sentinel.io', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aLKbFIGq9K6Kxe', 'System Admin', 'admin', 'IT Security'),
('analyst@sentinel.io', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aLKbFIGq9K6Kxe', 'John Analyst', 'analyst', 'Fraud Operations'),
('viewer@sentinel.io', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aLKbFIGq9K6Kxe', 'Jane Viewer', 'viewer', 'Compliance');

-- ============================================
-- CUSTOMERS
-- ============================================
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_id VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'USA',
    risk_score DECIMAL(5,2) DEFAULT 0.0,
    risk_level VARCHAR(20) DEFAULT 'LOW',  -- LOW, MEDIUM, HIGH, CRITICAL
    total_transactions INTEGER DEFAULT 0,
    total_spent DECIMAL(15,2) DEFAULT 0.0,
    total_alerts INTEGER DEFAULT 0,
    first_transaction_at TIMESTAMPTZ,
    last_transaction_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_card_id ON customers(card_id);
CREATE INDEX idx_customers_risk_level ON customers(risk_level);
CREATE INDEX idx_customers_risk_score ON customers(risk_score DESC);

-- ============================================
-- TRANSACTIONS
-- ============================================
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    card_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    merchant_category VARCHAR(100),
    merchant_name VARCHAR(255),
    location VARCHAR(255),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',  -- completed, pending, declined, flagged
    fraud_score DECIMAL(5,4),
    is_fraud BOOLEAN DEFAULT false,
    processing_time_ms DECIMAL(10,3),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_customer FOREIGN KEY (card_id) REFERENCES customers(card_id) ON DELETE SET NULL
);

CREATE INDEX idx_transactions_card_id ON transactions(card_id);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp DESC);
CREATE INDEX idx_transactions_is_fraud ON transactions(is_fraud);
CREATE INDEX idx_transactions_fraud_score ON transactions(fraud_score DESC);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_merchant_category ON transactions(merchant_category);

-- Partitioning for performance (by month)
-- In production, you'd implement table partitioning here

-- ============================================
-- FRAUD ALERTS
-- ============================================
CREATE TABLE fraud_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(100) NOT NULL,
    card_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    location VARCHAR(255),
    merchant_category VARCHAR(100),
    
    -- Fraud detection results
    fraud_score DECIMAL(5,4) NOT NULL,
    fraud_reason TEXT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    velocity_triggered BOOLEAN DEFAULT false,
    velocity_count INTEGER DEFAULT 0,
    
    -- Processing info
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    latency_ms DECIMAL(10,3),
    model_version VARCHAR(50),
    
    -- Status
    status VARCHAR(20) DEFAULT 'new',  -- new, reviewing, escalated, resolved, false_positive
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

CREATE INDEX idx_alerts_card_id ON fraud_alerts(card_id);
CREATE INDEX idx_alerts_status ON fraud_alerts(status);
CREATE INDEX idx_alerts_risk_level ON fraud_alerts(risk_level);
CREATE INDEX idx_alerts_detected_at ON fraud_alerts(detected_at DESC);
CREATE INDEX idx_alerts_fraud_score ON fraud_alerts(fraud_score DESC);

-- ============================================
-- CASES (Investigation Management)
-- ============================================
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Related entities
    alert_id UUID,
    customer_id UUID,
    card_id VARCHAR(50),
    
    -- Case details
    priority VARCHAR(20) DEFAULT 'medium',  -- low, medium, high, critical
    status VARCHAR(20) DEFAULT 'open',  -- open, investigating, pending_info, escalated, resolved, closed
    category VARCHAR(50),  -- velocity_fraud, identity_theft, card_testing, friendly_fraud, other
    
    -- Financial impact
    total_amount DECIMAL(15,2) DEFAULT 0.0,
    potential_loss DECIMAL(15,2) DEFAULT 0.0,
    recovered_amount DECIMAL(15,2) DEFAULT 0.0,
    
    -- Assignment
    assigned_to UUID,
    assigned_at TIMESTAMPTZ,
    escalated_to UUID,
    escalated_at TIMESTAMPTZ,
    
    -- Resolution
    resolution VARCHAR(50),  -- confirmed_fraud, false_positive, inconclusive, customer_error
    resolution_notes TEXT,
    resolved_by UUID,
    resolved_at TIMESTAMPTZ,
    
    -- SLA tracking
    sla_due_at TIMESTAMPTZ,
    sla_breached BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_alert FOREIGN KEY (alert_id) REFERENCES fraud_alerts(id),
    CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
    CONSTRAINT fk_assigned FOREIGN KEY (assigned_to) REFERENCES users(id),
    CONSTRAINT fk_escalated FOREIGN KEY (escalated_to) REFERENCES users(id),
    CONSTRAINT fk_resolved FOREIGN KEY (resolved_by) REFERENCES users(id)
);

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_assigned_to ON cases(assigned_to);
CREATE INDEX idx_cases_created_at ON cases(created_at DESC);
CREATE INDEX idx_cases_sla_due_at ON cases(sla_due_at);

-- ============================================
-- CASE COMMENTS
-- ============================================
CREATE TABLE case_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL,
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT true,  -- internal note vs customer-visible
    attachments JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_case FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_case_comments_case_id ON case_comments(case_id);
CREATE INDEX idx_case_comments_created_at ON case_comments(created_at DESC);

-- ============================================
-- CASE ACTIVITY LOG (Audit Trail)
-- ============================================
CREATE TABLE case_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(50) NOT NULL,  -- created, assigned, status_changed, commented, escalated, resolved
    old_value TEXT,
    new_value TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_case FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_case_activities_case_id ON case_activities(case_id);
CREATE INDEX idx_case_activities_created_at ON case_activities(created_at DESC);

-- ============================================
-- FRAUD RULES
-- ============================================
CREATE TABLE fraud_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Rule definition
    rule_type VARCHAR(50) NOT NULL,  -- velocity, amount, location, time, pattern, ml_threshold
    conditions JSONB NOT NULL,  -- Flexible rule conditions
    action VARCHAR(50) NOT NULL,  -- flag, block, alert, review
    risk_weight DECIMAL(5,2) DEFAULT 1.0,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,  -- Lower = higher priority
    
    -- Performance tracking
    total_triggers INTEGER DEFAULT 0,
    true_positives INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    
    -- Metadata
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_created_by FOREIGN KEY (created_by) REFERENCES users(id),
    CONSTRAINT fk_updated_by FOREIGN KEY (updated_by) REFERENCES users(id)
);

CREATE INDEX idx_rules_is_active ON fraud_rules(is_active);
CREATE INDEX idx_rules_rule_type ON fraud_rules(rule_type);

-- Insert default rules
INSERT INTO fraud_rules (name, description, rule_type, conditions, action, risk_weight, is_active) VALUES
('High Velocity', 'More than 5 transactions in 60 seconds', 'velocity', '{"count_threshold": 5, "window_seconds": 60}', 'flag', 2.0, true),
('Large Amount', 'Transaction over $5,000', 'amount', '{"min_amount": 5000}', 'flag', 1.5, true),
('Night Transactions', 'Transactions between 2-5 AM', 'time', '{"start_hour": 2, "end_hour": 5}', 'flag', 1.2, true),
('High Risk Location', 'Transaction from high-risk countries', 'location', '{"countries": ["VPN", "TOR", "Proxy"]}', 'flag', 2.5, true),
('Card Testing Pattern', 'Multiple small transactions under $2', 'pattern', '{"max_amount": 2, "min_count": 3, "window_minutes": 10}', 'block', 3.0, true),
('ML Threshold High', 'ML model score above 0.8', 'ml_threshold', '{"min_score": 0.8}', 'flag', 2.0, true),
('Impossible Travel', 'Card used in distant locations within short time', 'location', '{"max_speed_kmh": 1000, "window_hours": 2}', 'flag', 3.0, true);

-- ============================================
-- ANALYTICS AGGREGATES (Pre-computed)
-- ============================================
CREATE TABLE analytics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    
    -- Transaction metrics
    total_transactions INTEGER DEFAULT 0,
    total_amount DECIMAL(20,2) DEFAULT 0.0,
    avg_transaction_amount DECIMAL(15,2) DEFAULT 0.0,
    
    -- Fraud metrics
    total_alerts INTEGER DEFAULT 0,
    confirmed_frauds INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    fraud_amount DECIMAL(20,2) DEFAULT 0.0,
    fraud_rate DECIMAL(8,4) DEFAULT 0.0,
    
    -- Performance metrics
    avg_detection_latency_ms DECIMAL(10,3) DEFAULT 0.0,
    p95_detection_latency_ms DECIMAL(10,3) DEFAULT 0.0,
    
    -- Case metrics
    cases_opened INTEGER DEFAULT 0,
    cases_resolved INTEGER DEFAULT 0,
    avg_resolution_hours DECIMAL(10,2) DEFAULT 0.0,
    
    -- Rule metrics
    velocity_violations INTEGER DEFAULT 0,
    rule_triggers JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_daily_date ON analytics_daily(date DESC);

-- ============================================
-- NOTIFICATIONS
-- ============================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    type VARCHAR(50) NOT NULL,  -- alert, case_assigned, case_updated, system
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================
-- SYSTEM SETTINGS
-- ============================================
CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_settings (key, value, description) VALUES
('fraud_score_threshold', '0.7', 'Minimum fraud score to trigger alert'),
('velocity_window_seconds', '60', 'Time window for velocity checks'),
('velocity_threshold', '5', 'Max transactions per card in window'),
('sla_critical_hours', '2', 'SLA for critical cases in hours'),
('sla_high_hours', '8', 'SLA for high priority cases'),
('sla_medium_hours', '24', 'SLA for medium priority cases'),
('sla_low_hours', '72', 'SLA for low priority cases'),
('notification_channels', '["websocket", "email"]', 'Enabled notification channels');

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-generate case number
CREATE OR REPLACE FUNCTION generate_case_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.case_number := 'CASE-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || 
                       LPAD(NEXTVAL('case_number_seq')::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE SEQUENCE IF NOT EXISTS case_number_seq START 1;

CREATE TRIGGER trigger_generate_case_number
    BEFORE INSERT ON cases
    FOR EACH ROW
    WHEN (NEW.case_number IS NULL)
    EXECUTE FUNCTION generate_case_number();

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_cases_updated_at BEFORE UPDATE ON cases FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_alerts_updated_at BEFORE UPDATE ON fraud_alerts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_rules_updated_at BEFORE UPDATE ON fraud_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- VIEWS
-- ============================================

-- Dashboard KPIs View
CREATE OR REPLACE VIEW v_dashboard_kpis AS
SELECT 
    (SELECT COUNT(*) FROM transactions WHERE created_at >= NOW() - INTERVAL '24 hours') AS transactions_24h,
    (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE created_at >= NOW() - INTERVAL '24 hours') AS volume_24h,
    (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '24 hours') AS alerts_24h,
    (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '24 hours' AND risk_level = 'CRITICAL') AS critical_alerts_24h,
    (SELECT COUNT(*) FROM cases WHERE status = 'open') AS open_cases,
    (SELECT COUNT(*) FROM cases WHERE sla_breached = true AND status NOT IN ('resolved', 'closed')) AS sla_breached,
    (SELECT COALESCE(AVG(latency_ms), 0) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '1 hour') AS avg_latency_ms;

-- Alert summary by risk level
CREATE OR REPLACE VIEW v_alerts_by_risk AS
SELECT 
    risk_level,
    COUNT(*) as count,
    COALESCE(SUM(amount), 0) as total_amount
FROM fraud_alerts
WHERE detected_at >= NOW() - INTERVAL '24 hours'
GROUP BY risk_level;

-- Top fraud patterns
CREATE OR REPLACE VIEW v_top_patterns AS
SELECT 
    fraud_reason,
    COUNT(*) as count
FROM fraud_alerts
WHERE detected_at >= NOW() - INTERVAL '7 days'
GROUP BY fraud_reason
ORDER BY count DESC
LIMIT 10;

COMMIT;
