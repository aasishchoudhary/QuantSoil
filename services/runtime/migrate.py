"""Idempotent PostgreSQL bootstrap for deployment.

Migration files are deliberately append-only and guarded by IF NOT EXISTS /
IF NOT EXISTS column clauses where supported. This command does not store or
print credentials.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path

def _migration_paths(root: Path) -> list[Path]:
    paths = sorted((root / "db" / "migrations").glob("*.sql")) + sorted((root / "migrations").glob("*.sql"))
    if len({path.name for path in paths}) != len(paths):
        raise SystemExit("duplicate migration filename detected")
    return paths

def main() -> None:
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise SystemExit("DATABASE_URL is required")
    import psycopg
    root = Path(__file__).resolve().parents[2]
    paths = _migration_paths(root)
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("gods-eye:migrations",))
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_name TEXT PRIMARY KEY,
                    checksum_sha256 TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            applied = {
                row[0]: row[1]
                for row in cursor.execute(
                    "SELECT migration_name, checksum_sha256 FROM schema_migrations"
                ).fetchall()
            }
            applied_count = 0
            for path in paths:
                body = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
                previous = applied.get(path.name)
                if previous is not None:
                    if previous != checksum:
                        raise RuntimeError(f"migration checksum changed: {path.name}")
                    continue
                cursor.execute(body)
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name, checksum_sha256) VALUES (%s, %s)",
                    (path.name, checksum),
                )
                applied_count += 1
        connection.commit()
    print(f"applied {applied_count} new migration files; verified {len(paths) - applied_count} existing")

if __name__ == "__main__":
    main()
