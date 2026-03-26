"""
Core D&D 3.5 monster advancement calculation engine.
Ports the Excel formula logic from the Models sheet to Python.
"""
import math
from dataclasses import dataclass, field, replace
from typing import Optional

# Size order for lookups
SIZE_ORDER = ["Fine", "Diminutive", "Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan", "Colossal"]

# Size -> AC/Attack modifier
SIZE_AC_MOD = {
    "Fine": 8, "Diminutive": 4, "Tiny": 2, "Small": 1,
    "Medium": 0, "Large": -1, "Huge": -2, "Gargantuan": -4, "Colossal": -8,
}

# Size -> Grapple modifier
SIZE_GRAPPLE_MOD = {
    "Fine": -16, "Diminutive": -12, "Tiny": -8, "Small": -4,
    "Medium": 0, "Large": 4, "Huge": 8, "Gargantuan": 12, "Colossal": 16,
}

# Size -> Space (ft)
SIZE_SPACE = {
    "Fine": "1/2", "Diminutive": "1", "Tiny": "2-1/2", "Small": "5",
    "Medium": "5", "Large": "10", "Huge": "15", "Gargantuan": "20", "Colossal": "30",
}

# Size -> Natural Reach (ft) for Tall creatures
SIZE_REACH_TALL = {
    "Fine": 0, "Diminutive": 0, "Tiny": 0, "Small": 5,
    "Medium": 5, "Large": 10, "Huge": 15, "Gargantuan": 20, "Colossal": 30,
}

# Size -> Natural Reach (ft) for Long creatures
SIZE_REACH_LONG = {
    "Fine": 0, "Diminutive": 0, "Tiny": 0, "Small": 5,
    "Medium": 5, "Large": 5, "Huge": 10, "Gargantuan": 15, "Colossal": 20,
}

# Size change stat adjustments (from Tables sheet)
SIZE_TRANSITIONS = {
    "Fine to Diminutive":       {"str": 0,  "dex": -2, "con": 0, "nat_ac": 0, "ac": -4, "atk": -4},
    "Diminutive to Tiny":       {"str": 2,  "dex": -2, "con": 0, "nat_ac": 0, "ac": -2, "atk": -2},
    "Tiny to Small":            {"str": 4,  "dex": -2, "con": 0, "nat_ac": 0, "ac": -1, "atk": -1},
    "Small to Medium":          {"str": 4,  "dex": -2, "con": 2, "nat_ac": 0, "ac": -1, "atk": -1},
    "Medium to Large":          {"str": 8,  "dex": -2, "con": 4, "nat_ac": 2, "ac": -1, "atk": -1},
    "Large to Huge":            {"str": 8,  "dex": -2, "con": 4, "nat_ac": 3, "ac": -1, "atk": -1},
    "Huge to Gargantuan":       {"str": 8,  "dex": 0,  "con": 4, "nat_ac": 4, "ac": -2, "atk": -2},
    "Gargantuan to Colossal":   {"str": 8,  "dex": 0,  "con": 4, "nat_ac": 5, "ac": -4, "atk": -4},
}

# Damage scaling (from Tables sheet)
DAMAGE_SCALE_UP = {
    "0": "0", "1": "1",
    "1d2": "1d3", "1d3": "1d4", "1d4": "1d6", "1d6": "1d8",
    "1d8": "2d6", "1d10": "2d8", "1d12": "3d6",
    "2d4": "2d6", "2d6": "3d6", "2d8": "3d8", "2d10": "4d8",
    "3d6": "3d8", "3d8": "4d8", "4d8": "6d8", "6d8": "8d8", "8d8": "12d8",
}

DAMAGE_SCALE_DOWN = {v: k for k, v in DAMAGE_SCALE_UP.items() if k != v}


@dataclass
class AttackData:
    name: str
    count: int = 1
    is_standard: bool = True
    weapon_nature: str = "natural"  # natural or manufactured
    att_mode: str = "melee"
    use_category: str = "natural_Primary"
    dmg_die: str = "1d6"
    crit_range: str = "20"
    crit_mult: int = 2
    str_mult: float = 1.0
    att_roll_enh: int = 0
    dmg_enh: int = 0
    group_id: int = 1


