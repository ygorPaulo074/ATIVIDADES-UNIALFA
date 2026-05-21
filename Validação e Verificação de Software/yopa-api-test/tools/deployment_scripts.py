"""
Deployment artifact generation: SQL schema, Dockerfile, docker-compose.yml.
Called by setup.py at the end of the initial configuration wizard.
"""
import os


# ── SQL Schema ─────────────────────────────────────────────────────────────────

def create_sql_scripts() -> None:
    sql = """-- =============================================================
-- AI-ChatBot — Schema SQL
-- PostgreSQL 14+
-- =============================================================

-- agents
CREATE TABLE agents (
    agent_id          VARCHAR(64)   PRIMARY KEY,
    name              VARCHAR(255)  NOT NULL,
    owner             VARCHAR(64)   NOT NULL,
    api_key_hash      VARCHAR(64)   NOT NULL UNIQUE,
    ai_model          VARCHAR(64),
    ai_api_key        TEXT,
    ai_validated      BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMP     NOT NULL,
    updated_at        TIMESTAMP     NOT NULL,
    active_since      TIMESTAMP,
    last_activity_at  TIMESTAMP,
    deleted_at        TIMESTAMP
);

-- agent_contexts (one row per version; current = MAX(version))
CREATE TABLE agent_contexts (
    id          SERIAL        PRIMARY KEY,
    agent_id    VARCHAR(64)   NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    version     INTEGER       NOT NULL DEFAULT 1,
    context     JSONB         NOT NULL DEFAULT '{}',
    changes     JSONB         NOT NULL DEFAULT '[]',
    updated_at  TIMESTAMP     NOT NULL,
    UNIQUE (agent_id, version)
);

-- user_contexts (one row per user+agent)
CREATE TABLE user_contexts (
    id           SERIAL        PRIMARY KEY,
    user_id      VARCHAR(64)   NOT NULL,
    agent_id     VARCHAR(64)   NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    created_at   TIMESTAMP     NOT NULL,
    updated_at   TIMESTAMP     NOT NULL,
    segment      VARCHAR(128),
    language     VARCHAR(16),
    form_answers JSONB,
    UNIQUE (user_id, agent_id)
);

-- sessions
CREATE TABLE sessions (
    session_id      VARCHAR(64)   PRIMARY KEY,
    agent_id        VARCHAR(64)   NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    user_id         VARCHAR(64),
    model           VARCHAR(64)   NOT NULL,
    started_at      TIMESTAMP     NOT NULL,
    ended_at        TIMESTAMP,
    total_messages  INTEGER       NOT NULL DEFAULT 0,
    input_tokens    INTEGER       NOT NULL DEFAULT 0,
    output_tokens   INTEGER       NOT NULL DEFAULT 0,
    total_tokens    INTEGER       NOT NULL DEFAULT 0,
    resolved        BOOLEAN       NOT NULL DEFAULT FALSE,
    escalated       BOOLEAN       NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP
);

-- session_history (persisted on session end)
CREATE TABLE session_history (
    session_id  VARCHAR(64)  PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    agent_id    VARCHAR(64)  NOT NULL,
    messages    JSONB        NOT NULL DEFAULT '[]'
);

-- scores (NLP scores aggregated per session)
CREATE TABLE scores (
    session_id               VARCHAR(64)   PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    agent_id                 VARCHAR(64)   NOT NULL,
    messages                 JSONB         NOT NULL DEFAULT '[]',
    avg_sentiment_score      FLOAT,
    sentiment_label          VARCHAR(16)   CHECK (sentiment_label IN ('positive', 'neutral', 'negative')),
    all_topics               JSONB,
    main_topic               VARCHAR(255),
    intent                   VARCHAR(128),
    avg_user_message_length  FLOAT,
    avg_response_time_ms     FLOAT,
    updated_at               TIMESTAMP     NOT NULL
);

-- insights (AI-generated, on demand)
CREATE TABLE insights (
    session_id        VARCHAR(64)   PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    agent_id          VARCHAR(64)   NOT NULL,
    generated_at      TIMESTAMP     NOT NULL,
    key_points        JSONB,
    suggested_actions JSONB,
    summary           TEXT
);

-- knowledge_files (uploaded knowledge base files per agent)
CREATE TABLE knowledge_files (
    file_id     VARCHAR(64)   PRIMARY KEY,
    agent_id    VARCHAR(64)   NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    filename    VARCHAR(255)  NOT NULL,
    file_type   VARCHAR(16)   NOT NULL CHECK (file_type IN ('csv', 'json', 'pdf', 'excel', 'txt', 'docx', 'url')),
    records     JSONB         NOT NULL DEFAULT '[]',
    uploaded_at TIMESTAMP     NOT NULL,
    updated_at  TIMESTAMP     NOT NULL
);

-- Indexes
CREATE INDEX idx_agent_contexts_agent_id   ON agent_contexts(agent_id);
CREATE INDEX idx_user_contexts_agent_id    ON user_contexts(agent_id);
CREATE INDEX idx_user_contexts_user_id     ON user_contexts(user_id);
CREATE INDEX idx_sessions_agent_id         ON sessions(agent_id);
CREATE INDEX idx_sessions_user_id          ON sessions(user_id);
CREATE INDEX idx_sessions_deleted_at       ON sessions(deleted_at);
CREATE INDEX idx_session_history_agent_id  ON session_history(agent_id);
CREATE INDEX idx_scores_agent_id           ON scores(agent_id);
CREATE INDEX idx_insights_agent_id         ON insights(agent_id);
CREATE INDEX idx_knowledge_files_agent_id  ON knowledge_files(agent_id);
CREATE INDEX idx_agents_deleted_at         ON agents(deleted_at);
"""
    os.makedirs("scripts", exist_ok=True)
    with open("scripts/schema.sql", "w") as f:
        f.write(sql)
    print("  ✓ scripts/schema.sql generated.")


