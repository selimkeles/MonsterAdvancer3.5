"""
SRD — Improving Monsters: Base Attack Bonus progression by creature type
========================================================================

From "Table: Creature Improvement by Type":

* Fighter progression (HD x 1):   Dragon, Magical beast, Monstrous humanoid,
                                  Outsider — and PHB classes Barbarian,
                                  Fighter, Paladin, Ranger.
* Cleric progression (HD x 3/4):  Aberration, Animal, Construct, Elemental,
                                  Giant, Humanoid, Ooze, Plant, Vermin —
                                  and most NPC classes.
* Wizard progression (HD x 1/2):  Fey, Undead — and PHB Wizard/Sorcerer.

Note: When a creature gains class levels, its BAB from class HD uses the
*class's* progression, not its monster type's (SRD: "if a creature
acquires a character class, it improves according to its class").
"""


def calc_bab(hd: int, bab_type: str) -> int:
    """
    Return the base attack bonus for *hd* Hit Dice on the given progression.

    Accepts both the short ("good"/"average"/"poor") and Excel-style
    ("goodBAB"/"averageBAB"/"poorBAB") aliases, since the seeded data
    uses the latter.
    """
    if bab_type in ("good", "goodBAB"):
        return hd                           # Fighter — +1 per HD.
    if bab_type in ("average", "averageBAB"):
        return (hd * 3) // 4                # Cleric — +3 per 4 HD, rounded down.
    return hd // 2                          # Wizard / poor — +1 per 2 HD.
