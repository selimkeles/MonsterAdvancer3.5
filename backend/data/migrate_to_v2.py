"""
migrate_to_v2.py — Populate new atomic monster tables from legacy schema.

Called by build_db.py after seed_v2.sql has been applied.  Reads from the
legacy monsters / attacks / armor_class_components tables in `src_con` and
writes to the new tables (named by `root`) in `dst_con`.

Parsing decisions:
  - Feats:   comma-split respecting parens; strip "(B)"; separate base name from
             parenthetical parameter; look up by name in feats catalog.
  - Skills:  comma-split respecting parens; regex to separate name / bonus /
             conditional / asterisk.
  - HD:      regex for one or more "NdM[+-K]" chunks; first = racial, rest =
             class (rare multi-source HD like "8d8+56 plus 10d4+70").
  - Attacks: mapped 1-to-1 from legacy attacks table (already structured).
  - Saves:   parsed from the saves string "Fort +N, Ref +N, Will +N".
  - Grapple: parsed from the grapple string "+N".
  - HP:      extracted from hit_dice string "(N hp)".
  - Init:    parsed from initiative string "+N".

Quarantine (needs_review=1) triggers:
  - NULL ability scores on a non-class-leveled monster.
  - HD regex fails to match.
  - advancement_type='class' but no class level found in monster name.
  - ac_total is NULL.
  - Any skill or feat token fails to parse.

Usage (from build_db.py):
    from migrate_to_v2 import migrate
    migrate(src_con, dst_con, root="monster_presets",
            report_path=Path("backend/data/migration_report.txt"))
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# HD string parsing
# ─────────────────────────────────────────────────────────────────────────────
_HD_CHUNK_RE = re.compile(r'(\d+)d(\d+)(?:[+-]\d+)?')
_HP_RE = re.compile(r'\((\d+)\s*hp\)', re.IGNORECASE)


def _parse_hd(hd_text: str | None) -> tuple[int, int | None, list[tuple[int, int]]]:
    """
    Returns (racial_hd_count, racial_hd_die, extra_chunks).
    extra_chunks = [(count, die), ...] for 'plus NdM' segments (class HD).
    """
    if not hd_text:
        return 0, None, []
    chunks = _HD_CHUNK_RE.findall(hd_text)
    if not chunks:
        return 0, None, []
    racial_count = int(chunks[0][0])
    racial_die = int(chunks[0][1])
    extra = [(int(c), int(d)) for c, d in chunks[1:]]
    return racial_count, racial_die, extra


def _parse_hp(hd_text: str | None) -> int | None:
    if not hd_text:
        return None
    m = _HP_RE.search(hd_text)
    return int(m.group(1)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# Integer-from-signed-string (grapple, initiative)
# ─────────────────────────────────────────────────────────────────────────────
_SIGNED_INT_RE = re.compile(r'([+-]?\d+)')


def _parse_signed_int(text: str | None) -> int | None:
    if not text:
        return None
    m = _SIGNED_INT_RE.search(str(text).strip())
    return int(m.group(1)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# Saves string:  "Fort +2, Ref +5, Will +4"
# ─────────────────────────────────────────────────────────────────────────────
_SAVES_RE = re.compile(
    r'Fort\s+([+-]\d+).*?Ref\s+([+-]\d+).*?Will\s+([+-]\d+)',
    re.IGNORECASE,
)


def _parse_saves(saves_text: str | None) -> tuple[int | None, int | None, int | None]:
    if not saves_text:
        return None, None, None
    m = _SAVES_RE.search(saves_text)
    if not m:
        return None, None, None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


# ─────────────────────────────────────────────────────────────────────────────
# Class name extraction from monster name
# e.g. "Aboleth Mage, 10th-Level Wizard" → (10, "Wizard")
# ─────────────────────────────────────────────────────────────────────────────
_CLASS_NAME_RE = re.compile(
    r',\s*(\d+)(?:st|nd|rd|th)-Level\s+(.+)$', re.IGNORECASE
)

_KNOWN_CLASSES: set[str] = {
    "warrior", "aristocrat", "expert", "commoner", "adept",
    "fighter", "rogue", "barbarian", "ranger",
    "wizard", "sorcerer", "cleric", "druid", "bard",
    "paladin", "monk", "blackguard", "psion",
}


def _parse_class_from_name(name: str) -> tuple[int, str] | None:
    """Return (levels, canonical_class_name) or None."""
    m = _CLASS_NAME_RE.search(name or "")
    if not m:
        return None
    levels = int(m.group(1))
    raw = m.group(2).strip().rstrip(".")
    canonical = raw.title()  # "wizard" → "Wizard"
    return levels, canonical


# ─────────────────────────────────────────────────────────────────────────────
# Feat token parsing
# ─────────────────────────────────────────────────────────────────────────────
_BONUS_TAG_RE = re.compile(r'\s*\(\s*B\s*\)\s*$', re.IGNORECASE)
_PARAM_TAIL_RE = re.compile(r'^(.*?)\s*\(([^)]+)\)\s*$')


def _parse_feat_token(token: str) -> tuple[str, str | None, bool]:
    """
    Return (base_name, parameter, is_bonus).
    "Weapon Focus (bite)"  → ("Weapon Focus", "bite", False)
    "Dodge (B)"            → ("Dodge", None, True)
    "Power Attack"         → ("Power Attack", None, False)
    "Armor Proficiency (Heavy)" → found in catalog as full name → no param split needed
    """
    token = token.strip()
    is_bonus = bool(_BONUS_TAG_RE.search(token))
    if is_bonus:
        token = _BONUS_TAG_RE.sub("", token).strip()

    m = _PARAM_TAIL_RE.match(token)
    if m:
        base = m.group(1).strip()
        param = m.group(2).strip()
        return base, param, is_bonus
    return token, None, is_bonus


def _split_feat_string(text: str) -> list[str]:
    """Comma-split while respecting parentheses."""
    tokens: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            t = "".join(current).strip()
            if t:
                tokens.append(t)
            current = []
        else:
            current.append(ch)
    t = "".join(current).strip()
    if t:
        tokens.append(t)
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# Skill string parsing
# ─────────────────────────────────────────────────────────────────────────────
_SKILL_RE = re.compile(
    r'^(.*?)\s+([+-]\d+)'          # skill name and signed total bonus
    r'((?:\s+\([^)]*\))*)'         # optional conditionals like " (+16 underground)"
    r'(\*?)$'                       # optional asterisk footnote
)


def _split_skill_string(text: str) -> list[str]:
    """Comma-split while respecting parentheses."""
    tokens: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            t = "".join(current).strip()
            if t:
                tokens.append(t)
            current = []
        else:
            current.append(ch)
    t = "".join(current).strip()
    if t:
        tokens.append(t)
    return tokens


def _parse_skills(skills_text: str | None) -> list[tuple[str, int | None, str | None]]:
    """
    Returns list of (skill_name, total_bonus, conditional_text).
    conditional_text includes asterisk if present.
    """
    if not skills_text or skills_text.strip() in ("-", "—", ""):
        return []
    results = []
    for token in _split_skill_string(skills_text):
        m = _SKILL_RE.match(token.strip())
        if m:
            name = m.group(1).strip()
            bonus = int(m.group(2))
            cond = m.group(3).strip() or None
            asterisk = m.group(4)
            if asterisk:
                cond = (cond + " *") if cond else "*"
            results.append((name, bonus, cond))
        else:
            results.append((token, None, None))   # failed parse
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Special traits (special_attacks / special_qualities)
# ─────────────────────────────────────────────────────────────────────────────
_ABILITY_TYPE_RE = re.compile(r'\(\s*(Ex|Su|Sp)\s*\)$', re.IGNORECASE)


def _parse_special_list(
    text: str | None, kind: str
) -> list[dict]:
    if not text or text.strip() in ("-", "—", ""):
        return []
    rows = []
    for i, token in enumerate(text.split(",")):
        token = token.strip()
        if not token:
            continue
        m_ab = _ABILITY_TYPE_RE.search(token)
        ability_type = m_ab.group(1).upper() if m_ab else None
        name = _ABILITY_TYPE_RE.sub("", token).strip() if m_ab else token
        rows.append({
            "kind": kind,
            "name": name,
            "short_label": name,
            "ability_type": ability_type,
            "description": None,
            "order_index": i,
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Critical string
# ─────────────────────────────────────────────────────────────────────────────
def _crit_string(crit_range: str | None, crit_mult: int | None) -> str | None:
    base = (crit_range or "20").strip()
    mult = int(crit_mult or 2)
    parts = []
    if base != "20":
        parts.append(base)
    if mult != 2:
        parts.append(f"x{mult}")
    return "/".join(parts) if parts else None


# ─────────────────────────────────────────────────────────────────────────────
# is_primary derivation
# ─────────────────────────────────────────────────────────────────────────────
_SECONDARY_CATEGORIES = {"natural_Secondary", "weapon_OH"}


def _is_primary(use_category: str | None) -> int:
    return 0 if use_category in _SECONDARY_CATEGORIES else 1


# ─────────────────────────────────────────────────────────────────────────────
# feats.parameter_options backfill map
# ─────────────────────────────────────────────────────────────────────────────
_FEAT_PARAM_OPTIONS: dict[str, str] = {
    "Weapon Focus":                  "weapon",
    "Greater Weapon Focus":          "weapon",
    "Weapon Specialization":         "weapon",
    "Greater Weapon Specialization": "weapon",
    "Improved Critical":             "weapon",
    "Exotic Weapon Proficiency":     "weapon",
    "Spell Focus":                   "school",
    "Greater Spell Focus":           "school",
    "Skill Focus":                   "skill",
    "Ability Focus":                 "ability",
}


# ─────────────────────────────────────────────────────────────────────────────
# Main migration
# ─────────────────────────────────────────────────────────────────────────────

def migrate(
    src_con: sqlite3.Connection,
    dst_con: sqlite3.Connection,
    root: str,
    report_path: Path | None = None,
) -> int:
    """
    Reads legacy tables from src_con, writes new atomic tables (named by root)
    in dst_con.  Returns the number of monsters flagged needs_review=1.
    """
    src_con.row_factory = sqlite3.Row
    dst_con.row_factory = sqlite3.Row
    src = src_con.cursor()
    dst = dst_con.cursor()

    R = root  # shorthand

    # ── Build lookup: feat name (lower) → id ─────────────────────────────────
    feat_lookup: dict[str, int] = {}
    for row in dst.execute("SELECT id, name FROM feats"):
        feat_lookup[row["name"].strip().lower()] = row["id"]

    # ── Build lookup: class name (lower) → exists ─────────────────────────────
    class_names: set[str] = set()
    for row in dst.execute("SELECT name FROM classes"):
        class_names.add(row["name"].strip().lower())

    # ── Load all legacy monsters with their AC components ────────────────────
    monsters = src.execute("""
        SELECT m.*,
               ac.base_nat_armor,
               ac.base_armor,
               ac.base_armor_description,
               ac.base_deflection,
               ac.base_deflection_description,
               ac.base_shield,
               ac.base_shield_description,
               ac.base_dodge,
               ac.base_dodge_description
        FROM monsters m
        LEFT JOIN armor_class_components ac ON ac.monster_id = m.id
        ORDER BY m.id
    """).fetchall()

    # ── Load all legacy attacks ───────────────────────────────────────────────
    all_attacks = src.execute(
        "SELECT * FROM attacks ORDER BY monster_id, group_id, id"
    ).fetchall()

    # Group attacks by monster_id for fast lookup
    attacks_by_monster: dict[int, list] = {}
    for atk in all_attacks:
        attacks_by_monster.setdefault(atk["monster_id"], []).append(atk)

    # ── Accumulate rows for bulk insert ──────────────────────────────────────
    monster_rows:  list[dict] = []
    class_rows:    list[dict] = []
    attack_rows:   list[dict] = []
    feat_rows:     list[dict] = []
    skill_rows:    list[dict] = []
    trait_rows:    list[dict] = []

    report_lines:     list[str] = []
    needs_review_total = 0

    for mon in monsters:
        mid: int = mon["id"]
        review_reasons: list[str] = []

        # ── NULL ability score anomaly ────────────────────────────────────────
        # Constructs have no Con (and sometimes no Int/Str) by SRD design.
        # Undead have no Con. Class-leveled monsters use class ability scores.
        _NULL_SCORE_OK = {"Construct", "Undead"}
        has_null_ability = any(
            mon[col] is None for col in ("str", "dex", "con", "int", "wis", "cha")
        )
        if (has_null_ability
                and mon["advancement_type"] != "class"
                and (mon["type"] or "") not in _NULL_SCORE_OK):
            review_reasons.append("NULL ability score on non-class non-Construct/Undead monster")

        # ── HD + HP ──────────────────────────────────────────────────────────
        hd_text = mon["hit_dice"]
        racial_hd_count, racial_hd_die, extra_hd_chunks = _parse_hd(hd_text)
        if racial_hd_count == 0 and (mon["hd_count"] or 0) > 0:
            racial_hd_count = mon["hd_count"]
        if racial_hd_count == 0 and hd_text:
            review_reasons.append(f"HD regex failed: {hd_text!r}")
        hp = _parse_hp(hd_text)

        # ── Class levels ──────────────────────────────────────────────────────
        if mon["advancement_type"] == "class" or extra_hd_chunks:
            parsed_class = _parse_class_from_name(mon["name"] or "")
            if parsed_class:
                levels, class_name = parsed_class
                canonical = class_name if class_name.lower() in class_names else None
                class_rows.append({
                    "monster_id": mid,
                    "class_name": canonical,
                    "class_name_raw": class_name,
                    "levels": levels,
                    "order_index": 1,
                    "associated": 0,
                })
            elif mon["advancement_type"] == "class":
                review_reasons.append("advancement_type=class but no class level in name")

        # ── AC components ─────────────────────────────────────────────────────
        nat_armor    = mon["base_nat_armor"] or 0
        defl_bonus   = mon["base_deflection"] or 0
        defl_desc    = mon["base_deflection_description"]
        dodge_bonus  = mon["base_dodge"] or 0
        dodge_desc   = mon["base_dodge_description"]
        if mon["ac_total"] is None:
            review_reasons.append("ac_total is NULL")

        # ── Saves + grapple + initiative ──────────────────────────────────────
        fort_save, ref_save, will_save = _parse_saves(mon["saves"])
        grapple_val  = _parse_signed_int(mon["grapple"])
        initiative   = _parse_signed_int(mon["initiative"])

        # ── Feats ─────────────────────────────────────────────────────────────
        all_feat_tokens: list[tuple[str, bool]] = []
        if mon["feats"]:
            all_feat_tokens += [(t, False) for t in _split_feat_string(mon["feats"])]
        if mon["bonus_feats"]:
            all_feat_tokens += [(t, True)  for t in _split_feat_string(mon["bonus_feats"])]

        for fi, (raw_token, from_bonus_col) in enumerate(all_feat_tokens):
            base_name, param, is_bonus_flag = _parse_feat_token(raw_token)
            is_bonus = from_bonus_col or is_bonus_flag

            # Look up by full name first (handles "Armor Proficiency (Heavy)")
            feat_id = feat_lookup.get(raw_token.strip().lower().rstrip("."))
            feat_name_raw = None
            resolved_param = param

            if feat_id is None and param is not None:
                # Try lookup by base_name (without the parameter)
                feat_id = feat_lookup.get(base_name.strip().lower())

            if feat_id is None:
                # Catalog miss — store raw text for later hand-fix
                feat_name_raw = raw_token
                if base_name:
                    review_reasons.append(f"feat not in catalog: {base_name!r}")
                resolved_param = param  # keep the parameter even on a miss
            else:
                # If we found by full name (e.g. "Armor Proficiency (Heavy)"), no param
                if feat_lookup.get(raw_token.strip().lower().rstrip(".")) == feat_id:
                    resolved_param = None

            feat_rows.append({
                "monster_id":    mid,
                "feat_id":       feat_id,
                "feat_name_raw": feat_name_raw,
                "is_bonus":      int(is_bonus),
                "parameter":     resolved_param,
                "order_index":   fi,
            })

        # ── Skills ────────────────────────────────────────────────────────────
        for si, (skill_name, total_bonus, cond_text) in enumerate(
            _parse_skills(mon["skills"])
        ):
            if total_bonus is None:
                review_reasons.append(f"skill parse failed: {skill_name!r}")
            skill_rows.append({
                "monster_id":       mid,
                "skill_name":       skill_name,
                "ranks":            0,
                "misc_modifier":    0,
                "total_bonus":      total_bonus,
                "conditional_text": cond_text,
            })

        # ── Special traits ────────────────────────────────────────────────────
        for item in _parse_special_list(mon["special_attacks"], "attack"):
            trait_rows.append({"monster_id": mid, **item})
        for item in _parse_special_list(mon["special_qualities"], "quality"):
            trait_rows.append({"monster_id": mid, **item})

        # ── Attacks (from legacy attacks table) ───────────────────────────────
        atk_order: dict[int, int] = {}  # group_id → next order_in_group
        for atk in attacks_by_monster.get(mid, []):
            grp = atk["group_id"] or 1
            order_in = atk_order.get(grp, 0)
            atk_order[grp] = order_in + 1

            source = "natural" if atk["weapon_nature"] == "natural" else "weapon"
            extra = atk["dmg_text"] or atk["dmg_composite"] or None
            attack_rows.append({
                "monster_id":    mid,
                "routine":       "full",
                "group_index":   grp,
                "order_in_group": order_in,
                "source":        source,
                "weapon_link_id": None,
                "natural_name":  atk["att_name"],
                "count":         atk["att_count"] or 1,
                "is_primary":    _is_primary(atk["use_category"]),
                "attack_kind":   atk["att_mode"],
                "bonus_total":   atk["att_roll_enh"],
                "iteratives":    None,
                "damage_dice":   atk["dmg_die"],
                "damage_bonus":  atk["dmg_enh"],
                "critical":      _crit_string(atk["crit_range"], atk["crit_mult"]),
                "extra_effects": extra,
            })

        # ── Monster row ───────────────────────────────────────────────────────
        needs_review = 1 if review_reasons else 0
        needs_review_total += needs_review
        if review_reasons:
            report_lines.append(f"[{mid}] {mon['name']}: {'; '.join(review_reasons)}")

        monster_rows.append({
            "id":               mid,
            "preset_id":        None,
            "needs_review":     needs_review,
            "review_notes":     "; ".join(review_reasons) if review_reasons else None,
            "name":             mon["name"],
            "altname":          mon["altname"],
            "description":      mon["special_abilities"],
            "picture_path":     None,
            "token_path":       None,
            "token3d_path":     None,
            "reference":        mon["reference"],
            "size":             mon["size"] or "Medium",
            "type":             mon["type"] or "Unknown",
            "subtypes":         mon["descriptor"],
            "alignment":        mon["alignment"],
            "str_score":        mon["str"],
            "dex_score":        mon["dex"],
            "con_score":        mon["con"],
            "int_score":        mon["int"],
            "wis_score":        mon["wis"],
            "cha_score":        mon["cha"],
            "racial_hd_count":  racial_hd_count,
            "racial_hd_die":    racial_hd_die,
            "hp":               hp,
            "speed_land":       None,
            "speed_fly":        None,
            "fly_maneuverability": None,
            "speed_swim":       None,
            "speed_climb":      None,
            "speed_burrow":     None,
            "natural_armor":    nat_armor,
            "deflection_bonus": defl_bonus,
            "deflection_desc":  defl_desc,
            "dodge_bonus":      dodge_bonus,
            "dodge_desc":       dodge_desc,
            "ac_total":         mon["ac_total"],
            "ac_touch":         mon["ac_touch"],
            "ac_flat":          mon["ac_flat_footed"],
            "space":            mon["space"],
            "reach":            mon["reach"],
            "initiative":       initiative,
            "bab":              mon["base_attack"],
            "grapple":          grapple_val,
            "fort_save":        fort_save,
            "ref_save":         ref_save,
            "will_save":        will_save,
            "fort_save_type":   mon["fort_save_type"],
            "ref_save_type":    mon["ref_save_type"],
            "will_save_type":   mon["will_save_type"],
            "special_attacks":  mon["special_attacks"],
            "special_qualities": mon["special_qualities"],
            "challenge_rating": mon["challenge_rating"],
            "level_adjustment": mon["level_adjustment"],
            "environment":      mon["environment"],
            "organization":     mon["organization"],
            "treasure":         mon["treasure"],
            "advancement":      mon["advancement"],
            "advancement_type": mon["advancement_type"],
            "adv_max_hd":       mon["adv_max_hd"],
            "adv_size_thresholds": mon["adv_size_thresholds"],
            "created_at":       None,
            "updated_at":       None,
        })

    # ── Bulk inserts ──────────────────────────────────────────────────────────

    # str/dex/con/int/wis/cha are reserved keywords; use explicit column list
    dst.executemany(f"""
        INSERT INTO {R} (
            id, preset_id, needs_review, review_notes,
            name, altname, description, picture_path, token_path, token3d_path, reference,
            size, type, subtypes, alignment,
            str, dex, con, int, wis, cha,
            racial_hd_count, racial_hd_die, hp,
            speed_land, speed_fly, fly_maneuverability, speed_swim, speed_climb, speed_burrow,
            natural_armor, deflection_bonus, deflection_desc, dodge_bonus, dodge_desc,
            ac_total, ac_touch, ac_flat,
            space, reach, initiative, bab, grapple,
            fort_save, ref_save, will_save,
            fort_save_type, ref_save_type, will_save_type,
            special_attacks, special_qualities,
            challenge_rating, level_adjustment,
            environment, organization, treasure, advancement,
            advancement_type, adv_max_hd, adv_size_thresholds,
            created_at, updated_at
        ) VALUES (
            :id, :preset_id, :needs_review, :review_notes,
            :name, :altname, :description, :picture_path, :token_path, :token3d_path, :reference,
            :size, :type, :subtypes, :alignment,
            :str_score, :dex_score, :con_score, :int_score, :wis_score, :cha_score,
            :racial_hd_count, :racial_hd_die, :hp,
            :speed_land, :speed_fly, :fly_maneuverability, :speed_swim, :speed_climb, :speed_burrow,
            :natural_armor, :deflection_bonus, :deflection_desc, :dodge_bonus, :dodge_desc,
            :ac_total, :ac_touch, :ac_flat,
            :space, :reach, :initiative, :bab, :grapple,
            :fort_save, :ref_save, :will_save,
            :fort_save_type, :ref_save_type, :will_save_type,
            :special_attacks, :special_qualities,
            :challenge_rating, :level_adjustment,
            :environment, :organization, :treasure, :advancement,
            :advancement_type, :adv_max_hd, :adv_size_thresholds,
            :created_at, :updated_at
        )
    """, monster_rows)
    dst_con.commit()
    print(f"  {R}: inserted {len(monster_rows)} rows")

    if class_rows:
        dst.executemany(f"""
            INSERT INTO {R}_classes
                (monster_id, class_name, class_name_raw, levels, order_index, associated)
            VALUES
                (:monster_id, :class_name, :class_name_raw, :levels, :order_index, :associated)
        """, class_rows)
        dst_con.commit()
        print(f"  {R}_classes: inserted {len(class_rows)} rows")

    dst.executemany(f"""
        INSERT INTO {R}_attacks (
            monster_id, routine, group_index, order_in_group,
            source, weapon_link_id, natural_name, count, is_primary,
            attack_kind, bonus_total, iteratives, damage_dice, damage_bonus,
            critical, extra_effects
        ) VALUES (
            :monster_id, :routine, :group_index, :order_in_group,
            :source, :weapon_link_id, :natural_name, :count, :is_primary,
            :attack_kind, :bonus_total, :iteratives, :damage_dice, :damage_bonus,
            :critical, :extra_effects
        )
    """, attack_rows)
    dst_con.commit()
    print(f"  {R}_attacks: inserted {len(attack_rows)} rows")

    dst.executemany(f"""
        INSERT INTO {R}_feats
            (monster_id, feat_id, feat_name_raw, is_bonus, parameter, order_index)
        VALUES
            (:monster_id, :feat_id, :feat_name_raw, :is_bonus, :parameter, :order_index)
    """, feat_rows)
    dst_con.commit()
    print(f"  {R}_feats: inserted {len(feat_rows)} rows")

    dst.executemany(f"""
        INSERT INTO {R}_skill_ranks
            (monster_id, skill_name, ranks, misc_modifier, total_bonus, conditional_text)
        VALUES
            (:monster_id, :skill_name, :ranks, :misc_modifier, :total_bonus, :conditional_text)
    """, skill_rows)
    dst_con.commit()
    print(f"  {R}_skill_ranks: inserted {len(skill_rows)} rows")

    if trait_rows:
        dst.executemany(f"""
            INSERT INTO {R}_special_traits
                (monster_id, kind, name, short_label, ability_type, description, order_index)
            VALUES
                (:monster_id, :kind, :name, :short_label, :ability_type, :description, :order_index)
        """, trait_rows)
        dst_con.commit()
        print(f"  {R}_special_traits: inserted {len(trait_rows)} rows")

    # ── Backfill feats.parameter_options ──────────────────────────────────────
    backfilled = 0
    for feat_name, param_type in _FEAT_PARAM_OPTIONS.items():
        dst.execute(
            "UPDATE feats SET parameter_options = ? "
            "WHERE lower(name) = ? AND parameter_options IS NULL",
            (param_type, feat_name.lower()),
        )
        backfilled += dst.rowcount
    dst_con.commit()
    print(f"  feats.parameter_options: backfilled {backfilled} rows")

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(monster_rows)
    clean = total - needs_review_total
    print(f"\n  Migration complete: {total} total | {clean} clean | {needs_review_total} flagged")

    if report_path and report_lines:
        rp = Path(report_path)
        with rp.open("w", encoding="utf-8") as f:
            f.write(f"Migration Report — {root}\n{'='*60}\n")
            f.write(f"Total: {total}  Clean: {clean}  Flagged: {needs_review_total}\n\n")
            for line in report_lines:
                f.write(line + "\n")
        print(f"  Report written to {rp}")

    return needs_review_total
