"""
Monster-advancement orchestration.

Takes an `AdvancedMonster` (already populated with the user's choices)
and produces the formatted stat-block dictionary the API/templates
consume. The math itself lives in `app.rules`; this module just wires
the rules together and produces presentation-layer text (attack lines,
AC breakdown, abilities row).
"""
from collections import defaultdict
from dataclasses import replace

from ..domain.monster import AdvancedMonster, AttackData
from ..rules.attacks import (
    applies_improved_critical,
    applies_improved_natural_attack,
    double_crit_range,
    has_feat_for_attack,
    secondary_attack_penalty,
)
from ..rules.sizes import (
    SIZE_AC_MOD,
    SIZE_REACH_TALL,
    SIZE_SPACE,
    scale_damage,
)


# ----------------------------------------------------------------------
# Per-attack math
# ----------------------------------------------------------------------

def calc_attack_roll(monster: AdvancedMonster, attack: AttackData) -> int:
    """
    Sum the to-hit components for one attack:

      BAB + ability mod (Str/Dex) + size mod + enhancement
        + Weapon Focus (+1 if applicable)
        + Multiattack penalty (secondary natural attacks: -2 with feat,
                               otherwise -5)
    """
    bab = monster.current_bab
    size_mod = SIZE_AC_MOD.get(monster.current_size, 0)

    # Default ability for to-hit: Str for melee, Dex for ranged.
    ability_bonus = monster.str_mod if attack.att_mode.lower() == "melee" else monster.dex_mod

    # Weapon Finesse: light-or-natural melee weapons may use Dex if higher.
    if "Weapon Finesse" in monster.all_feats_text and attack.att_mode.lower() == "melee":
        is_finessable = (
            attack.weapon_nature.lower() == "natural"
            or attack.use_category.lower() == "weapon_oh"
        )
        if is_finessable:
            ability_bonus = max(monster.str_mod, monster.dex_mod)

    focus_bonus = 1 if (
        f"Weapon Focus ({attack.name})" in monster.all_feats_text
        or "Weapon Focus" in monster.all_feats_text
    ) else 0

    multiattack_penalty = (
        secondary_attack_penalty(monster.all_feats_text)
        if attack.use_category.lower() == "natural_secondary"
        else 0
    )

    return bab + ability_bonus + size_mod + attack.att_roll_enh + focus_bonus + multiattack_penalty


def calc_damage_bonus(monster: AdvancedMonster, attack: AttackData) -> int:
    """
    Damage bonus = Str * str_mult (1.5x two-handed/sole natural; 0.5x off-hand)
                 + enhancement
                 + Weapon Specialization (+2, Fighter 4+).
    """
    str_bonus = int(monster.str_mod * attack.str_mult)
    spec_bonus = 0
    for cl in monster.class_levels:
        if cl.class_name == "Fighter" and cl.level >= 4:
            if f"Weapon Specialization ({attack.name})" in monster.all_feats_text:
                spec_bonus = 2
    return str_bonus + attack.dmg_enh + spec_bonus


# ----------------------------------------------------------------------
# Attack-line formatting
# ----------------------------------------------------------------------

def format_attack_text(monster: AdvancedMonster, attack: AttackData, is_full: bool = True) -> str:
    """Format one attack as a stat-block string, e.g. '2 claws +7 melee (1d6+3)'."""
    roll = calc_attack_roll(monster, attack)
    dmg_bonus = calc_damage_bonus(monster, attack)

    roll_sign = "+" if roll >= 0 else ""
    bonus_text = f"+{dmg_bonus}" if dmg_bonus > 0 else (str(dmg_bonus) if dmg_bonus < 0 else "")

    count_text = f"{attack.count} " if attack.count > 1 and is_full else ""
    name_plural = f"{attack.name}s" if attack.count > 1 and is_full else attack.name

    crit_parts = []
    if attack.crit_range != "20":
        crit_parts.append(attack.crit_range)
    if attack.crit_mult != 2:
        crit_parts.append(f"x{attack.crit_mult}")
    crit_text = ("/" + "/".join(crit_parts)) if crit_parts else ""

    return (
        f"{count_text}{name_plural} {roll_sign}{roll} {attack.att_mode} "
        f"({attack.dmg_die}{bonus_text}{crit_text})"
    )


