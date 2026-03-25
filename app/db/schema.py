from app.db.database import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("PRAGMA table_info(conversations)")
    conversation_columns = [row[1] for row in cur.fetchall()]
    if "project_id" not in conversation_columns:
        cur.execute("ALTER TABLE conversations ADD COLUMN project_id INTEGER")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
        content TEXT NOT NULL,
        model_used TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        source_message_id INTEGER,
        fact_text TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        confidence REAL DEFAULT 0.7,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'superseded', 'outdated', 'uncertain', 'deleted')),
        visibility TEXT DEFAULT 'personal' CHECK(visibility IN ('general', 'personal', 'sensitive', 'restricted')),
        is_pinned INTEGER DEFAULT 0 CHECK(is_pinned IN (0, 1)),
        provenance TEXT DEFAULT 'explicit' CHECK(provenance IN ('explicit', 'inferred', 'imported', 'corrected')),
        supersedes_fact_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_confirmed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        FOREIGN KEY (source_message_id) REFERENCES messages(id),
        FOREIGN KEY (supersedes_fact_id) REFERENCES facts(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_facts_visibility ON facts(visibility)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_facts_conversation_id ON facts(conversation_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_facts_source_message_id ON facts(source_message_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_facts_created_at ON facts(created_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS episodic_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        summary TEXT NOT NULL,
        importance REAL DEFAULT 0.7,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reflections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        reflection_text TEXT NOT NULL,
        reflection_type TEXT DEFAULT 'general',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """)

    cur.execute("PRAGMA table_info(reflections)")
    reflection_columns = [row[1] for row in cur.fetchall()]

    structured_reflection_columns = {
        "user_insights": "TEXT",
        "preference_updates": "TEXT",
        "project_updates": "TEXT",
        "goal_updates": "TEXT",
        "potential_conflicts": "TEXT",
        "recommended_long_term_memories": "TEXT"
    }

    for col_name, col_type in structured_reflection_columns.items():
        if col_name not in reflection_columns:
            cur.execute(f"ALTER TABLE reflections ADD COLUMN {col_name} {col_type}")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_learnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learning_date TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS weekly_learnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_label TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_weekly_learnings_week_label ON weekly_learnings(week_label)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'archived')),
        priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'critical')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects(priority)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        goal_text TEXT NOT NULL,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'abandoned')),
        priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'critical')),
        target_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_goals_project_id ON goals(project_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS open_loops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        conversation_id INTEGER,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'open' CHECK(status IN ('open', 'resolved', 'dropped')),
        priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'critical')),
        due_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_open_loops_project_id ON open_loops(project_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_open_loops_conversation_id ON open_loops(conversation_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_open_loops_status ON open_loops(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_open_loops_priority ON open_loops(priority)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        source_ref_id INTEGER,
        recommendation_text TEXT NOT NULL,
        category TEXT DEFAULT 'memory_candidate',
        confidence REAL DEFAULT 0.75,
        status TEXT DEFAULT 'proposed' CHECK(status IN ('proposed', 'accepted', 'rejected', 'promoted')),
        decision_note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_recommendations_source_type ON memory_recommendations(source_type)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_recommendations_status ON memory_recommendations(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_memory_recommendations_category ON memory_recommendations(category)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS surfaced_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suggestion_type TEXT NOT NULL,
        suggestion_text TEXT NOT NULL,
        conversation_id INTEGER,
        surfaced_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_surfaced_suggestions_type ON surfaced_suggestions(suggestion_type)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_surfaced_suggestions_surfaced_at ON surfaced_suggestions(surfaced_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reasoning_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        project_id INTEGER,
        task TEXT NOT NULL,
        goal TEXT DEFAULT '',
        constraints TEXT DEFAULT '[]',
        assumptions TEXT DEFAULT '[]',
        candidate_actions TEXT DEFAULT '[]',
        selected_action TEXT,
        confidence REAL DEFAULT 0.5,
        self_check TEXT DEFAULT '{}',
        status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'active', 'completed', 'abandoned')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_reasoning_states_conversation_id ON reasoning_states(conversation_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_reasoning_states_project_id ON reasoning_states(project_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_reasoning_states_status ON reasoning_states(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_reasoning_states_updated_at ON reasoning_states(updated_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        project_id INTEGER,
        reasoning_state_id INTEGER,
        title TEXT NOT NULL,
        goal TEXT DEFAULT '',
        status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'active', 'completed', 'abandoned')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (reasoning_state_id) REFERENCES reasoning_states(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plans_conversation_id ON plans(conversation_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plans_project_id ON plans(project_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plans_reasoning_state_id ON plans(reasoning_state_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plan_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        step_order INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed', 'blocked', 'failed', 'skipped')),
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plan_steps_plan_id ON plan_steps(plan_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plan_steps_status ON plan_steps(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plan_steps_order ON plan_steps(plan_id, step_order)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plan_step_dependencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        step_id INTEGER NOT NULL,
        depends_on_step_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans(id),
        FOREIGN KEY (step_id) REFERENCES plan_steps(id),
        FOREIGN KEY (depends_on_step_id) REFERENCES plan_steps(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plan_step_deps_plan_id ON plan_step_dependencies(plan_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plan_step_deps_step_id ON plan_step_dependencies(step_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_plan_step_deps_depends_on ON plan_step_dependencies(depends_on_step_id)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS step_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        step_id INTEGER NOT NULL,
        attempt_number INTEGER NOT NULL DEFAULT 1,
        action_type TEXT DEFAULT 'manual',
        action_payload TEXT DEFAULT '{}',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
        result_summary TEXT DEFAULT '',
        verification_status TEXT DEFAULT 'unverified' CHECK(verification_status IN ('unverified', 'verified', 'verification_failed')),
        error_message TEXT DEFAULT '',
        started_at TEXT,
        finished_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans(id),
        FOREIGN KEY (step_id) REFERENCES plan_steps(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_step_executions_plan_id ON step_executions(plan_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_step_executions_step_id ON step_executions(step_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_step_executions_status ON step_executions(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_step_executions_verification_status ON step_executions(verification_status)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tool_invocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_name TEXT NOT NULL,
        payload_signature TEXT DEFAULT '',
        success INTEGER DEFAULT 0 CHECK(success IN (0, 1)),
        error_message TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool_name ON tool_invocations(tool_name)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_tool_invocations_created_at ON tool_invocations(created_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS autonomy_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        reasoning_state_id INTEGER,
        status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'running', 'paused', 'completed', 'stopped', 'failed')),
        max_steps INTEGER DEFAULT 10,
        steps_executed INTEGER DEFAULT 0,
        max_tool_calls INTEGER DEFAULT 20,
        tool_calls_used INTEGER DEFAULT 0,
        stop_reason TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans(id),
        FOREIGN KEY (reasoning_state_id) REFERENCES reasoning_states(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_autonomy_runs_plan_id ON autonomy_runs(plan_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_autonomy_runs_reasoning_state_id ON autonomy_runs(reasoning_state_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_autonomy_runs_status ON autonomy_runs(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_autonomy_runs_updated_at ON autonomy_runs(updated_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS execution_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL UNIQUE,
        plan_id INTEGER NOT NULL,
        current_step_id INTEGER,
        current_execution_id INTEGER,
        status TEXT DEFAULT 'running' CHECK(status IN ('running', 'paused', 'completed', 'abandoned')),
        step_log TEXT DEFAULT '[]',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        FOREIGN KEY (plan_id) REFERENCES plans(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_sessions_conversation_id ON execution_sessions(conversation_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_sessions_status ON execution_sessions(status)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS execution_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id INTEGER,
        step_id INTEGER,
        plan_id INTEGER,
        event_type TEXT NOT NULL CHECK(event_type IN ('start', 'progress', 'retry', 'fail', 'verify', 'stuck', 'pause', 'resume', 'complete')),
        message TEXT DEFAULT '',
        confidence REAL,
        risk_level TEXT DEFAULT 'medium' CHECK(risk_level IN ('low', 'medium', 'high')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (execution_id) REFERENCES step_executions(id),
        FOREIGN KEY (step_id) REFERENCES plan_steps(id),
        FOREIGN KEY (plan_id) REFERENCES plans(id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_events_execution_id ON execution_events(execution_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_events_step_id ON execution_events(step_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_events_plan_id ON execution_events(plan_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_events_type ON execution_events(event_type)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_execution_events_created_at ON execution_events(created_at)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS successful_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        step_type TEXT NOT NULL,
        step_title_pattern TEXT DEFAULT '',
        solution_summary TEXT NOT NULL,
        strategy TEXT DEFAULT '',
        success_count INTEGER DEFAULT 1,
        last_used_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_successful_patterns_step_type ON successful_patterns(step_type)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_successful_patterns_success_count ON successful_patterns(success_count)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS project_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_type TEXT NOT NULL,
        failure_stage TEXT DEFAULT '',
        success_stage TEXT DEFAULT '',
        total_plans INTEGER DEFAULT 1,
        completed_plans INTEGER DEFAULT 0,
        failed_plans INTEGER DEFAULT 0,
        avg_steps_to_failure REAL DEFAULT 0,
        success_strategy TEXT DEFAULT '',
        insight TEXT DEFAULT '',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_project_patterns_type ON project_patterns(project_type)
    """)

    conn.commit()
    conn.close()
