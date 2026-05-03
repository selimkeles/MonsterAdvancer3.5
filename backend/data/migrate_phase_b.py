"""Phase B migration: normalized advancement + AC columns.

Adds to the monsters table:
  advancement_type, adv_max_hd, adv_size_thresholds  -- parsed from advancement text
  ac_total, ac_touch, ac_flat_footed                 -- parsed from armor_class text

Also replaces vague "Special (see below)" entries with descriptive prose
and fixes three grapple/attack column corruptions from the source XML.

Run:
    python backend/data/migrate_phase_b.py

After it completes it regenerates seed.sql so the new schema is committed.
"""
import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "monsters.db"
SEED_PATH = HERE / "seed.sql"

# ── Size name normalisations ─────────────────────────────────────────────────
# Old SRD used "Medium-size"; we normalise to the standard SIZE_ORDER names.
# "Colossal+" is an epic-only size beyond Colossal — map to Colossal since
# that is our ceiling.
_SIZE_ALIASES: dict[str, str] = {
    "medium-size": "Medium",
    "medium size": "Medium",
    "colossal+": "Colossal",
}


def _normalise_size(raw: str) -> str:
    s = raw.strip()
    return _SIZE_ALIASES.get(s.lower(), s.capitalize())


# ── Sentinel sets ────────────────────────────────────────────────────────────
# Both "-" and "None" appear in the source XML for the exact same meaning:
# "this creature has no standard HD advancement path."  They are the result
# of inconsistent data entry — there is no semantic distinction between them.
_NONE_SENTINELS: frozenset[str] = frozenset({
    "-",
    "none",
    # Single creature with a parenthetical explanation after "None"
    "none (abilities may vary by level of possessing spirit)",
})

# All variants of "advances by taking class levels".
_CLASS_VARIANTS: frozenset[str] = frozenset({
    "by character class",
    "by character class (usually psion)",
    "as character class",   # Uvuudaum
    "as character",         # Worm that Walks
})

# ── Segment regex ─────────────────────────────────────────────────────────────
# Matches one HD range segment, e.g.:
#   "4-6 HD (Small)"   "3 HD (Medium)"   "37+ HD (Gargantuan)"
#   "13-24 (Medium)"   (missing "HD" keyword — seen in real data)
# Group layout: (lower) (upper|None) (plus_sign|None) (size)
_SEG = re.compile(
    r'(\d+)'                        # group 1: lower bound
    r'(?:\s*[-–]\s*(\d+)|(\+))?'   # group 2: range upper  OR  group 3: open "+"
    r'\s*(?:HD\s*)?'                # optional "HD" keyword
    r'\(([^)]+)\)',                 # group 4: size name
    re.IGNORECASE,
)


def _classify(text: str | None) -> tuple[str, int | None, str]:
    """Return (advancement_type, adv_max_hd, adv_size_thresholds_json).

    advancement_type values:
      'hd'          – creature advances by gaining racial HD (bounded range)
      'hd_or_class' – creature may advance by HD *or* class levels (Sahuagin)
      'class'       – advances by class levels only
      'special'     – unique/exceptional advancement (e.g. Barghest)
      'none'        – no standard advancement path
    """
    if not text:
        return "none", None, "[]"

    norm = text.strip().lower()

    if norm in _NONE_SENTINELS:
        return "none", None, "[]"

    if norm in _CLASS_VARIANTS:
        return "class", None, "[]"

    # Descriptive text we wrote for Barghest/Greater Barghest
    if norm.startswith("grows into greater barghest"):
        return "special", None, "[]"
    if norm.startswith("none (fully grown"):
        return "none", None, "[]"

    is_mixed = "or by character class" in norm or "or character class" in norm

    thresholds: list[list] = []
    max_hd: int | None = None
    open_ended = False

    for m in _SEG.finditer(text):
        lower = int(m.group(1))
        upper_str = m.group(2)           # e.g. "6" from "4-6 HD"
        is_open = m.group(3) is not None  # explicit "+" suffix
        size = _normalise_size(m.group(4))
        thresholds.append([lower, size])
        if upper_str is not None:
            candidate = int(upper_str)
            if max_hd is None or candidate > max_hd:
                max_hd = candidate
        elif is_open:
            # "N+ HD (Size)" — genuinely no upper cap
            open_ended = True
        else:
            # "N HD (Size)" — single value; the lower IS the max for this segment
            if max_hd is None or lower > max_hd:
                max_hd = lower

    if thresholds:
        thresholds.sort(key=lambda t: t[0])
        if open_ended:
            max_hd = None  # no firm upper bound
        adv_type = "hd_or_class" if is_mixed else "hd"
        return adv_type, max_hd, json.dumps(thresholds)

    # Unrecognised format — treat conservatively as no advancement
    return "none", None, "[]"


