import psycopg2
from datetime import datetime, timezone
from db.config import DB_CONFIG

class Postgre:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rating_analysis (
                id SERIAL PRIMARY KEY,
                movie_title TEXT NOT NULL,
                comment TEXT NOT NULL,
                true_rating REAL,
                predicted_rating REAL,
                delta REAL,
                analysis_timestamp TIMESTAMPTZ
            )
        """)
        self.conn.commit()

    def save_rating_results(self, movie_title, results):
        now = datetime.now(timezone.utc)
        for row in results:
            # validate data fields
            if not all(k in row for k in ("comment", "true_rating", "predicted_rating", "delta")):
                continue  # skip incompleted rows

            comment = row["comment"] or ""
            true_rating = float(row["true_rating"])
            predicted_rating = float(row["predicted_rating"])
            delta = float(row["delta"])

            # validate numbers
            if not isinstance(true_rating, (int, float)) or not isinstance(predicted_rating, (int, float)):
                continue

            self.cursor.execute("""
                INSERT INTO rating_analysis (
                    movie_title, comment, true_rating, predicted_rating, delta, analysis_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (movie_title, comment, true_rating, predicted_rating, delta, now))

        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
