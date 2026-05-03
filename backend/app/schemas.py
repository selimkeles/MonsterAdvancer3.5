"""Pydantic schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel


class MonsterSummary(BaseModel):
    id: int
    name: str
    size: Optional[str] = None
    type: Optional[str] = None
    challenge_rating: Optional[float] = None
    hd_count: Optional[int] = None
    alignment: Optional[str] = None
    advancement: Optional[str] = None
    environment: Optional[str] = None


class MonsterDetail(BaseModel):
    id: int
    name: str
    size: Optional[str] = None
    type: Optional[str] = None
    descriptor: Optional[str] = None
    hd_count: Optional[int] = None
    hit_dice: Optional[str] = None
    initiative: Optional[str] = None
    speed: Optional[str] = None
    armor_class: Optional[str] = None
    ac_total: Optional[int] = None
    ac_touch: Optional[int] = None
    ac_flat_footed: Optional[int] = None
    base_attack: Optional[int] = None
    grapple: Optional[str] = None
    attack: Optional[str] = None
    full_attack: Optional[str] = None
    space: Optional[str] = None
    reach: Optional[str] = None
    special_attacks: Optional[str] = None
    special_qualities: Optional[str] = None
    skills: Optional[str] = None
    feats: Optional[str] = None
    bonus_feats: Optional[str] = None
    fort_save_type: Optional[str] = None
    ref_save_type: Optional[str] = None
    will_save_type: Optional[str] = None
    strength: Optional[int] = None
    dex: Optional[int] = None
    con: Optional[int] = None
    intelligence: Optional[int] = None
    wis: Optional[int] = None
    cha: Optional[int] = None
    environment: Optional[str] = None
    organization: Optional[str] = None
    challenge_rating: Optional[float] = None
    treasure: Optional[str] = None
    alignment: Optional[str] = None
    advancement: Optional[str] = None
    advancement_type: Optional[str] = None   # 'hd'|'hd_or_class'|'class'|'special'|'none'
    adv_max_hd: Optional[int] = None         # None = open-ended or non-advancing
    adv_size_thresholds: list = []           # [[min_hd, "Size"], ...]
    # Convenience booleans for the frontend, derived from advancement_type
    can_advance_hd: bool = False             # True for 'hd' and 'hd_or_class'
    advances_by_class: bool = False          # True for 'class' and 'hd_or_class'
    special_abilities: Optional[str] = None
    level_adjustment: Optional[str] = None
    attacks: list = []
    ac_components: Optional[dict] = None


class AttackSchema(BaseModel):
    id: int
    att_name: Optional[str] = None
    att_count: Optional[int] = None
    is_standard: Optional[int] = None
    weapon_nature: Optional[str] = None
    att_mode: Optional[str] = None
    use_category: Optional[str] = None
    dmg_die: Optional[str] = None
    crit_range: Optional[str] = None
    crit_mult: Optional[int] = None
    str_mult: Optional[float] = None
    group_id: Optional[int] = None
    reach: Optional[str] = None


class ACComponentSchema(BaseModel):
    base_nat_armor: int = 0
    base_armor: int = 0
    base_armor_description: Optional[str] = None
    base_deflection: int = 0
    base_deflection_description: Optional[str] = None
    base_shield: int = 0
    base_shield_description: Optional[str] = None
    base_dodge: int = 0
    base_dodge_description: Optional[str] = None


class ClassLevelRequest(BaseModel):
    class_name: str
    level: int


class AdvancementRequest(BaseModel):
    monster_id: int
    new_hd: Optional[int] = None
    ability_increases: Optional[dict] = None  # {"str": 2, "dex": 0, ...}
    acquired_feats: Optional[str] = None
    class_levels: list[ClassLevelRequest] = []
    equipped_armor: Optional[str] = None
    equipped_shield: Optional[str] = None
    is_masterwork_armor: bool = False
    skill_increases: Optional[dict] = None  # {"Climb": 2, "Hide": 1, ...}


class StatBlockResponse(BaseModel):
    name: str
    type_line: str
    hit_points: str
    hp_average: int
    initiative: str
    speed: str
    armor_class: str
    total_ac: int
    touch_ac: int
    flat_footed_ac: int
    base_attack: str
    grapple: str
    saves: str
    fort_save: int
    ref_save: int
    will_save: int
    abilities: str
    strength: int
    dex: int
    con: Optional[int] = None
    intelligence: Optional[int] = None  # None for Int "—" creatures
    wis: int
    cha: int
    feats: str
    max_feats: int
    skills: str
    bonus_skill_points: int = 0
    spent_skill_points: int = 0
    special_attacks: str
    special_qualities: str
    environment: str
    organization: str
    challenge_rating: float
    treasure: str
    alignment: str
    advancement: str
    level_adjustment: str
    space_reach: str
    attack: str = ""
    full_attack: str = ""
    class_levels: str
    class_features: list[str]
    total_hd: int
    current_size: str
    sneak_attack_dice: int = 0
    barbarian_rage_per_day: int = 0
    damage_reduction: str = ""


class WeaponSchema(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    dmg_small: Optional[str] = None
    dmg_medium: Optional[str] = None
    critical: Optional[str] = None
    range_increment: Optional[str] = None
    weight: Optional[float] = None
    damage_type: Optional[str] = None
    special: Optional[str] = None


class ArmorSchema(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    ac_bonus: Optional[int] = None
    max_dex: Optional[int] = None
    check_penalty: Optional[int] = None
    spell_failure: Optional[int] = None
    weight: Optional[float] = None


class ClassSchema(BaseModel):
    name: str
    category: Optional[str] = None
    hd_type: Optional[int] = None
    bab_progression: Optional[str] = None
    fort_progression: Optional[str] = None
    ref_progression: Optional[str] = None
    will_progression: Optional[str] = None
    skill_points_base: Optional[int] = None
    weapon_proficiency: Optional[str] = None
    armor_proficiency: Optional[str] = None
    description: Optional[str] = None


class ClassProgressionSchema(BaseModel):
    level: int
    bab: int
    fort_save: int
    ref_save: int
    will_save: int
    hd_type: int
    features: Optional[str] = None


class MonsterFilter(BaseModel):
    min_cr: Optional[float] = None
    max_cr: Optional[float] = None
    type: Optional[str] = None
    size: Optional[str] = None
    environment: Optional[str] = None
    alignment: Optional[str] = None
    search: Optional[str] = None
