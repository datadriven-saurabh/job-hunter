CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    location VARCHAR(255) NOT NULL,
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    work_authorization VARCHAR(100) NOT NULL,
    base_resume_json JSONB NOT NULL,
    eeo_demographics_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_config (
    config_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    search_criteria_json JSONB NOT NULL,
    execution_preferences_json JSONB NOT NULL,
    llm_config_json JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_records (
    job_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    job_url TEXT NOT NULL,
    match_score FLOAT NOT NULL,
    classification VARCHAR(50) NOT NULL, -- HEADLESS_AUTO | HUMAN_IN_THE_LOOP_LINK
    status VARCHAR(50) NOT NULL,        -- DISCOVERED | MATCHED | QUEUED | TAILORED | APPLIED | INTERVIEWING | REJECTED | OFFER
    tailored_resume_path TEXT,
    tailored_cover_letter_path TEXT,
    extracted_form_fields JSONB,
    submission_logs_json JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional Table for Meta-Agent Selectors
CREATE TABLE IF NOT EXISTS dom_patches (
    patch_id VARCHAR(255) PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    selector_mappings JSONB NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_apps_status ON application_records(status);
CREATE INDEX IF NOT EXISTS idx_apps_classification ON application_records(classification);

CREATE TABLE IF NOT EXISTS resumes (
    resume_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    path TEXT NOT NULL,
    text TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS application_resume_selection (
    job_id TEXT PRIMARY KEY REFERENCES application_records(job_id) ON DELETE CASCADE,
    resume_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_cache (
    cache_key TEXT PRIMARY KEY,
    fetched_at REAL NOT NULL,
    payload TEXT NOT NULL
);

-- Search history includes filtered-out jobs. Changed filters/content are eligible again.
CREATE TABLE IF NOT EXISTS discovery_seen (
    job_key TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    criteria_hash TEXT NOT NULL,
    seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Reversible opportunity removal. Rediscovery does not revive the same record.
CREATE TABLE IF NOT EXISTS deleted_opportunities (
    job_id TEXT PRIMARY KEY REFERENCES application_records(job_id) ON DELETE CASCADE,
    deleted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