@dataclass
class ClassLevel:
    class_name: str
    level: int
    hd_type: int
    bab: int
    fort_save: int
    ref_save: int
    will_save: int
    skill_points_per_level: int
    features: str = ""


@dataclass
class AdvancedMonster:
    """Represents a monster after advancement calculations."""
    # Identity
    name: str
    original_size: str
    current_size: str
    type: str
    descriptor: str = ""

    # Hit Dice
    base_hd: int = 1
    current_hd: int = 1
    hd_type: int = 8  # d8, d10, d12

    # Abilities
    base_str: int = 10
    base_dex: int = 10
    base_con: int = 10
    base_int: int = 10
    base_wis: int = 10
    base_cha: int = 10
    str_inc: int = 0  # manual ability score increases
    dex_inc: int = 0
    con_inc: int = 0
    int_inc: int = 0
    wis_inc: int = 0
    cha_inc: int = 0

    # Size change adjustments (calculated)
    size_str: int = 0
    size_dex: int = 0
    size_con: int = 0
    size_nat_ac: int = 0

    # AC components
    base_nat_armor: int = 0
    base_armor: int = 0
    base_shield: int = 0
    base_deflection: int = 0
    base_dodge: int = 0

    # Combat
    bab_type: str = "averageBAB"
    base_bab: int = 0

    # Saves
    fort_type: str = "poorSave"
    ref_type: str = "poorSave"
    will_type: str = "goodSave"

    # Feats
    base_feats: str = ""
    acquired_feats: str = ""
    bonus_feat_count: int = 0

    # Attacks
    attacks: list = field(default_factory=list)

    # Class levels
    class_levels: list = field(default_factory=list)

    # Other
    speed: str = ""
    space: str = "5"
    reach: str = "5"
    special_attacks: str = ""
    special_qualities: str = ""
    skills_text: str = ""
    environment: str = ""
    organization: str = ""
    treasure: str = ""
    alignment: str = ""
    advancement: str = ""
    base_cr: float = 1.0
    level_adjustment: str = "-"

    # CR advancement divisor from type_rules (e.g. Animal=3, Dragon=2)
    cr_mod: int = 3

    # Toughness / special
    toughness_count: int = 0
    has_desecrating_aura: bool = False
    improved_nat_armor_count: int = 0

    # --- Computed Properties ---

    @property
    def total_str(self) -> int:
        return self.base_str + self.size_str + self.str_inc

    @property
    def total_dex(self) -> int:
        return self.base_dex + self.size_dex + self.dex_inc

    @property
    def total_con(self) -> Optional[int]:
        if self.type in ("Construct", "Undead"):
            return None  # no Con score
        return self.base_con + self.size_con + self.con_inc

    @property
    def total_int(self) -> int:
        return self.base_int + self.int_inc

    @property
    def total_wis(self) -> int:
        return self.base_wis + self.wis_inc

    @property
    def total_cha(self) -> int:
        return self.base_cha + self.cha_inc

    @property
    def str_mod(self) -> int:
        return ability_mod(self.total_str)

    @property
    def dex_mod(self) -> int:
        return ability_mod(self.total_dex)

    @property
    def con_mod(self) -> Optional[int]:
        c = self.total_con
        return ability_mod(c) if c is not None else None

    @property
    def int_mod(self) -> int:
        return ability_mod(self.total_int)

    @property
    def wis_mod(self) -> int:
        return ability_mod(self.total_wis)

    @property
    def cha_mod(self) -> int:
        return ability_mod(self.total_cha)

    @property
    def total_hd(self) -> int:
        """Monster HD + all class level HD."""
        class_hd = sum(cl.level for cl in self.class_levels)
        # Rule: 1 HD monsters lose their HD when gaining class levels
        if self.base_hd <= 1 and class_hd > 0:
            return class_hd
        return self.current_hd + class_hd

    @property
    def current_bab(self) -> int:
        """Combined BAB from monster HD + class levels."""
        monster_bab = calc_bab(self.current_hd, self.bab_type)
        # If 1 HD monster replaced by class, use only class BAB
        if self.base_hd <= 1 and self.class_levels:
            monster_bab = 0
        class_bab = sum(cl.bab for cl in self.class_levels)
        return monster_bab + class_bab

    @property
    def current_nat_armor(self) -> int:
        return self.base_nat_armor + self.size_nat_ac + self.improved_nat_armor_count

    @property
    def size_ac_mod(self) -> int:
        return SIZE_AC_MOD.get(self.current_size, 0)

    @property
    def total_ac(self) -> int:
        return (10 + self.size_ac_mod + self.dex_mod + self.current_nat_armor
                + self.base_armor + self.base_shield + self.base_deflection + self.base_dodge)

    @property
    def touch_ac(self) -> int:
        return 10 + self.size_ac_mod + self.dex_mod + self.base_deflection + self.base_dodge

    @property
    def flat_footed_ac(self) -> int:
        dex_penalty = min(self.dex_mod, 0)  # only negative dex applies to flat-footed
        return (10 + self.size_ac_mod + dex_penalty + self.current_nat_armor
                + self.base_armor + self.base_shield + self.base_deflection)

    @property
    def grapple(self) -> int:
        return self.current_bab + self.str_mod + SIZE_GRAPPLE_MOD.get(self.current_size, 0)

    @property
    def max_feats(self) -> int:
        """Max feats = 1 + total_hd // 3 + bonus_feat_count."""
        base = 1 + self.total_hd // 3
        # Fighter bonus feats
        fighter_bonus = 0
        for cl in self.class_levels:
            if cl.class_name == "Fighter":
                fighter_bonus = 1 + cl.level // 2  # 1st + every even level
        return base + self.bonus_feat_count + fighter_bonus

    @property
    def fort_save(self) -> int:
        monster_save = calc_save(self.current_hd, self.fort_type)
        if self.base_hd <= 1 and self.class_levels:
            monster_save = 0
        class_save = sum(cl.fort_save for cl in self.class_levels)
        con = self.con_mod or 0
        feat_bonus = 2 if "Great Fortitude" in self.all_feats_text else 0
        return monster_save + class_save + con + feat_bonus

    @property
    def ref_save(self) -> int:
        monster_save = calc_save(self.current_hd, self.ref_type)
        if self.base_hd <= 1 and self.class_levels:
            monster_save = 0
        class_save = sum(cl.ref_save for cl in self.class_levels)
        feat_bonus = 2 if "Lightning Reflexes" in self.all_feats_text else 0
        return monster_save + class_save + self.dex_mod + feat_bonus

    @property
    def will_save(self) -> int:
        monster_save = calc_save(self.current_hd, self.will_type)
        if self.base_hd <= 1 and self.class_levels:
            monster_save = 0
        class_save = sum(cl.will_save for cl in self.class_levels)
        feat_bonus = 2 if "Iron Will" in self.all_feats_text else 0
        return monster_save + class_save + self.wis_mod + feat_bonus

    @property
    def initiative(self) -> int:
        bonus = 4 if "Improved Initiative" in self.all_feats_text else 0
        return self.dex_mod + bonus

    @property
    def hp_average(self) -> int:
        """Calculate average HP."""
        # Monster HD HP
        if self.base_hd <= 1 and self.class_levels:
            monster_hp = 0
        else:
            avg_roll = (self.hd_type + 1) / 2
            con = self.con_mod or 0
            monster_hp = int(self.current_hd * (avg_roll + con))

        # Class level HP
        class_hp = 0
        for cl in self.class_levels:
            avg_roll = (cl.hd_type + 1) / 2
            con = self.con_mod or 0
            class_hp += int(cl.level * (avg_roll + con))

        # Toughness feat: +3 per occurrence
        toughness_hp = self.toughness_count * 3

        # Desecrating Aura: +2 * total HD
        desecrate_hp = self.total_hd * 2 if self.has_desecrating_aura else 0

        # Constructs get bonus HP from size
        construct_hp = 0
        if self.type == "Construct":
            construct_sizes = {
                "Small": 10, "Medium": 20, "Large": 30, "Huge": 40,
                "Gargantuan": 60, "Colossal": 80,
            }
            construct_hp = construct_sizes.get(self.current_size, 0)

        return max(1, monster_hp + class_hp + toughness_hp + desecrate_hp + construct_hp)

    @property
    def hp_text(self) -> str:
        """Generate HP text like '5d10+25 (52 hp)'."""
        parts = []

        # Monster HD
        if not (self.base_hd <= 1 and self.class_levels):
            parts.append(f"{self.current_hd}d{self.hd_type}")

        # Class HD
        for cl in self.class_levels:
            parts.append(f"{cl.level}d{cl.hd_type}")

        hd_text = " plus ".join(parts) if parts else "0"

        # Calculate bonus HP
        con = self.con_mod or 0
        total_bonus = con * self.total_hd + self.toughness_count * 3
        if self.has_desecrating_aura:
            total_bonus += self.total_hd * 2
        if self.type == "Construct":
            construct_sizes = {"Small": 10, "Medium": 20, "Large": 30, "Huge": 40, "Gargantuan": 60, "Colossal": 80}
            total_bonus += construct_sizes.get(self.current_size, 0)

        if total_bonus > 0:
            return f"{hd_text}+{total_bonus} ({self.hp_average} hp)"
        elif total_bonus < 0:
            return f"{hd_text}{total_bonus} ({self.hp_average} hp)"
        else:
            return f"{hd_text} ({self.hp_average} hp)"

    @property
    def all_feats_text(self) -> str:
        parts = []
        if self.base_feats:
            parts.append(self.base_feats)
        if self.acquired_feats:
            parts.append(self.acquired_feats)
        return ", ".join(parts)

    @property
    def current_cr(self) -> float:
        """CR = baseCR + INT((curHD - baseHD) / crMod)  — exact Excel formula."""
        hd_added = self.current_hd - self.base_hd
        cr_gain = int(hd_added / self.cr_mod) if hd_added > 0 and self.cr_mod > 0 else 0
        return self.base_cr + cr_gain

    @property
    def sneak_attack_dice(self) -> int:
        """Calculate Rogue sneak attack dice."""
        for cl in self.class_levels:
            if cl.class_name == "Rogue":
                return (cl.level + 1) // 2  # 1d6 at 1, 2d6 at 3, etc.
        return 0

    @property
    def barbarian_rage_per_day(self) -> int:
        for cl in self.class_levels:
            if cl.class_name == "Barbarian":
                return 1 + (cl.level - 1) // 4
        return 0

    @property
    def damage_reduction(self) -> str:
        for cl in self.class_levels:
            if cl.class_name == "Barbarian" and cl.level >= 7:
                dr = (cl.level - 4) // 3
                return f"DR {dr}/-"
        return ""


