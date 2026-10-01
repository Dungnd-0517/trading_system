from pathlib import Path

from sqlalchemy import text

from core.database import engine

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


async def run_migrations() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version VARCHAR(128) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
            )
        )
        migration_path = _MIGRATIONS_DIR / "0002_phase2_sprint1.sql"
        version = migration_path.stem
        applied = await connection.scalar(
            text("SELECT 1 FROM schema_migrations WHERE version = :version"),
            {"version": version},
        )
        if applied:
            return

        script = migration_path.read_text(encoding="utf-8")
        for statement in script.split(";"):
            if statement.strip():
                await connection.execute(text(statement))
        await connection.execute(
            text("INSERT INTO schema_migrations (version) VALUES (:version)"),
            {"version": version},
        )