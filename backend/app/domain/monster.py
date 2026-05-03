"""
Domain dataclasses for an in-flight monster advancement.

`AdvancedMonster` is a value object describing the user's *intent* — base
creature plus all advancement choices (size change, added HD, class
levels, ability bumps, equipped armor, manually-added feats). Its
properties are computed on demand by delegating to the SRD rule modules
in `app.rules`.

The dataclass is intentionally not bound to SQLAlchemy — DB rows are
loaded into ORM models in `app.models` (the legacy module under
`app/models.py`); the conversion happens in the service layer.
"""
from dataclasses import dataclass, field
from typing import Optional

from ..rules.abilities import ability_mod
from ..rules.bab import calc_bab
from ..rules.saves import calc_save
from ..rules.sizes import (
    SIZE_AC_MOD,
    SIZE_GRAPPLE_MOD,
    SIZE_ORDER,
    is_tiny_or_smaller,
)
from ..rules.hit_dice import (
    CONSTRUCT_BONUS_HP,
    average_hp_for_hd,
    replaces_monster_hd,
    total_hd as compute_total_hd,
)
from ..rules.feats import feat_count
from ..rules.skills import apply_skill_increases, skill_points_per_hd
from ..rules.class_levels import (
    barbarian_dr,
    barbarian_rage_per_day,
    fighter_bonus_feats,
    sneak_attack_dice,
)
from ..rules.challenge_rating import (
    ExtraCRModifiers,
    cr_from_class_levels,
    cr_from_hd_advancement,
    extra_cr_modifiers,
)
from ..rules.abilities import hd_increase_ability_points
from ..rules.class_levels import NPC_CLASSES


@dataclass
class AttackData:
    """One row from the attacks table — natural or manufactured weapon."""
    name: str
    count: int = 1
    is_standard: bool = True
    weapon_nature: str = "natural"           # "natural" or "manufactured"
    att_mode: str = "melee"                   # "melee" or "ranged"
    use_category: str = "natural_Primary"     # natural_Primary / natural_secondary / weapon_TH / weapon_OH
    dmg_die: str = "1d6"
    crit_range: str = "20"
    crit_mult: int = 2
    str_mult: float = 1.0                     # 1.5 for two-handed / sole natural; 0.5 for off-hand
    att_roll_enh: int = 0
    dmg_enh: int = 0
    group_id: int = 1                         # attacks in same group → "and"; different groups → "or"


@dataclass
class ClassLevel:
    """One leg of a multiclass progression added on top of monster HD."""
    class_name: str
    level: int
    hd_type: int
    bab: int
    fort_save: int
    ref_save: int
    will_save: int
    skill_points_per_level: int
    features: str = ""
    # SRD CR rule: a class is "associated" when it plays to the creature's
    # existing strengths (e.g. Fighter for a melee monster). Default False
    # means the level counts as nonassociated for CR purposes.
    is_associated: bool = False
    # NPC classes are *always* nonassociated per SRD, regardless of the
    # flag above. The orchestrator should set this when seeding from
    # `app.rules.class_levels.NPC_CLASSES`.
    is_npc_class: bool = False


