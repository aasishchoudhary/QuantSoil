"""Idempotent PostgreSQL bootstrap for deployment.

Migration files are deliberately append-only and guarded by IF NOT EXISTS /
IF NOT EXISTS column clauses where supported. This command does not store or
print credentials.
"""
from __future__ import annotations
import os
from pathlib import Path

def main() -> None:
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise SystemExit("DATABASE_URL is required")
    import psycopg
    root = Path(__file__).resolve().parents[2]
    paths = sorted((root / "db" / "migrations").glob("*.sql")) + sorted((root / "migrations").glob("*.sql"))
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            for path in paths:
                cursor.execute(path.read_text(encoding="utf-8"))
        connection.commit()
    print(f"applied {len(paths)} migration files")

if __name__ == "__main__":
    main()