def ability_mod(score: int) -> int:
    """Calculate ability modifier: (score - 10) // 2"""
    return (score - 10) // 2


def calc_bab(hd: int, bab_type: str) -> int:
    """Calculate BAB from HD and progression type."""
    if bab_type in ("good", "goodBAB"):
        return hd
    elif bab_type in ("average", "averageBAB"):
        return int(hd * 3 / 4)
    else:  # poor
        return hd // 2


def calc_save(hd: int, save_type: str) -> int:
    """Calculate base save from HD and progression type."""
    if save_type in ("good", "goodSave"):
        return 2 + hd // 2
    else:  # poor
        return hd // 3


def get_size_transition(old_size: str, new_size: str) -> dict:
    """Get cumulative stat changes for a size transition."""
    old_idx = SIZE_ORDER.index(old_size)
    new_idx = SIZE_ORDER.index(new_size)

    if old_idx == new_idx:
        return {"str": 0, "dex": 0, "con": 0, "nat_ac": 0, "ac": 0, "atk": 0}

    total = {"str": 0, "dex": 0, "con": 0, "nat_ac": 0, "ac": 0, "atk": 0}
    step = 1 if new_idx > old_idx else -1

    for i in range(old_idx, new_idx, step):
        if step > 0:
            key = f"{SIZE_ORDER[i]} to {SIZE_ORDER[i + 1]}"
            if key in SIZE_TRANSITIONS:
                for k in total:
                    total[k] += SIZE_TRANSITIONS[key][k]
        else:
            key = f"{SIZE_ORDER[i - 1]} to {SIZE_ORDER[i]}"
            if key in SIZE_TRANSITIONS:
                for k in total:
                    total[k] -= SIZE_TRANSITIONS[key][k]

    return total