# ── Dockerfile ─────────────────────────────────────────────────────────────────

def generate_dockerfile(port: str = "8000") -> None:
    content = f"""FROM python:3.12-slim

WORKDIR /app

COPY requirements*.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm && python -m spacy download pt_core_news_sm

COPY . .

ENV RUN_MODE=production

EXPOSE {port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""
    with open("Dockerfile", "w") as f:
        f.write(content)
    print("  ✓ Dockerfile generated.")


# ── Docker Compose ─────────────────────────────────────────────────────────────

def generate_docker_compose(port: str = "8000", storage_type: str = "local") -> None:
    db_block = ""
    db_migrate_block = ""
    db_depends = ""
    db_volume = ""
    data_volume = ""
    db_env_override = ""

    if storage_type == "local":
        data_volume = "      - ./data:/app/data\n"

    if storage_type == "database":
        db_block = """
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
"""
        db_migrate_block = """
  db-migrate:
    image: postgres:16-alpine
    depends_on:
      db:
        condition: service_healthy
    environment:
      PGPASSWORD: ${DB_PASSWORD}
    volumes:
      - ./scripts/schema.sql:/schema.sql:ro
    command: >
      sh -c "if [ -f /schema.sql ];
             then psql -h db -U ${DB_USER} -d ${DB_NAME} -f /schema.sql;
             else echo 'schema.sql not found — skipping migration.'; fi"
    restart: "no"
"""
        db_depends = """      db-migrate:
        condition: service_completed_successfully
      redis:
        condition: service_started"""
        db_volume = "  db_data:\n"
        db_env_override = """    environment:
      DATABASE_URL: "postgresql://${DB_USER}:${DB_PASSWORD}@db:${DB_PORT}/${DB_NAME}"
"""

    api_depends = f"""    depends_on:
      - redis""" if storage_type != "database" else f"""    depends_on:
{db_depends}"""

    api_volumes = f"    volumes:\n{data_volume}" if data_volume else ""

    content = f"""services:
  api:
    build: .
    image: ai-chatbot-api:${{APP_VERSION}}
    ports:
      - "{port}:{port}"
    env_file:
      - .env
{db_env_override}{api_depends}
    restart: unless-stopped
{api_volumes}{db_block}{db_migrate_block}
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  redis_data:
{db_volume}"""
    with open("docker-compose.yml", "w") as f:
        f.write(content)
    print("  ✓ docker-compose.yml generated.")
