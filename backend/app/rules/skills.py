"""
SRD — Improving Monsters: Skill Points
=======================================

From "Table: Creature Improvement by Type" (footnote 2):

> As long as a creature has an Intelligence of at least 1, it gains a
> minimum of 1 skill point per Hit Die.

And from footnote 3:

> Creatures with an Intelligence score of "—" gain no skill points or feats.

The base rate per HD comes from the type table — e.g. Animal/Humanoid get
2 + Int mod, Dragon gets 6 + Int mod, Outsider gets 8 + Int mod, Fey gets
6 + Int mod, etc. That "type rate" is stored on each monster instance
(`type_skill_points`); this module only encodes the per-HD math.
"""
import re


def skill_points_per_hd(type_rate: int, int_mod: int, has_intelligence: bool = True) -> int:
    """
    Skill points granted per HD.

    * type_rate       : the "X + Int mod per HD" base from the type table.
    * int_mod         : the creature's current Intelligence modifier.
    * has_intelligence: False for Int "—" creatures (returns 0).

    The minimum-1 floor only applies when Int >= 1 (i.e. there *is* an
    Int score). Mindless Int-"—" creatures get 0 skill points.
    """
    if not has_intelligence:
        return 0
    return max(1, type_rate + int_mod)


def parse_skills(skills_text: str) -> list[tuple[str, int]]:
    """
    Parse a stat-block skills line such as:

        "Climb +13, Hide +10, Knowledge (dungeoneering) +14"

    into [(name, bonus), ...].

    Handles complex names with parentheses and trailing notes
    ("+5 underground" etc.).
    """
    if not skills_text or not skills_text.strip():
        return []
    results = []
    # Naive split on commas — re-paired by matching the bonus pattern.
    for part in re.split(r",\s*", skills_text):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.+?)\s+([+-]\d+)(.*)", part)
        if m:
            results.append((m.group(1).strip(), int(m.group(2))))
    return results


def apply_skill_increases(skills_text: str, increases: dict) -> str:
    """
    Bump skill bonuses in a stat-block string by the deltas in *increases*.

    increases = {"Climb": 2, "Hide": 1}  →  "Climb +13" becomes "Climb +15".

    Only the first match per skill is rewritten; if a skill isn't present
    in the source text, it's silently skipped (caller's responsibility).
    """
    if not increases:
        return skills_text
    result = skills_text
    for skill_name, delta in increases.items():
        if delta == 0:
            continue
        escaped = re.escape(skill_name)
        pattern = rf"({escaped}\s+)([+-])(\d+)"

        def replacer(m, _delta=delta):
            old_bonus = int(f"{m.group(2)}{m.group(3)}")
            new_bonus = old_bonus + _delta
            sign = "+" if new_bonus >= 0 else ""
            return f"{m.group(1)}{sign}{new_bonus}"

        result = re.sub(pattern, replacer, result, count=1)
    return result
