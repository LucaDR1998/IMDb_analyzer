import os
import psycopg2
from psycopg2.extras import execute_values

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "analyzerdatabase"),
        user=os.getenv("DB_USER", "analyzer"),
        password=os.getenv("DB_PASSWORD", "analyzerpass"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )

def init_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentiments (
            id SERIAL PRIMARY KEY,
            review TEXT,
            label TEXT,
            score FLOAT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_results_to_db(results):
    conn = get_connection()
    cur = conn.cursor()

    execute_values(cur,
        "INSERT INTO sentiments (review, label, score) VALUES %s",
        [(r['review'], r['label'], r['score']) for r in results]
    )

    conn.commit()
    cur.close()
    conn.close()
    print("# Results saved in DB")
