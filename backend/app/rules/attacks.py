"""
Attack and damage calculation
==============================

Sources: PHB combat chapter and the various SRD feat / monster-type pages.
This module covers the per-attack math (roll bonus, damage bonus,
secondary-attack penalties, threat-range doubling) — not the higher-level
stat-block formatting, which lives in `app.services.advancement`.

Key rules wrapped here:

* Strength / Dexterity to-hit selection (melee uses Str by default; ranged
  uses Dex; Weapon Finesse lets light/natural weapons use the higher of
  the two).
* Multiattack feat: secondary natural attacks are at -2 instead of -5.
* Improved Critical: doubles the threat range (20 → 19-20, 19-20 → 17-20,
  18-20 → 15-20). Floor at 2 because a natural 1 is always a miss.
* Weapon Focus: +1 to attack rolls with the named weapon.
* Weapon Specialization: +2 damage with the named weapon (Fighter 4+).
* Improved Natural Attack: bumps the natural-weapon damage die one step.
"""
from .sizes import scale_damage


def has_feat_for_attack(feat_name: str, attack_name: str, feats_text: str) -> bool:
    """
    True if a weapon-specific feat referencing *attack_name* is present
    (case-insensitive, e.g. ``Weapon Focus (Claw)``).
    """
    target = f"{feat_name} ({attack_name})".lower()
    return target in feats_text.lower()


def double_crit_range(crit_range: str) -> str:
    """
    Apply Improved Critical: double the current threat range.

    20      → 19-20
    19-20   → 17-20
    18-20   → 15-20

    Threat range is computed as ``21 - low``; the new low is clamped to 2
    so a natural-1 auto-miss is preserved.
    """
    s = crit_range.strip()
    low = int(s.split("-")[0]) if "-" in s else int(s)
    threat = 21 - low
    new_low = max(2, 21 - threat * 2)
    return f"{new_low}-20" if new_low < 20 else "20"


def secondary_attack_penalty(feats_text: str) -> int:
    """
    Penalty applied to secondary natural attacks.

    Default is -5. Multiattack reduces it to -2 (SRD: Multiattack feat).
    """
    return -2 if "Multiattack" in feats_text else -5


def applies_improved_natural_attack(attack_name: str, feats_text: str) -> bool:
    """Improved Natural Attack scales the damage die up one step."""
    return has_feat_for_attack("Improved Natural Attack", attack_name, feats_text.lower())


def applies_improved_critical(attack_name: str, feats_text: str) -> bool:
    """Improved Critical doubles the threat range for the named weapon."""
    return has_feat_for_attack("Improved Critical", attack_name, feats_text.lower())


# Re-export so callers can do `from .attacks import scale_damage` if they
# want the size-step damage scaling alongside the feat helpers.
__all__ = [
    "has_feat_for_attack",
    "double_crit_range",
    "secondary_attack_penalty",
    "applies_improved_natural_attack",
    "applies_improved_critical",
    "scale_damage",
]