def _build_attack_text(monster: AdvancedMonster, attacks: list) -> tuple[str, str]:
    """
    Group attacks by `group_id`:
      attacks within a group → joined with " and " (simultaneous attacks).
      different groups       → joined with " or "  (alternative routines).

    Returns (standard_attack, full_attack) tuple.
    """
    if not attacks:
        return "", ""

    groups: dict[int, list] = defaultdict(list)
    for a in attacks:
        groups[a.group_id].append(a)

    full_attack = " or ".join(
        " and ".join(format_attack_text(monster, a, is_full=True) for a in groups[gid])
        for gid in sorted(groups.keys())
    )

    std = next((a for a in attacks if a.is_standard), attacks[0])
    standard_attack = format_attack_text(monster, std, is_full=False)
    return standard_attack, full_attack


# ----------------------------------------------------------------------
# Feat / size effects on natural attacks
# ----------------------------------------------------------------------

def _apply_attack_modifiers(monster: AdvancedMonster, attacks: list) -> list:
    """
    Mirror the Excel order:

      1. Improved Natural Attack — bump natural-weapon damage one die step.
      2. Size change — bump natural-weapon damage one die step per size step.
      3. Improved Critical — double the threat range on the named weapon.

    The order matters: stacking INA *before* the size scale keeps the
    final die one step higher, matching the SRD's "size happens last
    in the stat-block math" convention used by the original tool.
    """
    feats_text = monster.all_feats_text
    size_changed = monster.current_size != monster.original_size

    out = list(attacks)

    out = [
        replace(a, dmg_die=scale_damage(a.dmg_die, 1))
        if applies_improved_natural_attack(a.name, feats_text) else a
        for a in out
    ]

    if size_changed:
        out = [
            replace(a, dmg_die=scale_damage(a.dmg_die, 1))
            if a.weapon_nature.lower() == "natural" else a
            for a in out
        ]

    out = [
        replace(a, crit_range=double_crit_range(a.crit_range))
        if applies_improved_critical(a.name, feats_text) else a
        for a in out
    ]

    return out


# ----------------------------------------------------------------------
# Stat-block assembly
# ----------------------------------------------------------------------