def scale_damage(dmg: str, steps: int) -> str:
    """Scale damage dice up or down by a number of size steps."""
    current = dmg
    for _ in range(abs(steps)):
        if steps > 0:
            current = DAMAGE_SCALE_UP.get(current, current)
        else:
            current = DAMAGE_SCALE_DOWN.get(current, current)
    return current


def calc_attack_roll(monster: AdvancedMonster, attack: AttackData) -> int:
    """Calculate attack roll bonus for a specific attack."""
    bab = monster.current_bab
    size_mod = SIZE_AC_MOD.get(monster.current_size, 0)  # same modifier

    # Ability modifier
    if attack.att_mode.lower() == "melee":
        ability_bonus = monster.str_mod
    else:
        ability_bonus = monster.dex_mod

    # Weapon Finesse check
    if "Weapon Finesse" in monster.all_feats_text and attack.weapon_nature.lower() == "natural":
        ability_bonus = max(monster.str_mod, monster.dex_mod)

    # Enhancement bonus
    enh = attack.att_roll_enh

    # Weapon Focus
    focus_bonus = 0
    if f"Weapon Focus ({attack.name})" in monster.all_feats_text or "Weapon Focus" in monster.all_feats_text:
        focus_bonus = 1

    # Multiattack penalty for secondary natural attacks
    multiattack_penalty = 0
    if attack.use_category.lower() == "natural_secondary":
        if "Multiattack" in monster.all_feats_text:
            multiattack_penalty = -2
        else:
            multiattack_penalty = -5

    return bab + ability_bonus + size_mod + enh + focus_bonus + multiattack_penalty


