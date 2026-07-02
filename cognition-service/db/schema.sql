-- Cognition Graph System — PostgreSQL Schema
-- Run: psql -U easykai -d cognition -f schema.sql

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════
-- Table 1: agents
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS agents (
    id              SERIAL PRIMARY KEY,
    agent_id        VARCHAR(64) UNIQUE NOT NULL,
    agent_name      VARCHAR(128) NOT NULL,
    owner_id        INTEGER,
    source_type     VARCHAR(32) DEFAULT 'Hermes',  -- Hermes | OpenClaw | API
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════
-- Table 2: skills
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS skills (
    id              SERIAL PRIMARY KEY,
    skill_id        VARCHAR(64) UNIQUE NOT NULL,
    skill_name      VARCHAR(256) NOT NULL,
    version         VARCHAR(16) DEFAULT '1.0.0'
);

-- ═══════════════════════════════════════════════
-- Table 3: predictions
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS predictions (
    id              SERIAL PRIMARY KEY,
    agent_id        VARCHAR(64) NOT NULL REFERENCES agents(agent_id),
    skill_id        VARCHAR(64) REFERENCES skills(skill_id),
    market          VARCHAR(16) NOT NULL CHECK (market IN ('CN','HK','US','CRYPTO','FUTURES')),
    ticker          VARCHAR(32) NOT NULL,
    stance          VARCHAR(8) NOT NULL CHECK (stance IN ('bullish','bearish','neutral')),
    confidence      INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    timeframe       VARCHAR(4) NOT NULL CHECK (timeframe IN ('1d','7d','30d','90d')),
    thesis_json     JSONB NOT NULL DEFAULT '[]',
    risk_level      VARCHAR(8) NOT NULL CHECK (risk_level IN ('low','medium','high')),
    price_target    DECIMAL(18,4),
    source_type     VARCHAR(32) DEFAULT 'Hermes',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    settlement_status VARCHAR(16) DEFAULT 'pending' CHECK (settlement_status IN ('pending','resolved'))
);

CREATE INDEX IF NOT EXISTS idx_predictions_agent ON predictions(agent_id);
CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker);
CREATE INDEX IF NOT EXISTS idx_predictions_market ON predictions(market);
CREATE INDEX IF NOT EXISTS idx_predictions_stance ON predictions(stance);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_settlement ON predictions(settlement_status, created_at);

-- ═══════════════════════════════════════════════
-- Table 4: prediction_results
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS prediction_results (
    id                  SERIAL PRIMARY KEY,
    prediction_id       INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    resolved_price      DECIMAL(18,4),
    target_hit          BOOLEAN DEFAULT FALSE,
    direction_correct   BOOLEAN DEFAULT FALSE,
    pnl_percent         DECIMAL(10,4),
    resolved_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_prediction ON prediction_results(prediction_id);

-- ═══════════════════════════════════════════════
-- Table 5: agent_reputation
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS agent_reputation (
    agent_id            VARCHAR(64) PRIMARY KEY REFERENCES agents(agent_id),
    total_predictions   INTEGER DEFAULT 0,
    accuracy_rate       DECIMAL(6,4) DEFAULT 0,
    avg_confidence      DECIMAL(6,4) DEFAULT 0,
    sharpe_like_score   DECIMAL(10,4) DEFAULT 0,
    reputation_score    DECIMAL(10,4) DEFAULT 0,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════
-- Table 6: thesis_embeddings (pgvector)
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS thesis_embeddings (
    id              SERIAL PRIMARY KEY,
    prediction_id   INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    thesis_text     TEXT NOT NULL,
    embedding       vector(384),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embedding ON thesis_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ═══════════════════════════════════════════════
-- Table 7: graph_edges (cognition graph)
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS graph_edges (
    id              SERIAL PRIMARY KEY,
    source_type     VARCHAR(16) NOT NULL,  -- agent | prediction | skill | topic
    source_id       VARCHAR(128) NOT NULL,
    target_type     VARCHAR(16) NOT NULL,
    target_id       VARCHAR(128) NOT NULL,
    relation        VARCHAR(32) NOT NULL,  -- SUPPORTS | OPPOSES | ANALYZES | USES_SKILL | AGREES_WITH | DISAGREES_WITH
    weight          DECIMAL(6,4) DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graph_source ON graph_edges(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_graph_target ON graph_edges(target_type, target_id);
