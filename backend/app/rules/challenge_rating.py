"""
SRD — Improving Monsters: Advanced Monster Challenge Rating
============================================================

From "Table: Improved Monster CR Increase":

CR increase per HD added (HD-only advancement, no class levels):

  +1 per 4 HD : Aberration, Construct, Elemental, Fey, Giant, Humanoid,
                Ooze, Plant, Undead, Vermin
  +1 per 3 HD : Animal, Magical beast, Monstrous humanoid
  +1 per 2 HD : Dragon, Outsider, *and* nonassociated class levels

Plus these flat modifiers (cumulative):

  +1 if size increased to Large or larger
  +1 if monster uses the elite array (only when *not* advanced by class)
  +2 for new special attacks/qualities that significantly improve combat
  +1 for new special abilities that improve combat in a minor way

Class-level rules (mutually exclusive with HD CR table):

  Associated class level    : +1 per level (class plays to creature's
                              existing strengths — e.g. Fighter for a
                              melee monster).
  Nonassociated class level : +½ per level until count equals the
                              creature's *original* HD; thereafter
                              +1 per level. NPC-class levels are
                              always nonassociated.

NOTE on parity: the legacy `current_cr` only used the per-HD divisor
stored on the monster (cr_mod). Use `cr_from_hd_advancement` for
parity; `extra_cr_modifiers` covers the flat-bonus rows; and
`cr_from_class_levels` covers associated/nonassociated class-level CR.
The orchestrator decides which to apply based on the user's choices.
"""
from dataclasses import dataclass


def cr_from_hd_advancement(base_cr: float, base_hd: int, current_hd: int, cr_mod: int) -> float:
    """
    The original Excel formula:

        CR = baseCR + floor((curHD - baseHD) / crMod)

    *cr_mod* is the per-type CR divisor (4 / 3 / 2). Returns *base_cr*
    unchanged when no HD have been added or *cr_mod* is non-positive.
    """
    hd_added = current_hd - base_hd
    if hd_added <= 0 or cr_mod <= 0:
        return float(base_cr)
    return float(base_cr) + (hd_added // cr_mod)


@dataclass
class ExtraCRModifiers:
    """Flag bundle for the SRD's flat CR-bonus rows."""
    size_increased_to_large_plus: bool = False
    uses_elite_array: bool = False
    significant_special_abilities: bool = False
    minor_special_abilities: bool = False


def extra_cr_modifiers(flags: ExtraCRModifiers) -> int:
    """Sum the flat CR adders. Significant and minor are mutually exclusive."""
    extra = 0
    if flags.size_increased_to_large_plus:
        extra += 1
    if flags.uses_elite_array:
        extra += 1
    # SRD: "Do not add this factor twice if a monster has both special
    # attacks and special qualities" — significant outranks minor.
    if flags.significant_special_abilities:
        extra += 2
    elif flags.minor_special_abilities:
        extra += 1
    return extra


def cr_from_class_levels(
    associated_levels: int,
    nonassociated_levels: int,
    base_hd: int,
) -> float:
    """
    SRD rule: nonassociated levels grant +½ CR each *until* the count of
    nonassociated levels equals the creature's original HD; subsequent
    nonassociated levels grant +1 each (treated as associated thereafter).

    Associated levels always grant +1 each.

    Returns the CR delta to add on top of the base creature's CR.
    """
    delta = float(associated_levels)
    if nonassociated_levels <= 0:
        return delta

    # Half-CR portion: up to the first `base_hd` nonassociated levels.
    half_cr_count = min(nonassociated_levels, max(base_hd, 0))
    full_cr_count = nonassociated_levels - half_cr_count
    delta += 0.5 * half_cr_count + 1.0 * full_cr_count
    return delta
