"""
SRD — Saving Throws: good and poor progressions
================================================

Per the PHB / SRD save tables (referenced from "Improving Monsters"):

* Good save:  +2 + HD/2  (i.e. +2 at 1st HD, +3 at 2nd, +4 at 4th, ...)
* Poor save:  HD/3       (rounded down: 0 at 1–2 HD, +1 at 3, +2 at 6, ...)

Which of Fort/Ref/Will is "good" depends on the creature's type
(see Table: Creature Improvement by Type) — that mapping is stored on
each `AdvancedMonster` instance, not here.

Final save = base (this function) + ability modifier (Con/Dex/Wis)
+ feat bonuses (Great Fortitude / Lightning Reflexes / Iron Will).
"""


def calc_save(hd: int, save_type: str) -> int:
    """
    Return the base save bonus for *hd* HD on a good or poor progression.

    Accepts both short ("good"/"poor") and Excel-style ("goodSave"/"poorSave")
    aliases for compatibility with the seeded data.
    """
    if save_type in ("good", "goodSave"):
        return 2 + hd // 2
    return hd // 3
