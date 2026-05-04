"""
Rebuild all database files from source-of-truth SQL.

Output files (all gitignored build artifacts):
  backend/data/base.db   — catalog + monster_presets tables (SRD read-only)
  backend/data/prod.db   — catalog + monster_builds tables (user data)

Source files (committed):
  backend/data/seed.sql      — schema + 562 SRD monsters (catalog tables)
  backend/data/seed_v2.sql   — new atomic-table DDL ({ROOT} placeholder)

Usage:
    python backend/data/build_db.py
"""
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent

SEED_SQL    = HERE / "seed.sql"
SEED_V2_SQL = HERE / "seed_v2.sql"
BASE_DB     = HERE / "base.db"
PROD_DB     = HERE / "prod.db"
REPORT_PATH = HERE / "migration_report.txt"


def _apply_sql(con: sqlite3.Connection, sql_path: Path, root: str | None = None) -> None:
    """Execute a SQL script, optionally substituting {ROOT} placeholder."""
    text = sql_path.read_text(encoding="utf-8")
    if root:
        text = text.replace("{ROOT}", root)
    con.executescript(text)
    con.commit()


def _unlink_safe(db_path: Path) -> None:
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            raise SystemExit(
                f"Cannot overwrite {db_path.name} — close any open SQLite connections "
                "(SQLite Browser, running server, etc.) and try again."
            )


def _build_v2(db_path: Path, root: str) -> None:
    """
    Build a v2 DB:
      1. Apply seed.sql  (catalog tables + legacy monster data)
      2. Apply seed_v2.sql  (new atomic tables for this root name)
      3. Run migrator  (parse legacy rows into new tables)
    """
    _unlink_safe(db_path)

    con = sqlite3.connect(db_path)
    try:
        _apply_sql(con, SEED_SQL)
        print(f"  {db_path.name}: seed.sql applied")

        _apply_sql(con, SEED_V2_SQL, root=root)
        print(f"  {db_path.name}: seed_v2.sql applied (root={root})")
    finally:
        con.close()

    from migrate_to_v2 import migrate

    # Migrator reads legacy tables from the same DB it just built
    src_con = sqlite3.connect(db_path)
    dst_con = sqlite3.connect(db_path)
    try:
        migrate(src_con, dst_con, root=root, report_path=REPORT_PATH)
    finally:
        src_con.close()
        dst_con.close()

    print(f"[OK] {db_path.name} built (root={root})")


def build() -> None:
    if not SEED_SQL.exists():
        raise SystemExit(f"seed.sql not found at {SEED_SQL}")
    if not SEED_V2_SQL.exists():
        raise SystemExit(f"seed_v2.sql not found at {SEED_V2_SQL}")

    print("Building base.db (SRD presets) ...")
    _build_v2(BASE_DB, root="monster_presets")

    print("\nBuilding prod.db (user data) ...")
    # root="monster_builds" avoids collision with legacy "monsters" table from seed.sql
    _build_v2(PROD_DB, root="monster_builds")

    print("\nDone.")
    print("  base.db  — SRD preset catalog (monster_presets + child tables)")
    print("  prod.db  — user data (monster_builds + child tables)")
    if REPORT_PATH.exists():
        print("  migration_report.txt — quarantine log")


if __name__ == "__main__":
    build()
