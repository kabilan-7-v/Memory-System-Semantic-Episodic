import json
from db import get_conn
from embeddings import EmbeddingModel

embedder = EmbeddingModel()

WINDOW = "2 minutes"

def episodize_super_chat():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT super_chat_id,
                   jsonb_agg(jsonb_build_object(
                     'role', role, 'content', content
                   ) ORDER BY created_at) AS messages,
                   MIN(created_at) AS date_from,
                   MAX(created_at) AS date_to,
                   COUNT(*) AS cnt
            FROM super_chat_messages
            WHERE episodized = FALSE
              AND created_at < NOW() - INTERVAL '{WINDOW}'
            GROUP BY super_chat_id
        """)

        for r in cur.fetchall():
            cur.execute("""
                INSERT INTO episodes
                (user_id, source_type, source_id,
                 messages, message_count, date_from, date_to)
                SELECT user_id, 'super_chat', %s,
                       %s, %s, %s, %s
                FROM super_chat WHERE id=%s
                RETURNING id
            """, (
                r["super_chat_id"],
                json.dumps(r["messages"]),
                r["cnt"],
                r["date_from"],
                r["date_to"],
                r["super_chat_id"]
            ))
            episode_id = cur.fetchone()["id"]

            # Compute and store vector
            text = " ".join(m["content"] for m in r["messages"])
            vec = embedder.encode(text)
            cur.execute("UPDATE episodes SET vector = %s WHERE id = %s", (vec.tolist(), episode_id))

            cur.execute("""
                UPDATE super_chat_messages
                SET episodized=TRUE, episodized_at=NOW()
                WHERE super_chat_id=%s
            """, (r["super_chat_id"],))

        conn.commit()