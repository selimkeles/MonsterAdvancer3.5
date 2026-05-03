"""
SRD — Improving Monsters: Feat Acquisition
===========================================

> All types have a number of feats equal to 1 + 1 per 3 Hit Dice.
> A monster's total Hit Dice, not its ECL, govern its acquisition of feats.
> Creatures with an Intelligence score of "—" gain no skill points or feats.

Plus the PHB Fighter:

> A fighter gains a bonus feat at 1st level. He gains an additional bonus
> feat at 2nd level and every two fighter levels thereafter (4th, 6th, …).

NOTE on parity: the legacy calculator's `max_feats` always returned at
least 1 feat. The SRD-correct behavior (0 feats for Int-"—" creatures
like Constructs and Oozes) is implemented here behind the
`has_intelligence` flag — callers should pass `has_intelligence=False`
when the creature has no Int score to enable that fix.
"""


def feat_count(total_hd: int, has_intelligence: bool = True, fighter_levels: int = 0) -> int:
    """
    Return the total number of feats a creature is entitled to.

    * total_hd        : monster racial HD + class levels.
    * has_intelligence: False for creatures with Int score "—" (no feats).
    * fighter_levels  : number of Fighter class levels for bonus feats.
    """
    if not has_intelligence:
        return 0
    base = 1 + total_hd // 3                      # SRD: 1 + 1 per 3 HD.
    fighter_bonus = (1 + fighter_levels // 2) if fighter_levels else 0
    return base + fighter_bonus
