
-- Complete PostgreSQL Database Schema for Customer Service Voice Agent

-- ============================================================================
-- CUSTOMERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_phone ON customers(phone_number);
CREATE INDEX idx_customers_email ON customers(email);

-- ============================================================================
-- AGENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS agents (
    agent_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'offline',
    current_call_count INT DEFAULT 0,
    max_concurrent_calls INT DEFAULT 1,
    skills JSONB,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_phone ON agents(phone_number);

-- ============================================================================
-- CALL QUEUE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_queue (
    queue_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    phone_number VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'waiting',
    priority INT DEFAULT 0,
    queue_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_agent_id INT REFERENCES agents(agent_id),
    assigned_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queue_status ON call_queue(status, priority DESC, queue_time);
CREATE INDEX idx_queue_agent ON call_queue(assigned_agent_id);
CREATE INDEX idx_queue_customer ON call_queue(customer_id);

-- ============================================================================
-- CALL SESSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_sessions (
    session_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    agent_id INT REFERENCES agents(agent_id),
    room_name VARCHAR(100) NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INT,
    handled_by VARCHAR(20) DEFAULT 'ai',
    transfer_count INT DEFAULT 0,
    sentiment VARCHAR(20),
    call_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_customer ON call_sessions(customer_id);
CREATE INDEX idx_sessions_agent ON call_sessions(agent_id);
CREATE INDEX idx_sessions_start_time ON call_sessions(start_time);
CREATE INDEX idx_sessions_room ON call_sessions(room_name);

-- ============================================================================
-- TRANSCRIPTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id SERIAL PRIMARY KEY,
    session_id INT REFERENCES call_sessions(session_id) ON DELETE CASCADE,
    speaker VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence FLOAT DEFAULT 1.0,
    sentiment VARCHAR(20)
);

CREATE INDEX idx_transcripts_session ON transcripts(session_id);
CREATE INDEX idx_transcripts_speaker ON transcripts(speaker);
CREATE INDEX idx_transcripts_timestamp ON transcripts(timestamp);

-- ============================================================================
-- CALLBACKS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS callbacks (
    callback_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    phone_number VARCHAR(20) NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'scheduled',
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_callbacks_customer ON callbacks(customer_id);
CREATE INDEX idx_callbacks_status ON callbacks(status);
CREATE INDEX idx_callbacks_scheduled_time ON callbacks(scheduled_time);

-- ============================================================================
-- CUSTOMER METADATA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_metadata (
    metadata_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, key)
);

CREATE INDEX idx_metadata_customer ON customer_metadata(customer_id);

-- ============================================================================
-- KNOWLEDGE BASE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    kb_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_category ON knowledge_base(category);

-- ============================================================================
-- CALL ANALYTICS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_analytics (
    analytics_id SERIAL PRIMARY KEY,
    session_id INT REFERENCES call_sessions(session_id),
    wait_time_seconds INT,
    talk_time_seconds INT,
    resolution_status VARCHAR(50),
    customer_satisfaction_score INT,
    ai_confidence_avg FLOAT,
    keywords JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analytics_session ON call_analytics(session_id);
CREATE INDEX idx_analytics_created ON call_analytics(created_at);

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- -- Insert sample agents
-- INSERT INTO agents (name, phone_number, status, skills, max_concurrent_calls)
-- VALUES 
--     ('Alice Johnson', '+1234567801', 'online', '{"departments": ["billing", "general"]}', 3),
--     ('Bob Smith', '+1234567802', 'online', '{"departments": ["technical", "general"]}', 2),
--     ('Carol Davis', '+1234567803', 'offline', '{"departments": ["sales", "general"]}', 2)
-- ON CONFLICT DO NOTHING;

-- -- Insert sample customers
-- INSERT INTO customers (phone_number, name, email)
-- VALUES 
--     ('+1234567890', 'John Doe', 'john@example.com'),
--     ('+1234567891', 'Jane Smith', 'jane@example.com'),
--     ('+1234567892', 'Mike Johnson', 'mike@example.com')
-- ON CONFLICT DO NOTHING;

-- -- Insert sample knowledge base
-- INSERT INTO knowledge_base (title, content, category)
-- VALUES 
--     ('Password Reset', 'To reset your password, visit the login page and click Forgot Password. You will receive a reset link via email.', 'account'),
--     ('Billing Questions', 'For billing inquiries, you can view your invoices in the account dashboard or contact our billing department.', 'billing'),
--     ('Technical Support', 'For technical issues, please provide your account number and describe the problem. Our technical team is available 24/7.', 'technical')
-- ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS outbound_calls (
    id SERIAL PRIMARY KEY,
    sip_call_id VARCHAR(255) UNIQUE NOT NULL,
    participant_id VARCHAR(255) NOT NULL,
    room_name VARCHAR(255) NOT NULL,
    to_number VARCHAR(50) NOT NULL,
    from_number VARCHAR(50) NOT NULL,
    trunk_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'initiating',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_outbound_calls_status ON outbound_calls(status);
CREATE INDEX idx_outbound_calls_created_at ON outbound_calls(created_at);
CREATE INDEX idx_outbound_calls_to_number ON outbound_calls(to_number);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_outbound_calls_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_outbound_calls
    BEFORE UPDATE ON outbound_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_outbound_calls_updated_at();