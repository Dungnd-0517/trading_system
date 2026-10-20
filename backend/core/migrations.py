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
        for migration_path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            version = migration_path.stem
            applied = await connection.scalar(
                text("SELECT 1 FROM schema_migrations WHERE version = :version"),
                {"version": version},
            )
            if applied:
                continue

            script = migration_path.read_text(encoding="utf-8")
            for statement in script.split(";"):
                # Loại bỏ các dòng comment thuần túy và khoảng trắng thừa
                clean_lines = [
                    line for line in statement.splitlines()
                    if line.strip() and not line.strip().startswith("--")
                ]
                clean_sql = "\n".join(clean_lines).strip()
                if clean_sql:
                    await connection.execute(text(clean_sql))
            await connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )