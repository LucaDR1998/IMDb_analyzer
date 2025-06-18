import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "analyzerdatabase"),
    "user": os.getenv("DB_USER", "analyzer"),
    "password": os.getenv("DB_PASSWORD", "analyzerpass")
}