def generate_stat_block(monster: AdvancedMonster) -> dict:
    """
    Build the complete stat-block dictionary returned by the API.

    Keys here are the wire format consumed by the frontend templates and
    by `schemas.StatBlockResponse` — do not rename without updating both.
    """
    # ----- type / class line -----
    class_text = " / ".join(f"{cl.class_name} {cl.level}" for cl in monster.class_levels)

    type_line = f"{monster.current_size} {monster.type}"
    if monster.descriptor:
        type_line += f" ({monster.descriptor})"
    if class_text:
        type_line += f" / {class_text}"

    # ----- space / reach -----
    # When size has changed, default to the SRD size table; otherwise keep
    # the creature's printed values (some monsters have unusual reach that
    # the table can't capture).
    size_changed = monster.current_size != monster.original_size
    if size_changed:
        space_val = SIZE_SPACE.get(monster.current_size, monster.space)
        reach_val = str(SIZE_REACH_TALL.get(monster.current_size, 5))
    else:
        space_val = monster.space
        reach_val = monster.reach

    # ----- attacks (apply feat + size modifiers, then format) -----
    effective_attacks = _apply_attack_modifiers(monster, monster.attacks)
    standard_attack, full_attack = _build_attack_text(monster, effective_attacks)

    # ----- AC breakdown -----
    ac_parts = []
    if monster.size_ac_mod != 0:
        ac_parts.append(f"{monster.size_ac_mod:+d} size")
    dex_to_ac = monster.effective_dex_to_ac
    if dex_to_ac != 0:
        dex_label = "Dex"
        if monster.effective_max_dex is not None and monster.dex_mod > monster.effective_max_dex:
            dex_label = f"Dex (max {monster.effective_max_dex:+d})"
        ac_parts.append(f"{dex_to_ac:+d} {dex_label}")
    if monster.current_nat_armor != 0:
        ac_parts.append(f"+{monster.current_nat_armor} natural")
    if monster.effective_armor != 0:
        ac_parts.append(f"+{monster.effective_armor} armor")
    if monster.effective_shield != 0:
        ac_parts.append(f"+{monster.effective_shield} shield")
    if monster.base_deflection != 0:
        ac_parts.append(f"+{monster.base_deflection} deflection")
    if monster.base_dodge != 0:
        ac_parts.append(f"+{monster.base_dodge} dodge")

    ac_text = (
        f"{monster.total_ac} ({', '.join(ac_parts)}), "
        f"touch {monster.touch_ac}, flat-footed {monster.flat_footed_ac}"
    )

    # ----- saves / abilities -----
    saves_text = (
        f"Fort {monster.fort_save:+d}, Ref {monster.ref_save:+d}, Will {monster.will_save:+d}"
    )

    con = monster.total_con
    intel = monster.total_int
    abilities_text = ", ".join([
        f"Str {monster.total_str}",
        f"Dex {monster.total_dex}",
        f"Con {con}" if con is not None else "Con -",
        f"Int {intel}" if intel is not None else "Int -",
        f"Wis {monster.total_wis}",
        f"Cha {monster.total_cha}",
    ])

    class_features = [
        f"{cl.class_name} {cl.level}: {cl.features}"
        for cl in monster.class_levels if cl.features
    ]

    return {
        "name": monster.name,
        "type_line": type_line,
        "hit_points": monster.hp_text,
        "hp_average": monster.hp_average,
        "initiative": f"{monster.initiative:+d}",
        "speed": monster.speed,
        "armor_class": ac_text,
        "total_ac": monster.total_ac,
        "touch_ac": monster.touch_ac,
        "flat_footed_ac": monster.flat_footed_ac,
        "base_attack": f"+{monster.current_bab}",
        "grapple": f"{monster.grapple:+d}",
        "saves": saves_text,
        "fort_save": monster.fort_save,
        "ref_save": monster.ref_save,
        "will_save": monster.will_save,
        "abilities": abilities_text,
        "strength": monster.total_str,
        "dex": monster.total_dex,
        "con": monster.total_con,
        "intelligence": monster.total_int,  # may be None for Int "—"
        "wis": monster.total_wis,
        "cha": monster.total_cha,
        "feats": monster.all_feats_text,
        "max_feats": monster.max_feats,
        "skills": monster.updated_skills_text,
        "bonus_skill_points": monster.bonus_skill_points,
        "spent_skill_points": monster.spent_skill_points,
        "special_attacks": monster.special_attacks,
        "special_qualities": monster.special_qualities,
        "environment": monster.environment,
        "organization": monster.organization,
        "challenge_rating": monster.current_cr,
        # CR breakdown for the UI / debugging.
        "cr_from_classes": monster.cr_from_classes,
        "cr_extra_modifiers": monster.cr_extra_modifiers,
        # SRD ability-point budget from HD advancement.
        "available_ability_points": monster.available_ability_points,
        "spent_ability_points": monster.spent_ability_points,
        "treasure": monster.treasure,
        "alignment": monster.alignment,
        "advancement": monster.advancement,
        "level_adjustment": monster.level_adjustment,
        "space_reach": f"{space_val} ft./{reach_val} ft.",
        "attack": standard_attack,
        "full_attack": full_attack,
        "class_levels": class_text,
        "class_features": class_features,
        "total_hd": monster.total_hd,
        "current_size": monster.current_size,
        "sneak_attack_dice": monster.sneak_attack_dice,
        "barbarian_rage_per_day": monster.barbarian_rage_per_day,
        "damage_reduction": monster.damage_reduction,
    }