# ── Per-creature text and type overrides ─────────────────────────────────────
# "Special (see below)" is only used by Barghest / Greater Barghest.
# Their advancement is driven by the Feed ability: a Barghest devours
# humanoid souls to grow in power, eventually becoming a Greater Barghest.
_TEXT_FIXES: dict[str, str] = {
    "Barghest": (
        "Grows into Greater Barghest by devouring humanoid souls "
        "(Feed ability; 6-9 HD)"
    ),
    "Greater Barghest": "None (fully grown; no further advancement)",
}

# Force a specific advancement_type for creatures whose fixed text would
# otherwise be misclassified by _classify().
_TYPE_FIXES: dict[str, str] = {
    "Barghest": "special",
    "Greater Barghest": "none",
}

# ── Grapple / attack column fixes ────────────────────────────────────────────
# These are XML source corruptions carried into the original DB.
#
# Athach: The XML author accidentally merged the attack line into the grapple
#   field, leaving the attack column NULL (stored as '0').  We split them.
#
# Weretiger (Tiger/Hybrid Form): attack column is '0' (was empty string in XML).
#   Natural-attack-only creatures in the SRD sometimes omit a single-attack
#   line; we derive it from the first primary attack in full_attack.
#
# Stirge: grapple = '-11 (+1 when attached)' is correct SRD data —
#   Diminutive size grapple is -11, with a +12 circumstance bonus when the
#   Stirge is attached to a victim.  Leave unchanged.
_GRAPPLE_ATTACK_FIXES: list[dict] = [
    {
        "name":    "Athach",
        "grapple": "+26",
        "attack":  "Morningstar +16 melee (3d6+8) or rock +9 ranged (2d6+8)",
    },
    {
        "name":    "Weretiger, Tiger Form",
        "grapple": None,   # leave grapple unchanged
        "attack":  "Claw +11 melee (1d8+7)",
    },
    {
        "name":    "Weretiger, Hybrid Form",
        "grapple": None,
        "attack":  "Claw +11 melee (1d8+7)",
    },
]


# ── AC text parser ───────────────────────────────────────────────────────────
# Source text format (all 562 rows):
#   "17 (+1 size, +2 Dex, +4 natural), touch 13, flat-footed 15"
# One outlier has an "AC " prefix:
#   "AC 23 (+5 Dex, ...), touch 16, flat-footed 18"
# Negative totals are theoretically possible (very low-level constructs, etc.)
# so we match a leading minus too.
_AC_RE = re.compile(
    r'^(?:AC\s+)?(-?\d+)'           # total AC (optional "AC " prefix)
    r'.*?touch\s+(-?\d+)'           # touch AC
    r'.*?flat-footed\s+(-?\d+)',    # flat-footed AC
    re.IGNORECASE | re.DOTALL,
)


def _parse_ac(text: str | None) -> tuple[int | None, int | None, int | None]:
    """Return (ac_total, ac_touch, ac_flat_footed) parsed from raw AC string.
    Returns (None, None, None) if text is missing or unparseable.
    """
    if not text:
        return None, None, None
    m = _AC_RE.match(text.strip())
    if not m:
        return None, None, None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


# ── Migration entry point ─────────────────────────────────────────────────────