@dataclass
class AdvancedMonster:
    """
    Full state of a monster mid-advancement. All "current_*" fields reflect
    the user's chosen advancement; "base_*" fields preserve the original
    statblock so deltas can be computed (e.g., for CR and ability bumps).
    """

    # Identity
    name: str
    original_size: str
    current_size: str
    type: str
    descriptor: str = ""

    # Hit Dice
    base_hd: int = 1
    current_hd: int = 1
    hd_type: int = 8

    # Ability scores — base (from statblock) + size adjustments + manual bumps.
    base_str: int = 10
    base_dex: int = 10
    base_con: int = 10
    base_int: int = 10
    base_wis: int = 10
    base_cha: int = 10
    str_inc: int = 0
    dex_inc: int = 0
    con_inc: int = 0
    int_inc: int = 0
    wis_inc: int = 0
    cha_inc: int = 0

    # Pre-computed size transition deltas (filled by the orchestrator).
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
    armor_max_dex: Optional[int] = None
    is_masterwork_armor: bool = False

    # Combat — type-derived progressions.
    bab_type: str = "averageBAB"
    base_bab: int = 0

    # Saves — which one is "good" depends on type rules.
    fort_type: str = "poorSave"
    ref_type: str = "poorSave"
    will_type: str = "goodSave"

    # Feats — text strings for compatibility with the seeded data.
    base_feats: str = ""
    acquired_feats: str = ""
    bonus_feat_count: int = 0

    # Attacks and class levels (lists default to empty, never shared).
    attacks: list = field(default_factory=list)
    class_levels: list = field(default_factory=list)

    # Misc
    speed: str = ""
    space: str = "5"
    reach: str = "5"
    special_attacks: str = ""
    special_qualities: str = ""
    skills_text: str = ""
    skill_increases: dict = field(default_factory=dict)
    type_skill_points: int = 2
    environment: str = ""
    organization: str = ""
    treasure: str = ""
    alignment: str = ""
    advancement: str = ""
    base_cr: float = 1.0
    level_adjustment: str = "-"

    # Per-type CR divisor (Animal=3, Dragon=2, Aberration=4, ...).
    cr_mod: int = 3

    # ----- SRD: Int "—" (no Intelligence score) -----
    # When False, the creature gains 0 feats and 0 skill points per HD
    # (Constructs and Oozes by default; certain mindless undead too).
    has_intelligence: bool = True

    # ----- SRD: flat CR adders from "Improved Monster CR Increase" -----
    # The orchestrator/UI sets these based on user choices. Each adds a
    # fixed amount on top of the HD-progression CR.
    uses_elite_array: bool = False                    # +1 CR
    has_significant_special_abilities: bool = False   # +2 CR
    has_minor_special_abilities: bool = False         # +1 CR (only if not significant)

    # Special add-ons
    toughness_count: int = 0
    has_desecrating_aura: bool = False
    improved_nat_armor_count: int = 0

    # ------------------------------------------------------------------
    # Ability scores
    # ------------------------------------------------------------------

    @property
    def total_str(self) -> int:
        return self.base_str + self.size_str + self.str_inc

    @property
    def total_dex(self) -> int:
        return self.base_dex + self.size_dex + self.dex_inc

    @property
    def total_con(self) -> Optional[int]:
        # SRD: Constructs and Undead have no Con score.
        if self.type in ("Construct", "Undead"):
            return None
        return self.base_con + self.size_con + self.con_inc

    @property
    def total_int(self) -> Optional[int]:
        # SRD: Int "—" creatures (no Int score) are reported as None and
        # display as "Int -" in the stat block; numeric Int math falls
        # back to 0 via `int_mod` below.
        if not self.has_intelligence:
            return None
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
        # No Int score → 0 modifier for any callers that still need a
        # number (skill-bonus arithmetic, stat-block formatting).
        i = self.total_int
        return ability_mod(i) if i is not None else 0

    @property
    def wis_mod(self) -> int:
        return ability_mod(self.total_wis)

    @property
    def cha_mod(self) -> int:
        return ability_mod(self.total_cha)

    # ------------------------------------------------------------------
    # Hit Dice / replacement rule
    # ------------------------------------------------------------------

    @property
    def class_hd_total(self) -> int:
        return sum(cl.level for cl in self.class_levels)

    @property
    def total_hd(self) -> int:
        return compute_total_hd(self.base_hd, self.current_hd, self.class_hd_total)

    @property
    def _replaces_monster_hd(self) -> bool:
        return replaces_monster_hd(self.base_hd, bool(self.class_levels))

    # ------------------------------------------------------------------
    # BAB / saves / grapple / initiative
    # ------------------------------------------------------------------

    @property
    def current_bab(self) -> int:
        # 1-HD humanoid replacement: ignore the racial BAB when class
        # levels are taken (per SRD: "the monster loses the attack bonus
        # ... granted by its 1 monster HD").
        monster_bab = 0 if self._replaces_monster_hd else calc_bab(self.current_hd, self.bab_type)
        return monster_bab + sum(cl.bab for cl in self.class_levels)

    @property
    def fort_save(self) -> int:
        monster = 0 if self._replaces_monster_hd else calc_save(self.current_hd, self.fort_type)
        class_bonus = sum(cl.fort_save for cl in self.class_levels)
        con = self.con_mod or 0
        feat_bonus = 2 if "Great Fortitude" in self.all_feats_text else 0
        return monster + class_bonus + con + feat_bonus

    @property
    def ref_save(self) -> int:
        monster = 0 if self._replaces_monster_hd else calc_save(self.current_hd, self.ref_type)
        class_bonus = sum(cl.ref_save for cl in self.class_levels)
        feat_bonus = 2 if "Lightning Reflexes" in self.all_feats_text else 0
        return monster + class_bonus + self.dex_mod + feat_bonus

    @property
    def will_save(self) -> int:
        monster = 0 if self._replaces_monster_hd else calc_save(self.current_hd, self.will_type)
        class_bonus = sum(cl.will_save for cl in self.class_levels)
        feat_bonus = 2 if "Iron Will" in self.all_feats_text else 0
        return monster + class_bonus + self.wis_mod + feat_bonus

    @property
    def initiative(self) -> int:
        bonus = 4 if "Improved Initiative" in self.all_feats_text else 0
        return self.dex_mod + bonus

    @property
    def grapple(self) -> int:
        return self.current_bab + self.str_mod + SIZE_GRAPPLE_MOD.get(self.current_size, 0)

    # ------------------------------------------------------------------
    # AC components
    # ------------------------------------------------------------------

    @property
    def current_nat_armor(self) -> int:
        return self.base_nat_armor + self.size_nat_ac + self.improved_nat_armor_count

    @property
    def size_ac_mod(self) -> int:
        return SIZE_AC_MOD.get(self.current_size, 0)

    @property
    def effective_max_dex(self) -> Optional[int]:
        """Masterwork armor raises the max-Dex cap by 1."""
        if self.armor_max_dex is None:
            return None
        return self.armor_max_dex + (1 if self.is_masterwork_armor else 0)

    @property
    def effective_dex_to_ac(self) -> int:
        cap = self.effective_max_dex
        return min(self.dex_mod, cap) if cap is not None else self.dex_mod

    @property
    def effective_armor(self) -> int:
        # Tiny-or-smaller creatures use halved manufactured armor bonuses.
        return self.base_armor // 2 if is_tiny_or_smaller(self.current_size) else self.base_armor

    @property
    def effective_shield(self) -> int:
        return self.base_shield // 2 if is_tiny_or_smaller(self.current_size) else self.base_shield

    @property
    def total_ac(self) -> int:
        return (
            10 + self.size_ac_mod + self.effective_dex_to_ac + self.current_nat_armor
            + self.effective_armor + self.effective_shield
            + self.base_deflection + self.base_dodge
        )

    @property
    def touch_ac(self) -> int:
        # Touch AC drops armor, shield, natural — but keeps size, Dex,
        # deflection, and dodge.
        return 10 + self.size_ac_mod + self.effective_dex_to_ac + self.base_deflection + self.base_dodge

    @property
    def flat_footed_ac(self) -> int:
        # Flat-footed: lose Dex bonus (penalties still apply); also loses dodge.
        dex_penalty = min(self.effective_dex_to_ac, 0)
        return (
            10 + self.size_ac_mod + dex_penalty + self.current_nat_armor
            + self.effective_armor + self.effective_shield + self.base_deflection
        )

    # ------------------------------------------------------------------
    # HP
    # ------------------------------------------------------------------

    @property
    def hp_average(self) -> int:
        con = self.con_mod or 0
        monster_hp = 0 if self._replaces_monster_hd else average_hp_for_hd(
            self.current_hd, self.hd_type, con
        )
        class_hp = sum(average_hp_for_hd(cl.level, cl.hd_type, con) for cl in self.class_levels)
        toughness_hp = self.toughness_count * 3
        desecrate_hp = self.total_hd * 2 if self.has_desecrating_aura else 0
        construct_hp = (
            CONSTRUCT_BONUS_HP.get(self.current_size, 0) if self.type == "Construct" else 0
        )
        return max(1, monster_hp + class_hp + toughness_hp + desecrate_hp + construct_hp)

    @property
    def hp_text(self) -> str:
        """Stat-block style HP line: '5d10+25 (52 hp)'."""
        parts = []
        if not self._replaces_monster_hd:
            parts.append(f"{self.current_hd}d{self.hd_type}")
        for cl in self.class_levels:
            parts.append(f"{cl.level}d{cl.hd_type}")
        hd_text = " plus ".join(parts) if parts else "0"

        con = self.con_mod or 0
        total_bonus = con * self.total_hd + self.toughness_count * 3
        if self.has_desecrating_aura:
            total_bonus += self.total_hd * 2
        if self.type == "Construct":
            total_bonus += CONSTRUCT_BONUS_HP.get(self.current_size, 0)

        if total_bonus > 0:
            return f"{hd_text}+{total_bonus} ({self.hp_average} hp)"
        if total_bonus < 0:
            return f"{hd_text}{total_bonus} ({self.hp_average} hp)"
        return f"{hd_text} ({self.hp_average} hp)"

    # ------------------------------------------------------------------
    # Feats
    # ------------------------------------------------------------------

    @property
    def all_feats_text(self) -> str:
        parts = [s for s in (self.base_feats, self.acquired_feats) if s]
        return ", ".join(parts)

    @property
    def max_feats(self) -> int:
        # SRD: creatures with Int "—" gain 0 feats; otherwise 1 + HD/3
        # plus Fighter bonus feats. `bonus_feat_count` covers extras
        # granted by templates or special qualities.
        fighter_levels = sum(cl.level for cl in self.class_levels if cl.class_name == "Fighter")
        base = feat_count(
            self.total_hd,
            has_intelligence=self.has_intelligence,
            fighter_levels=fighter_levels,
        )
        # No Int → no bonus feats either (templates that want to grant a
        # feat to a mindless creature must override has_intelligence).
        return base + (self.bonus_feat_count if self.has_intelligence else 0)

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    @property
    def skill_points_per_hd(self) -> int:
        return skill_points_per_hd(
            self.type_skill_points,
            self.int_mod,
            has_intelligence=self.has_intelligence,
        )

    @property
    def base_skill_points(self) -> int:
        return self.skill_points_per_hd * self.base_hd

    @property
    def total_skill_points(self) -> int:
        monster_sp = 0 if self._replaces_monster_hd else self.skill_points_per_hd * self.current_hd
        # SRD: Int "—" creatures get 0 skill points from class levels too.
        # In practice they can't take classes (Int 3 required for ECL),
        # but the guard makes the math defensive.
        if not self.has_intelligence:
            class_sp = 0
        else:
            class_sp = sum(
                max(1, cl.skill_points_per_level + self.int_mod) * cl.level
                for cl in self.class_levels
            )
        return monster_sp + class_sp

    @property
    def bonus_skill_points(self) -> int:
        return self.total_skill_points - self.base_skill_points

    @property
    def spent_skill_points(self) -> int:
        return sum(self.skill_increases.values())

    @property
    def updated_skills_text(self) -> str:
        return apply_skill_increases(self.skills_text, self.skill_increases) if self.skill_increases else self.skills_text

    # ------------------------------------------------------------------
    # Challenge Rating — full SRD calculation
    # ------------------------------------------------------------------
    # Final CR = base CR
    #          + HD-progression CR (cr_mod-based, from added racial HD)
    #          + class-level CR    (associated/nonassociated split)
    #          + flat adders       (Large+ size, elite array, special abs)
    #
    # SRD caveat: "Do not stack [HD] CR increase with any increase from
    # class levels." The summation here treats them as additive because
    # in practice monsters advance via *one* of the two but the data
    # model allows both; users / templates set whichever is appropriate.

    @property
    def _size_increased_to_large_plus(self) -> bool:
        # Only counts when the size was *increased* past Medium during
        # advancement (not when the creature was already Large at base).
        large_idx = SIZE_ORDER.index("Large")
        return (
            SIZE_ORDER.index(self.current_size) >= large_idx
            and SIZE_ORDER.index(self.current_size) > SIZE_ORDER.index(self.original_size)
        )

    @property
    def cr_extra_modifiers(self) -> int:
        """Sum of the flat adders from the SRD CR table."""
        return extra_cr_modifiers(ExtraCRModifiers(
            size_increased_to_large_plus=self._size_increased_to_large_plus,
            uses_elite_array=self.uses_elite_array,
            significant_special_abilities=self.has_significant_special_abilities,
            minor_special_abilities=self.has_minor_special_abilities,
        ))

    @property
    def cr_from_classes(self) -> float:
        """
        CR delta contributed by class levels.

        Associated:    +1 per level.
        Nonassociated: +½ per level until count == base_hd, then +1.
        NPC classes:   always nonassociated, regardless of `is_associated`.
        """
        associated = 0
        nonassociated = 0
        for cl in self.class_levels:
            forced_nonassoc = cl.is_npc_class or (cl.class_name in NPC_CLASSES)
            if cl.is_associated and not forced_nonassoc:
                associated += cl.level
            else:
                nonassociated += cl.level
        return cr_from_class_levels(associated, nonassociated, self.base_hd)

    @property
    def current_cr(self) -> float:
        hd_cr = cr_from_hd_advancement(
            self.base_cr, self.base_hd, self.current_hd, self.cr_mod
        )
        return hd_cr + self.cr_from_classes + self.cr_extra_modifiers

    # ------------------------------------------------------------------
    # SRD: Ability score increases from added HD
    # ------------------------------------------------------------------
    @property
    def available_ability_points(self) -> int:
        """
        Number of +1 ability bumps the creature has *earned* from HD
        advancement (4th, 8th, 12th, … total HD threshold crossings,
        counted only on HD added past base_hd per the SRD).

        These are budget; the user spends them via the `*_inc` fields.
        """
        return hd_increase_ability_points(self.base_hd, self.total_hd)

    @property
    def spent_ability_points(self) -> int:
        """Total +1 increments the user has applied across all six abilities."""
        return self.str_inc + self.dex_inc + self.con_inc + self.int_inc + self.wis_inc + self.cha_inc

    # ------------------------------------------------------------------
    # Class-feature pass-throughs
    # ------------------------------------------------------------------

    @property
    def sneak_attack_dice(self) -> int:
        rogue = sum(cl.level for cl in self.class_levels if cl.class_name == "Rogue")
        return sneak_attack_dice(rogue)

    @property
    def barbarian_rage_per_day(self) -> int:
        barb = sum(cl.level for cl in self.class_levels if cl.class_name == "Barbarian")
        return barbarian_rage_per_day(barb)

    @property
    def damage_reduction(self) -> str:
        barb = sum(cl.level for cl in self.class_levels if cl.class_name == "Barbarian")
        return barbarian_dr(barb)
