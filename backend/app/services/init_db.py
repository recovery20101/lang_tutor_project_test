from pathlib import Path
import sqlparse
from sqlalchemy import text

from app.database import async_session_factory

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SQL_FILE_PATH = BASE_DIR / "app" / "migrations" / "initial_data.sql"


async def import_initial_data_if_empty() -> None:
    """Imports initial seed data into the database if rule_explanations table is empty."""
    async with async_session_factory() as db:
        try:
            print("🚀 Checking for initial data in the database...")

            result = await db.execute(text("SELECT COUNT(*) FROM rule_explanations;"))
            count = result.scalar()

            if count == 0:
                print("📝 Database is empty. Starting import from initial_data.sql...")

                if not SQL_FILE_PATH.exists():
                    print(f"⚠️ Dump file not found at path: {SQL_FILE_PATH}. Import skipped.")
                    return

                try:
                    with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    with open(SQL_FILE_PATH, "r", encoding="utf-16") as f:
                        lines = f.readlines()

                clean_lines = [
                    line for line in lines
                    if not line.strip().startswith("\\")
                ]
                clean_sql_script = "".join(clean_lines)

                statements = sqlparse.split(clean_sql_script)

                for stmt in statements:
                    stmt_clean = stmt.strip()
                    if not stmt_clean or "alembic_version" in stmt_clean:
                        continue

                    await db.execute(text(stmt_clean))

                await db.commit()
                print("✅ Import completed successfully!")
            else:
                print(f"ℹ️ Database already contains content (records: {count}). Import not required.")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error during automatic data import to DB: {e}")