def calc_damage_bonus(monster: AdvancedMonster, attack: AttackData) -> int:
    """Calculate damage bonus for a specific attack."""
    str_bonus = int(monster.str_mod * attack.str_mult)
    enh = attack.dmg_enh

    # Weapon Specialization (Fighter only)
    spec_bonus = 0
    for cl in monster.class_levels:
        if cl.class_name == "Fighter" and cl.level >= 4:
            if f"Weapon Specialization ({attack.name})" in monster.all_feats_text:
                spec_bonus = 2

    return str_bonus + enh + spec_bonus


def format_attack_text(monster: AdvancedMonster, attack: AttackData, is_full: bool = True) -> str:
    """Format a single attack line."""
    roll = calc_attack_roll(monster, attack)
    dmg_bonus = calc_damage_bonus(monster, attack)

    roll_sign = "+" if roll >= 0 else ""
    bonus_text = f"+{dmg_bonus}" if dmg_bonus > 0 else (str(dmg_bonus) if dmg_bonus < 0 else "")

    count_text = f"{attack.count} " if attack.count > 1 and is_full else ""
    name_plural = attack.name + "s" if attack.count > 1 and is_full else attack.name

    dmg_text = f"{attack.dmg_die}{bonus_text}"

    return f"{count_text}{name_plural} {roll_sign}{roll} {attack.att_mode} ({dmg_text})"


def _build_attack_text(monster: AdvancedMonster, attacks: list) -> tuple[str, str]:
    """Return (standard_attack_text, full_attack_text) grouped by group_id."""
    if not attacks:
        return "", ""

    from collections import defaultdict
    groups: dict[int, list] = defaultdict(list)
    for a in attacks:
        groups[a.group_id].append(a)

    # Full attack: join groups with " or ", attacks within a group with " and "
    group_parts = []
    for gid in sorted(groups.keys()):
        atk_parts = [format_attack_text(monster, a, is_full=True) for a in groups[gid]]
        group_parts.append(" and ".join(atk_parts))
    full_attack = " or ".join(group_parts)

    # Standard attack: first standard attack in group 1, else first attack overall
    std = next((a for a in attacks if a.is_standard), attacks[0])
    standard_attack = format_attack_text(monster, std, is_full=False)

    return standard_attack, full_attack


