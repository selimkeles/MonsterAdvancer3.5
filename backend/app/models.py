"""SQLAlchemy ORM models mapping to our SQLite tables."""
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Monster(Base):
    __tablename__ = "monsters"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    size = Column(String)
    type = Column(String)
    descriptor = Column(String)
    hd_count = Column(Integer)
    hit_dice = Column(String)
    initiative = Column(String)
    speed = Column(String)
    armor_class = Column(String)
    base_attack = Column(Integer)
    grapple = Column(String)
    attack = Column(String)
    full_attack = Column(String)
    space = Column(String)
    reach = Column(String)
    special_attacks = Column(Text)
    special_qualities = Column(Text)
    skills = Column(Text)
    feats = Column(Text)
    bonus_feats = Column(Text)
    saves = Column(String)
    # Per-row save progressions exist because the SRD type table marks
    # Humanoid as "Varies" — the specific good save can't be derived
    # from the creature type alone.
    fort_save_type = Column(String)
    ref_save_type = Column(String)
    will_save_type = Column(String)
    str = Column(Integer)
    dex = Column(Integer)
    con = Column(Integer)
    int = Column(Integer)
    wis = Column(Integer)
    cha = Column(Integer)
    environment = Column(String)
    organization = Column(String)
    challenge_rating = Column(Float)
    treasure = Column(String)
    alignment = Column(String)
    advancement = Column(Text)
    advancement_type = Column(String)       # 'hd' | 'hd_or_class' | 'class' | 'special' | 'none'
    adv_max_hd = Column(Integer)            # NULL when open-ended or non-advancing
    adv_size_thresholds = Column(Text)      # JSON: [[min_hd, "Size"], ...]
    ac_total = Column(Integer)              # parsed from armor_class text
    ac_touch = Column(Integer)
    ac_flat_footed = Column(Integer)
    special_abilities = Column(Text)
    reference = Column(String)
    level_adjustment = Column(String)
    altname = Column(String)

    attacks = relationship("Attack", back_populates="monster")
    ac_components = relationship("ArmorClassComponent", back_populates="monster", uselist=False)


class Attack(Base):
    __tablename__ = "attacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monster_id = Column(Integer, ForeignKey("monsters.id"), nullable=False)
    group_id = Column(Integer)
    att_name = Column(String)
    att_count = Column(Integer)
    is_standard = Column(Integer)
    weapon_nature = Column(String)
    att_mode = Column(String)
    use_category = Column(String)
    dmg_die = Column(String)
    crit_range = Column(String)
    crit_mult = Column(Integer)
    str_mult = Column(Float)
    att_roll_enh = Column(Integer, default=0)
    dmg_enh = Column(Integer, default=0)
    dmg_composite = Column(String)
    dmg_text = Column(String)
    weapon_text = Column(String)
    # Per-attack reach for asymmetric creatures (e.g., a long-armed monster
    # with bite reach 5 ft. and tentacle reach 10 ft.). NULL falls back to
    # the monster's default `reach` column.
    reach = Column(String)

    monster = relationship("Monster", back_populates="attacks")


class ArmorClassComponent(Base):
    __tablename__ = "armor_class_components"

    id = Column(Integer, primary_key=True)
    monster_id = Column(Integer, ForeignKey("monsters.id"), nullable=False)
    name = Column(String)
    base_nat_armor = Column(Integer, default=0)
    base_armor = Column(Integer, default=0)
    base_armor_description = Column(String)
    base_deflection = Column(Integer, default=0)
    base_deflection_description = Column(String)
    base_shield = Column(Integer, default=0)
    base_shield_description = Column(String)
    base_dodge = Column(Integer, default=0)
    base_dodge_description = Column(String)

    monster = relationship("Monster", back_populates="ac_components")


class TypeRule(Base):
    __tablename__ = "type_rules"

    type_name = Column(String, primary_key=True)
    hd_type = Column(Integer)
    bab_progression = Column(String)
    skill_point_base = Column(Integer)
    cr_mod = Column(Integer)


class SizeChange(Base):
    __tablename__ = "size_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    size_transition = Column(String, nullable=False)
    str_change = Column(Integer)
    dex_change = Column(Integer)
    con_change = Column(Integer)
    nat_armor_change = Column(Integer)
    ac_change = Column(Integer)
    attack_change = Column(Integer)


class DamageScaling(Base):
    __tablename__ = "damage_scaling"

    old_damage = Column(String, primary_key=True)
    new_damage = Column(String)


class Feat(Base):
    __tablename__ = "feats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)


class ClassDef(Base):
    __tablename__ = "classes"

    name = Column(String, primary_key=True)
    category = Column(String)
    hd_type = Column(Integer)
    bab_progression = Column(String)
    fort_progression = Column(String)
    ref_progression = Column(String)
    will_progression = Column(String)
    skill_points_base = Column(Integer)
    weapon_proficiency = Column(String)
    armor_proficiency = Column(String)
    description = Column(Text)


class ClassProgression(Base):
    __tablename__ = "class_progression"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_name = Column(String, nullable=False)
    level = Column(Integer, nullable=False)
    bab = Column(Integer)
    fort_save = Column(Integer)
    ref_save = Column(Integer)
    will_save = Column(Integer)
    hd_type = Column(Integer)
    skill_points_per_level = Column(Integer)
    features = Column(Text)


class Weapon(Base):
    __tablename__ = "weapons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String)
    subcategory = Column(String)
    cost = Column(String)
    dmg_small = Column(String)
    dmg_medium = Column(String)
    critical = Column(String)
    range_increment = Column(String)
    weight = Column(Float)
    damage_type = Column(String)
    special = Column(String)


class Armor(Base):
    __tablename__ = "armor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String)
    ac_bonus = Column(Integer)
    max_dex = Column(Integer)
    check_penalty = Column(Integer)
    spell_failure = Column(Integer)
    speed_30 = Column(String)
    speed_20 = Column(String)
    weight = Column(Float)
    cost = Column(String)