def migrate() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found — run build_db.py first")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Add columns idempotently (SQLite < 3.35 has no IF NOT EXISTS for ADD COLUMN)
    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(monsters)")}
    for col, ddl in [
        ("advancement_type",    "TEXT"),
        ("adv_max_hd",          "INTEGER"),
        ("adv_size_thresholds", "TEXT"),
        ("ac_total",            "INTEGER"),
        ("ac_touch",            "INTEGER"),
        ("ac_flat_footed",      "INTEGER"),
    ]:
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE monsters ADD COLUMN {col} {ddl}")
            print(f"  Added column: {col}")
        else:
            print(f"  Column already exists: {col}")

    # Fix descriptive text for "Special (see below)" creatures
    for name, text in _TEXT_FIXES.items():
        cur.execute("UPDATE monsters SET advancement = ? WHERE name = ?", (text, name))
        if cur.rowcount:
            print(f"  Fixed advancement text: {name}")

    # Fix grapple/attack column corruptions
    for fix in _GRAPPLE_ATTACK_FIXES:
        name = fix["name"]
        if fix["grapple"] is not None:
            cur.execute("UPDATE monsters SET grapple = ? WHERE name = ?", (fix["grapple"], name))
            if cur.rowcount:
                print(f"  Fixed grapple: {name} -> {fix['grapple']!r}")
        cur.execute("UPDATE monsters SET attack = ? WHERE name = ?", (fix["attack"], name))
        if cur.rowcount:
            print(f"  Fixed attack:  {name} -> {fix['attack']!r}")

    con.commit()

    # Backfill AC columns from raw armor_class text
    ac_rows = cur.execute("SELECT id, armor_class FROM monsters").fetchall()
    ac_updates = []
    failed_ac = []
    for row in ac_rows:
        total, touch, flat = _parse_ac(row["armor_class"])
        if total is None:
            failed_ac.append(row["id"])
        ac_updates.append((total, touch, flat, row["id"]))
    cur.executemany(
        "UPDATE monsters SET ac_total=?, ac_touch=?, ac_flat_footed=? WHERE id=?",
        ac_updates,
    )
    con.commit()
    parsed_ok = len(ac_updates) - len(failed_ac)
    print(f"  AC columns backfilled: {parsed_ok}/{len(ac_updates)} parsed")
    if failed_ac:
        names = [r["name"] for r in cur.execute(
            f"SELECT name FROM monsters WHERE id IN ({','.join('?' * len(failed_ac))})",
            failed_ac,
        )]
        print(f"  WARNING: could not parse AC for: {names}")

    # Backfill every row
    rows = cur.execute("SELECT id, name, advancement FROM monsters").fetchall()
    updates = []
    for row in rows:
        forced_type = _TYPE_FIXES.get(row["name"])
        if forced_type:
            adv_type, max_hd, thresholds = forced_type, None, "[]"
        else:
            adv_type, max_hd, thresholds = _classify(row["advancement"])
        updates.append((adv_type, max_hd, thresholds, row["id"]))

    cur.executemany(
        "UPDATE monsters SET advancement_type=?, adv_max_hd=?, adv_size_thresholds=? WHERE id=?",
        updates,
    )
    con.commit()

    # Verification report
    cur.execute(
        "SELECT advancement_type, COUNT(*) n FROM monsters GROUP BY advancement_type ORDER BY n DESC"
    )
    print("\nAdvancement type distribution:")
    for t, n in cur.fetchall():
        print(f"  {n:4d}  {t}")

    # Check that no "Special (see below)" survived
    cur.execute("SELECT name FROM monsters WHERE advancement LIKE '%Special (see below)%'")
    leftovers = cur.fetchall()
    if leftovers:
        print(f"\nWARNING: 'Special (see below)' still present in: {[r[0] for r in leftovers]}")
    else:
        print("\n  No unresolved 'Special (see below)' entries — good.")

    # Check that grapple column has no embedded attack text
    cur.execute("SELECT name, grapple FROM monsters WHERE grapple LIKE '%Attack:%'")
    bad_grapple = cur.fetchall()
    if bad_grapple:
        print(f"  WARNING: grapple still contains attack data: {[r[0] for r in bad_grapple]}")
    else:
        print("  No grapple/attack column corruption remaining — good.")

    # Check that no attack column is the bare string '0'
    cur.execute("SELECT name FROM monsters WHERE attack = '0'")
    zero_attack = cur.fetchall()
    if zero_attack:
        print(f"  WARNING: attack = '0' still in: {[r[0] for r in zero_attack]}")
    else:
        print("  No attack='0' entries remaining — good.")

    # Check AC columns were populated
    null_ac = cur.execute("SELECT COUNT(*) FROM monsters WHERE ac_total IS NULL").fetchone()[0]
    if null_ac:
        print(f"  WARNING: {null_ac} monsters still have NULL ac_total")
    else:
        total_m = cur.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
        print(f"  AC columns fully populated for all {total_m} monsters — good.")

    # Dump new seed.sql
    print(f"\nDumping to {SEED_PATH} …")
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")
    print(f"Done. Commit seed.sql to persist the new schema.")

    con.close()


if __name__ == "__main__":
    migrate()