def generate_stat_block(monster: AdvancedMonster) -> dict:
    """Generate a complete stat block dictionary."""
    # Class level text
    class_text = ""
    if monster.class_levels:
        parts = [f"{cl.class_name} {cl.level}" for cl in monster.class_levels]
        class_text = " / ".join(parts)

    # Type line
    type_line = f"{monster.current_size} {monster.type}"
    if monster.descriptor:
        type_line += f" ({monster.descriptor})"
    if class_text:
        type_line += f" / {class_text}"

    # Space / Reach — use size tables when size changed
    size_changed = monster.current_size != monster.original_size
    if size_changed:
        space_val = SIZE_SPACE.get(monster.current_size, monster.space)
        reach_val = str(SIZE_REACH_TALL.get(monster.current_size, 5))
    else:
        space_val = monster.space
        reach_val = monster.reach

    # Scale natural attack damage one step when size changes
    if size_changed:
        effective_attacks = [
            replace(a, dmg_die=scale_damage(a.dmg_die, 1)) if a.weapon_nature.lower() == "natural" else a
            for a in monster.attacks
        ]
    else:
        effective_attacks = monster.attacks

    # Build attack text
    standard_attack, full_attack = _build_attack_text(monster, effective_attacks)

    # AC text
    ac_parts = []
    if monster.size_ac_mod != 0:
        ac_parts.append(f"{monster.size_ac_mod:+d} size")
    if monster.dex_mod != 0:
        ac_parts.append(f"{monster.dex_mod:+d} Dex")
    if monster.current_nat_armor != 0:
        ac_parts.append(f"+{monster.current_nat_armor} natural")
    if monster.base_armor != 0:
        ac_parts.append(f"+{monster.base_armor} armor")
    if monster.base_shield != 0:
        ac_parts.append(f"+{monster.base_shield} shield")
    if monster.base_deflection != 0:
        ac_parts.append(f"+{monster.base_deflection} deflection")
    if monster.base_dodge != 0:
        ac_parts.append(f"+{monster.base_dodge} dodge")

    ac_breakdown = ", ".join(ac_parts)
    ac_text = f"{monster.total_ac} ({ac_breakdown}), touch {monster.touch_ac}, flat-footed {monster.flat_footed_ac}"

    # Save text
    saves_text = f"Fort {monster.fort_save:+d}, Ref {monster.ref_save:+d}, Will {monster.will_save:+d}"

    # Abilities text
    abilities = []
    abilities.append(f"Str {monster.total_str}")
    abilities.append(f"Dex {monster.total_dex}")
    con = monster.total_con
    abilities.append(f"Con {con}" if con is not None else "Con -")
    abilities.append(f"Int {monster.total_int}")
    abilities.append(f"Wis {monster.total_wis}")
    abilities.append(f"Cha {monster.total_cha}")
    abilities_text = ", ".join(abilities)

    # Class features text
    class_features = []
    for cl in monster.class_levels:
        if cl.features:
            class_features.append(f"{cl.class_name} {cl.level}: {cl.features}")

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
        "intelligence": monster.total_int,
        "wis": monster.total_wis,
        "cha": monster.total_cha,
        "feats": monster.all_feats_text,
        "max_feats": monster.max_feats,
        "skills": monster.skills_text,
        "special_attacks": monster.special_attacks,
        "special_qualities": monster.special_qualities,
        "environment": monster.environment,
        "organization": monster.organization,
        "challenge_rating": monster.current_cr,
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
        # Combat details
        "sneak_attack_dice": monster.sneak_attack_dice,
        "barbarian_rage_per_day": monster.barbarian_rage_per_day,
        "damage_reduction": monster.damage_reduction,
    }
