"""
SRD — Improving Monsters: Size Increases
========================================

> A creature may become larger when its Hit Dice are increased. A size
> increase affects any special ability the creature has that is affected
> by size. Increased size also affects a creature's ability scores, AC,
> attack bonuses, and damage values.

Two SRD tables are encoded here:

* Table: Changes to Statistics by Size
    - cumulative Str/Dex/Con, natural-armor, and AC/attack adjustments
      applied for each one-step size category change.
* Table: Increased Damage By Size
    - damage-die scaling per size step (e.g., 1d6 → 1d8 → 2d6 …).

Sizes form an ordered ladder; transitions are walked one step at a time
so multi-step changes (e.g., Medium → Huge) sum correctly.
"""
from typing import Optional


# Ordered list of size categories — used as a ladder for stepwise transitions.
SIZE_ORDER = [
    "Fine", "Diminutive", "Tiny", "Small", "Medium",
    "Large", "Huge", "Gargantuan", "Colossal",
]

# AC / attack-roll modifier by size (smaller = harder to hit + easier to hit with).
# Source: SRD combat rules; matches the "AC/Attack" column of the size table
# applied cumulatively from Medium = 0.
SIZE_AC_MOD = {
    "Fine": 8, "Diminutive": 4, "Tiny": 2, "Small": 1,
    "Medium": 0, "Large": -1, "Huge": -2, "Gargantuan": -4, "Colossal": -8,
}

# Grapple modifier by size (special-size mod, larger = easier to grapple).
SIZE_GRAPPLE_MOD = {
    "Fine": -16, "Diminutive": -12, "Tiny": -8, "Small": -4,
    "Medium": 0, "Large": 4, "Huge": 8, "Gargantuan": 12, "Colossal": 16,
}

# Space (square footprint) per size, in feet — string to preserve "1/2", "2-1/2".
SIZE_SPACE = {
    "Fine": "1/2", "Diminutive": "1", "Tiny": "2-1/2", "Small": "5",
    "Medium": "5", "Large": "10", "Huge": "15", "Gargantuan": "20", "Colossal": "30",
}

# Natural reach for "Tall" creatures (humanoid-like proportions).
SIZE_REACH_TALL = {
    "Fine": 0, "Diminutive": 0, "Tiny": 0, "Small": 5,
    "Medium": 5, "Large": 10, "Huge": 15, "Gargantuan": 20, "Colossal": 30,
}

# Natural reach for "Long" creatures (quadrupeds, serpents) — one step shorter
# than Tall above Medium.
SIZE_REACH_LONG = {
    "Fine": 0, "Diminutive": 0, "Tiny": 0, "Small": 5,
    "Medium": 5, "Large": 5, "Huge": 10, "Gargantuan": 15, "Colossal": 20,
}

# Per-step transition deltas — exactly the rows of "Table: Changes to
# Statistics by Size" in the SRD. Each entry describes the change going
# *upward* one category. Reverse the signs for size decreases.
SIZE_TRANSITIONS = {
    "Fine to Diminutive":     {"str": 0, "dex": -2, "con": 0, "nat_ac": 0, "ac": -4, "atk": -4},
    "Diminutive to Tiny":     {"str": 2, "dex": -2, "con": 0, "nat_ac": 0, "ac": -2, "atk": -2},
    "Tiny to Small":          {"str": 4, "dex": -2, "con": 0, "nat_ac": 0, "ac": -1, "atk": -1},
    "Small to Medium":        {"str": 4, "dex": -2, "con": 2, "nat_ac": 0, "ac": -1, "atk": -1},
    "Medium to Large":        {"str": 8, "dex": -2, "con": 4, "nat_ac": 2, "ac": -1, "atk": -1},
    "Large to Huge":          {"str": 8, "dex": -2, "con": 4, "nat_ac": 3, "ac": -1, "atk": -1},
    "Huge to Gargantuan":     {"str": 8, "dex": 0,  "con": 4, "nat_ac": 4, "ac": -2, "atk": -2},
    "Gargantuan to Colossal": {"str": 8, "dex": 0,  "con": 4, "nat_ac": 5, "ac": -4, "atk": -4},
}

# Damage-die scaling per +1 size step (SRD: Table: Increased Damage By Size).
# Anything not in this table is left unchanged (e.g., "0", "1" — non-dice).
DAMAGE_SCALE_UP = {
    "0": "0", "1": "1",
    "1d2": "1d3", "1d3": "1d4", "1d4": "1d6", "1d6": "1d8",
    "1d8": "2d6", "1d10": "2d8", "1d12": "3d6",
    "2d4": "2d6", "2d6": "3d6", "2d8": "3d8", "2d10": "4d8",
    "3d6": "3d8", "3d8": "4d8", "4d8": "6d8", "6d8": "8d8", "8d8": "12d8",
}

# Inverse mapping — used when shrinking a creature one or more steps.
DAMAGE_SCALE_DOWN = {v: k for k, v in DAMAGE_SCALE_UP.items() if k != v}


def get_size_transition(old_size: str, new_size: str) -> dict:
    """
    Sum the per-step Str/Dex/Con/natural-armor/AC/attack deltas for going
    from *old_size* to *new_size*. Walks the ladder one step at a time so
    multi-step changes accumulate correctly.

    Returns zeros when the size doesn't change.
    """
    old_idx = SIZE_ORDER.index(old_size)
    new_idx = SIZE_ORDER.index(new_size)
    if old_idx == new_idx:
        return {"str": 0, "dex": 0, "con": 0, "nat_ac": 0, "ac": 0, "atk": 0}

    total = {"str": 0, "dex": 0, "con": 0, "nat_ac": 0, "ac": 0, "atk": 0}
    step = 1 if new_idx > old_idx else -1

    for i in range(old_idx, new_idx, step):
        if step > 0:
            key = f"{SIZE_ORDER[i]} to {SIZE_ORDER[i + 1]}"
            for k in total:
                total[k] += SIZE_TRANSITIONS[key][k]
        else:
            # Walking down — apply the upward step's negation.
            key = f"{SIZE_ORDER[i - 1]} to {SIZE_ORDER[i]}"
            for k in total:
                total[k] -= SIZE_TRANSITIONS[key][k]
    return total


def scale_damage(dmg: str, steps: int) -> str:
    """
    Step a damage die up (positive) or down (negative) by *steps* size
    categories. Unmapped values pass through unchanged so unusual dice
    (or text like "—") survive without raising.
    """
    current = dmg
    table = DAMAGE_SCALE_UP if steps > 0 else DAMAGE_SCALE_DOWN
    for _ in range(abs(steps)):
        current = table.get(current, current)
    return current


def is_tiny_or_smaller(size: str) -> bool:
    """Tiny / Diminutive / Fine creatures use halved armor/shield AC bonuses."""
    return SIZE_ORDER.index(size) <= SIZE_ORDER.index("Tiny")
