"""
SRD — Improving Monsters: Class Levels
=======================================

> If a creature acquires a character class, it follows the rules for
> multiclass characters. The creature's Hit Dice equal the number of
> class levels it has plus its racial Hit Dice.

> Additional Hit Dice gained from taking levels in a character class
> never affect a creature's size.

> A monster's total Hit Dice, not its ECL, govern its acquisition of
> feats and ability score increases.

This module hosts class-feature lookups (Fighter bonus feats, Rogue
sneak attack progression, Barbarian rage / DR) and the predicate that
distinguishes associated from nonassociated class levels for CR
purposes (used by `challenge_rating.cr_from_class_levels`).
"""

# Classes considered "associated" for melee-focused base creatures
# (SRD: "Barbarian, fighter, paladin, and ranger are associated classes
# for a creature that relies on its fighting ability").
MELEE_ASSOCIATED = {"Barbarian", "Fighter", "Paladin", "Ranger"}

# Stealth/skill-focused associated classes.
STEALTH_ASSOCIATED = {"Rogue", "Ranger"}

# NPC classes — always nonassociated per SRD.
NPC_CLASSES = {"Adept", "Aristocrat", "Commoner", "Expert", "Warrior"}


def sneak_attack_dice(rogue_levels: int) -> int:
    """Rogue: +1d6 sneak attack at 1st level, +1d6 every two levels."""
    if rogue_levels <= 0:
        return 0
    return (rogue_levels + 1) // 2


def barbarian_rage_per_day(barbarian_levels: int) -> int:
    """Barbarian: 1/day at 1st, +1/day every 4 levels (5th, 9th, ...)."""
    if barbarian_levels <= 0:
        return 0
    return 1 + (barbarian_levels - 1) // 4


def barbarian_dr(barbarian_levels: int) -> str:
    """
    Barbarian damage reduction: DR 1/- at 7th, +1 every 3 levels
    (10th = 2/-, 13th = 3/-, ...).
    """
    if barbarian_levels < 7:
        return ""
    return f"DR {(barbarian_levels - 4) // 3}/-"


def fighter_bonus_feats(fighter_levels: int) -> int:
    """Fighter bonus feats: 1 at 1st, +1 every two levels."""
    if fighter_levels <= 0:
        return 0
    return 1 + fighter_levels // 2
