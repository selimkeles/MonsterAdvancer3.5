"""
SRD — Improving Monsters: Hit Dice and the 1-HD Replacement Rule
=================================================================

> Creatures with 1 or less HD replace their monster levels with their
> character levels. The monster loses the attack bonus, saving throw
> bonuses, skills, and feats granted by its 1 monster HD and gains the
> attack bonus, save bonuses, skills, feats, and other class abilities
> of a 1st-level character of the appropriate class.

> The creature's Hit Dice equal the number of class levels it has plus
> its racial Hit Dice. Additional Hit Dice gained from taking levels in
> a character class never affect a creature's size.

This module exposes small predicates and an HP calculator used by both
the orchestrator and the dataclass property layer.
"""


def replaces_monster_hd(base_hd: int, has_class_levels: bool) -> bool:
    """
    True when the creature is a 1-HD humanoid taking class levels — its
    monster HD is fully replaced by its first class level (no stacking
    of monster BAB/saves/HP/skills/feats from racial HD).
    """
    return base_hd <= 1 and has_class_levels


def total_hd(base_hd: int, current_hd: int, class_hd: int) -> int:
    """
    Total HD = monster HD + class HD, with the 1-HD replacement rule
    applied. *current_hd* is the post-advancement monster HD count
    (i.e. base_hd plus any racial HD added).
    """
    if replaces_monster_hd(base_hd, class_hd > 0):
        return class_hd
    return current_hd + class_hd


def average_hp_for_hd(hd_count: int, hd_die: int, con_mod: int) -> int:
    """
    Average HP from a block of HD using the standard "average roll" of
    (die + 1) / 2 per HD, plus Con mod per HD. Truncates with int() to
    match the original calculator's rounding.
    """
    if hd_count <= 0:
        return 0
    avg_roll = (hd_die + 1) / 2
    return int(hd_count * (avg_roll + con_mod))


# Construct bonus HP by size (from MM Construct type description).
CONSTRUCT_BONUS_HP = {
    "Small": 10, "Medium": 20, "Large": 30, "Huge": 40,
    "Gargantuan": 60, "Colossal": 80,
}
