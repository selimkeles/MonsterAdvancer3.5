"""
SRD — Improving Monsters: Ability Scores
=========================================

Three standard arrays for monsters (before racial adjustments):

* Standard array : 11, 11, 11, 10, 10, 10  — typical / un-improved monster.
* Nonelite array : 13, 12, 11, 10,  9,  8  — appropriate for NPC-class advances.
* Elite array    : 15, 14, 13, 12, 10,  8  — appropriate for PC-class advances
                                              and "any monster unique enough
                                              to be improved".

> Treat monster Hit Dice the same as character level for determining ability
> score increases. This only applies to Hit Dice increases — monsters do not
> gain ability score increases for levels they "already reached" with their
> racial Hit Dice.

That means: when advancing a monster from base_hd to current_hd, it gains
+1 to one ability score for every 4 *added* HD that crosses a multiple of
4 (4th, 8th, 12th, 16th, 20th total HD).
"""

STANDARD_ARRAY = (11, 11, 11, 10, 10, 10)
NONELITE_ARRAY = (13, 12, 11, 10, 9, 8)
ELITE_ARRAY    = (15, 14, 13, 12, 10, 8)


def ability_mod(score: int) -> int:
    """Standard 3.5 ability modifier: floor((score - 10) / 2)."""
    # Note: Python's `//` floors toward negative infinity, which matches the
    # SRD intent for sub-10 scores (e.g., score=8 → -1, score=7 → -2).
    return (score - 10) // 2


def hd_increase_ability_points(base_hd: int, current_hd: int) -> int:
    """
    Number of +1 ability bumps earned by adding HD past *base_hd*.

    Counts how many 4th-HD thresholds (4, 8, 12, …) the new HD crosses
    that the base HD did not — matching the SRD guidance that bumps only
    apply to *added* HD.
    """
    if current_hd <= base_hd:
        return 0
    return (current_hd // 4) - (base_hd // 4)
