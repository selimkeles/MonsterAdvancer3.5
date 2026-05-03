"""
Rebuild all database files from source-of-truth SQL.

Output files (all gitignored build artifacts):
  backend/data/monsters.db   — legacy schema, still read by the running app
  backend/data/base.db       — legacy schema + atomic monster_presets tables (SRD catalog)
  backend/data/prod.db       — legacy schema + atomic monsters tables (user data)

Source files (committed):
  backend/data/seed.sql      — legacy schema + 562 SRD monsters
  backend/data/seed_v2.sql   — new atomic-table DDL ({ROOT} placeholder)

Usage:
    python backend/data/build_db.py
"""
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent

SEED_SQL     = HERE / "seed.sql"
SEED_V2_SQL  = HERE / "seed_v2.sql"
MONSTERS_DB  = HERE / "monsters.db"
BASE_DB      = HERE / "base.db"
PROD_DB      = HERE / "prod.db"
REPORT_PATH  = HERE / "migration_report.txt"


def _apply_sql(con: sqlite3.Connection, sql_path: Path, root: str | None = None) -> None:
    """Execute a SQL script, optionally substituting {ROOT} placeholder."""
    text = sql_path.read_text(encoding="utf-8")
    if root:
        text = text.replace("{ROOT}", root)
    con.executescript(text)
    con.commit()


def _build_legacy() -> None:
    """Rebuild monsters.db from seed.sql (drop-and-recreate)."""
    if MONSTERS_DB.exists():
        MONSTERS_DB.unlink()
    con = sqlite3.connect(MONSTERS_DB)
    try:
        _apply_sql(con, SEED_SQL)
    finally:
        con.close()
    print(f"[OK] monsters.db built from {SEED_SQL.name}")


def _build_v2(db_path: Path, root: str, src_db: Path) -> None:
    """
    Build a v2 DB: apply seed.sql (catalog + legacy monsters), then apply
    seed_v2.sql (new tables with given root name), then run the migrator.
    """
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            raise SystemExit(
                f"Cannot overwrite {db_path.name} — close any open SQLite connections "
                f"(SQLite Browser, the running server, etc.) and try again."
            )

    con = sqlite3.connect(db_path)
    try:
        # 1. Full legacy schema + data (same as monsters.db)
        _apply_sql(con, SEED_SQL)
        print(f"  {db_path.name}: seed.sql applied")

        # 2. New atomic tables
        _apply_sql(con, SEED_V2_SQL, root=root)
        print(f"  {db_path.name}: seed_v2.sql applied (root={root})")

    finally:
        con.close()

    # 3. Migrate legacy rows → new tables
    from migrate_to_v2 import migrate  # local import avoids circular deps

    src_con = sqlite3.connect(src_db)
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

    print("Building monsters.db (legacy) ...")
    _build_legacy()

    print("\nBuilding base.db (SRD presets) ...")
    _build_v2(BASE_DB, root="monster_presets", src_db=MONSTERS_DB)

    print("\nBuilding prod.db (user data) ...")
    # root="monster_builds" avoids collision with the legacy "monsters" table that
    # seed.sql creates; the router still reads legacy "monsters" until the cutover.
    _build_v2(PROD_DB, root="monster_builds", src_db=MONSTERS_DB)

    print("\nDone.")
    print(f"  monsters.db — legacy app DB (router reads this)")
    print(f"  base.db     — SRD preset catalog (monster_presets + child tables)")
    print(f"  prod.db     — user data (monster_builds + child tables; future app target)")
    if REPORT_PATH.exists():
        print(f"  migration_report.txt — quarantine log")


if __name__ == "__main__":
    build()
