from .db import get_conn
from .embeddings import EmbeddingModel

embedder = EmbeddingModel()


def create_tables():
    with get_conn() as conn, conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # --------------------
        # Super Chat
        # --------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS super_chat (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS super_chat_messages (
                id SERIAL PRIMARY KEY,
                super_chat_id INTEGER REFERENCES super_chat(id),
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                episodized BOOLEAN DEFAULT FALSE,
                episodized_at TIMESTAMP
            )
        """)

        # --------------------
        # Deep Dive
        # --------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deepdive_conversations (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                tenant_id TEXT,
                title VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS deepdive_messages (
                id SERIAL PRIMARY KEY,
                deepdive_conversation_id INTEGER REFERENCES deepdive_conversations(id),
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # --------------------
        # Episodes
        # --------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                tenant_id TEXT,
                source_type VARCHAR(50) NOT NULL,  -- 'super_chat' or 'deepdive'
                source_id INTEGER NOT NULL,
                messages JSONB NOT NULL,
                message_count INTEGER NOT NULL,
                date_from TIMESTAMP NOT NULL,
                date_to TIMESTAMP NOT NULL,
                vector vector(384),  -- all-MiniLM-L6-v2
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # --------------------
        # Instances (archived episodes)
        # --------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                tenant_id TEXT,
                source_type VARCHAR(50) NOT NULL,
                source_id INTEGER NOT NULL,
                original_episode_id INTEGER NOT NULL,
                messages JSONB NOT NULL,
                message_count INTEGER NOT NULL,
                date_from TIMESTAMP NOT NULL,
                date_to TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # --------------------
        # Vector index (CRITICAL for scale)
        # --------------------
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_vector
            ON episodes USING ivfflat (vector vector_cosine_ops)
            WITH (lists = 100);
        """)

        conn.commit()

        # --------------------
        # Migration safety (ignore if already correct)
        # --------------------
        try:
            cur.execute("ALTER TABLE super_chat ALTER COLUMN user_id TYPE TEXT")
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE deepdive_conversations ALTER COLUMN user_id TYPE TEXT")
            cur.execute("ALTER TABLE deepdive_conversations ALTER COLUMN tenant_id TYPE TEXT")
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE episodes ALTER COLUMN user_id TYPE TEXT")
            cur.execute("ALTER TABLE episodes ALTER COLUMN tenant_id TYPE TEXT")
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE instances ALTER COLUMN user_id TYPE TEXT")
            cur.execute("ALTER TABLE instances ALTER COLUMN tenant_id TYPE TEXT")
        except Exception:
            pass

        conn.commit()

    print("✅ Tables and indexes created successfully.")

    # Backfill vectors for existing episodes
    populate_vectors()


def populate_vectors():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, messages
            FROM episodes
            WHERE vector IS NULL
        """)
        episodes = cur.fetchall()

        updated = 0
        for ep in episodes:
            messages = ep.get("messages")

            # Safety check
            if not messages or not isinstance(messages, list):
                continue

            text = " ".join(
                m.get("content", "")
                for m in messages
                if isinstance(m, dict) and m.get("content")
            ).strip()

            if not text:
                continue

            vec = embedder.encode(text)

            cur.execute(
                "UPDATE episodes SET vector = %s WHERE id = %s",
                (vec.tolist(), ep["id"])
            )
            updated += 1

        conn.commit()

    print(f"🧠 Populated vectors for {updated} episodes.")


if __name__ == "__main__":
    create_tables()
