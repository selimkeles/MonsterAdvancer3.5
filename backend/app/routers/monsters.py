"""Monster API endpoints."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import Monster, Attack, ArmorClassComponent, TypeRule, ClassProgression, Weapon, Armor, ClassDef, Feat
from ..schemas import (
    MonsterSummary, MonsterDetail, AttackSchema, ACComponentSchema,
    AdvancementRequest, StatBlockResponse, WeaponSchema, ArmorSchema,
    ClassSchema, ClassProgressionSchema, MonsterFilter,
)
from ..services.calculator import (
    AdvancedMonster, AttackData, ClassLevel, generate_stat_block,
    get_size_transition, SIZE_ORDER,
)

router = APIRouter()

_HD_TYPES = frozenset({"hd", "hd_or_class"})
_CLASS_TYPES = frozenset({"class", "hd_or_class"})


def _advancement_fields(monster: Monster) -> dict:
    """Derive frontend advancement fields from the normalised DB columns."""
    adv_type = monster.advancement_type or "none"
    thresholds = []
    try:
        raw = monster.adv_size_thresholds
        if raw:
            thresholds = json.loads(raw)
    except (ValueError, TypeError):
        pass
    return {
        "advancement_type": adv_type,
        "adv_max_hd": monster.adv_max_hd,
        "adv_size_thresholds": thresholds,
        "can_advance_hd": adv_type in _HD_TYPES,
        "advances_by_class": adv_type in _CLASS_TYPES,
    }


def combined_feats(monster: Monster) -> str:
    """Replace the dropped `all_feats` column: feats + bonus_feats joined."""
    parts = [s for s in (monster.feats, monster.bonus_feats) if s]
    return ", ".join(parts)


def bonus_feat_count(monster: Monster) -> int:
    """Replace the dropped `bonus_feat_count` column: count comma-separated entries."""
    if not monster.bonus_feats:
        return 0
    return sum(1 for x in monster.bonus_feats.split(",") if x.strip())


@router.get("/monsters", response_model=list[MonsterSummary])
def list_monsters(
    min_cr: Optional[float] = None,
    max_cr: Optional[float] = None,
    type: Optional[str] = None,
    size: Optional[str] = None,
    environment: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=600),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Monster)
    if min_cr is not None:
        q = q.filter(Monster.challenge_rating >= min_cr)
    if max_cr is not None:
        q = q.filter(Monster.challenge_rating <= max_cr)
    if type:
        q = q.filter(Monster.type == type)
    if size:
        q = q.filter(Monster.size == size)
    if environment:
        q = q.filter(Monster.environment.contains(environment))
    if search:
        q = q.filter(Monster.name.ilike(f"%{search}%"))

    return q.order_by(Monster.name).offset(offset).limit(limit).all()


@router.get("/monsters/{monster_id}", response_model=MonsterDetail)
def get_monster(monster_id: int, db: Session = Depends(get_db)):
    monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")

    attacks = db.query(Attack).filter(Attack.monster_id == monster_id).all()
    ac = db.query(ArmorClassComponent).filter(ArmorClassComponent.monster_id == monster_id).first()

    result = MonsterDetail(
        id=monster.id,
        name=monster.name,
        size=monster.size,
        type=monster.type,
        descriptor=monster.descriptor,
        hd_count=monster.hd_count,
        hit_dice=monster.hit_dice,
        initiative=monster.initiative,
        speed=monster.speed,
        armor_class=monster.armor_class,
        ac_total=monster.ac_total,
        ac_touch=monster.ac_touch,
        ac_flat_footed=monster.ac_flat_footed,
        base_attack=monster.base_attack,
        grapple=monster.grapple,
        attack=monster.attack,
        full_attack=monster.full_attack,
        space=monster.space,
        reach=monster.reach,
        special_attacks=monster.special_attacks,
        special_qualities=monster.special_qualities,
        skills=monster.skills,
        feats=monster.feats,
        bonus_feats=monster.bonus_feats,
        fort_save_type=monster.fort_save_type,
        ref_save_type=monster.ref_save_type,
        will_save_type=monster.will_save_type,
        strength=monster.str,
        dex=monster.dex,
        con=monster.con,
        intelligence=monster.int,
        wis=monster.wis,
        cha=monster.cha,
        environment=monster.environment,
        organization=monster.organization,
        challenge_rating=monster.challenge_rating,
        treasure=monster.treasure,
        alignment=monster.alignment,
        advancement=monster.advancement,
        special_abilities=monster.special_abilities,
        level_adjustment=monster.level_adjustment,
        **_advancement_fields(monster),
        attacks=[AttackSchema(
            id=a.id, att_name=a.att_name, att_count=a.att_count,
            is_standard=a.is_standard, weapon_nature=a.weapon_nature,
            att_mode=a.att_mode, use_category=a.use_category,
            dmg_die=a.dmg_die, crit_range=a.crit_range, crit_mult=a.crit_mult,
            str_mult=a.str_mult, group_id=a.group_id, reach=a.reach,
        ) for a in attacks],
        ac_components=ACComponentSchema(
            base_nat_armor=ac.base_nat_armor if ac else 0,
            base_armor=ac.base_armor if ac else 0,
            base_armor_description=ac.base_armor_description if ac else None,
            base_deflection=ac.base_deflection if ac else 0,
            base_deflection_description=ac.base_deflection_description if ac else None,
            base_shield=ac.base_shield if ac else 0,
            base_shield_description=ac.base_shield_description if ac else None,
            base_dodge=ac.base_dodge if ac else 0,
            base_dodge_description=ac.base_dodge_description if ac else None,
        ).model_dump() if ac else None,
    )
    return result


@router.post("/monsters/advance", response_model=StatBlockResponse)
def advance_monster(req: AdvancementRequest, db: Session = Depends(get_db)):
    """Advance a monster with HD, size changes, feats, and/or class levels."""
    monster = db.query(Monster).filter(Monster.id == req.monster_id).first()
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")

    ac_comp = db.query(ArmorClassComponent).filter(
        ArmorClassComponent.monster_id == req.monster_id
    ).first()

    attacks_db = db.query(Attack).filter(Attack.monster_id == req.monster_id).all()

    # Get type rules
    type_rule = db.query(TypeRule).filter(TypeRule.type_name == monster.type).first()
    bab_type = type_rule.bab_progression if type_rule else "averageBAB"
    hd_type = type_rule.hd_type if type_rule else 8
    cr_mod = type_rule.cr_mod if type_rule else 3
    type_skill_points = type_rule.skill_point_base if type_rule else 2

    # Determine new HD. We no longer store Excel-parsed advancement bounds
    # (max_adv_base_size / max_adv_next_size); the only floor is the
    # creature's own base HD. Size is bumped one step when HD doubles
    # past the base — a simple, type-agnostic heuristic until Phase B
    # parses the `advancement` text properly.
    new_hd = req.new_hd if req.new_hd is not None else monster.hd_count
    if new_hd < monster.hd_count:
        raise HTTPException(
            status_code=400,
            detail=f"HD cannot be reduced below base ({monster.hd_count})",
        )

    if new_hd >= monster.hd_count * 2 and monster.size in SIZE_ORDER:
        size_idx = SIZE_ORDER.index(monster.size)
        new_size = SIZE_ORDER[size_idx + 1] if size_idx < len(SIZE_ORDER) - 1 else monster.size
    else:
        new_size = monster.size

    # Calculate size transition stat bonuses
    size_delta = get_size_transition(monster.size, new_size) if new_size != monster.size else {
        "str": 0, "dex": 0, "con": 0, "nat_ac": 0, "ac": 0, "atk": 0
    }

    # Aggregate feats (racial + bonus + just-acquired) to count special
    # feats whose effect is by-occurrence (Toughness, Improved Natural Armor).
    all_feats = combined_feats(monster)
    if req.acquired_feats:
        all_feats = f"{all_feats}, {req.acquired_feats}" if all_feats else req.acquired_feats

    toughness_count = all_feats.lower().count("toughness")
    imp_nat_armor = all_feats.lower().count("improved natural armor")
    has_desecrate = "desecrating aura" in (monster.special_attacks or "").lower()

    # Ability increases
    inc = req.ability_increases or {}

    # Resolve class levels
    class_level_objs = []
    for cl_req in req.class_levels:
        prog = db.query(ClassProgression).filter(
            ClassProgression.class_name == cl_req.class_name,
            ClassProgression.level == cl_req.level,
        ).first()
        if not prog:
            raise HTTPException(status_code=400, detail=f"Invalid class: {cl_req.class_name} level {cl_req.level}")
        class_level_objs.append(ClassLevel(
            class_name=cl_req.class_name,
            level=cl_req.level,
            hd_type=prog.hd_type,
            bab=prog.bab,
            fort_save=prog.fort_save,
            ref_save=prog.ref_save,
            will_save=prog.will_save,
            skill_points_per_level=prog.skill_points_per_level,
            features=prog.features or "",
        ))

    # Handle equipped armor
    armor_bonus = ac_comp.base_armor if ac_comp else 0
    shield_bonus = ac_comp.base_shield if ac_comp else 0
    armor_max_dex = None
    if req.equipped_armor:
        armor_item = db.query(Armor).filter(Armor.name == req.equipped_armor).first()
        if armor_item:
            armor_bonus = armor_item.ac_bonus
            armor_max_dex = armor_item.max_dex
    if req.equipped_shield:
        shield_item = db.query(Armor).filter(Armor.name == req.equipped_shield).first()
        if shield_item:
            shield_bonus = shield_item.ac_bonus
            # Shield max_dex stacks: use the lower cap if both armor and shield have one
            if shield_item.max_dex is not None:
                if armor_max_dex is not None:
                    armor_max_dex = min(armor_max_dex, shield_item.max_dex)
                else:
                    armor_max_dex = shield_item.max_dex

    # Build AdvancedMonster
    adv = AdvancedMonster(
        name=monster.name,
        original_size=monster.size,
        current_size=new_size,
        type=monster.type,
        descriptor=monster.descriptor or "",
        base_hd=monster.hd_count,
        current_hd=new_hd,
        hd_type=hd_type,
        base_str=monster.str or 10,
        base_dex=monster.dex or 10,
        base_con=monster.con or 10,
        base_int=monster.int or 2,
        base_wis=monster.wis or 10,
        base_cha=monster.cha or 10,
        str_inc=inc.get("str", 0),
        dex_inc=inc.get("dex", 0),
        con_inc=inc.get("con", 0),
        int_inc=inc.get("int", 0),
        wis_inc=inc.get("wis", 0),
        cha_inc=inc.get("cha", 0),
        size_str=size_delta["str"],
        size_dex=size_delta["dex"],
        size_con=size_delta["con"],
        size_nat_ac=size_delta["nat_ac"],
        base_nat_armor=ac_comp.base_nat_armor if ac_comp else 0,
        base_armor=armor_bonus,
        base_shield=shield_bonus,
        base_deflection=ac_comp.base_deflection if ac_comp else 0,
        base_dodge=ac_comp.base_dodge if ac_comp else 0,
        armor_max_dex=armor_max_dex,
        is_masterwork_armor=req.is_masterwork_armor,
        bab_type=bab_type,
        fort_type=monster.fort_save_type or "poorSave",
        ref_type=monster.ref_save_type or "poorSave",
        will_type=monster.will_save_type or "goodSave",
        base_feats=combined_feats(monster),
        acquired_feats=req.acquired_feats or "",
        bonus_feat_count=bonus_feat_count(monster),
        class_levels=class_level_objs,
        speed=monster.speed or "",
        space=monster.space or "5",
        reach=monster.reach or "5",
        special_attacks=monster.special_attacks or "",
        special_qualities=monster.special_qualities or "",
        skills_text=monster.skills or "",
        skill_increases=req.skill_increases or {},
        type_skill_points=type_skill_points,
        environment=monster.environment or "",
        organization=monster.organization or "",
        treasure=monster.treasure or "",
        alignment=monster.alignment or "",
        advancement=monster.advancement or "",
        base_cr=monster.challenge_rating or 1,
        cr_mod=cr_mod,
        level_adjustment=monster.level_adjustment or "-",
        toughness_count=toughness_count,
        has_desecrating_aura=has_desecrate,
        improved_nat_armor_count=imp_nat_armor,
        attacks=[AttackData(
            name=a.att_name, count=a.att_count or 1,
            is_standard=bool(a.is_standard),
            weapon_nature=a.weapon_nature or "natural",
            att_mode=a.att_mode or "melee",
            use_category=a.use_category or "natural_Primary",
            dmg_die=a.dmg_die or "1d6",
            crit_range=a.crit_range or "20",
            crit_mult=a.crit_mult or 2,
            str_mult=a.str_mult or 1.0,
            att_roll_enh=a.att_roll_enh or 0,
            dmg_enh=a.dmg_enh or 0,
            group_id=a.group_id or 1,
        ) for a in attacks_db],
    )

    return generate_stat_block(adv)


# --- Equipment and Class endpoints ---

@router.get("/weapons", response_model=list[WeaponSchema])
def list_weapons(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Weapon)
    if category:
        q = q.filter(Weapon.category == category)
    return q.order_by(Weapon.category, Weapon.subcategory, Weapon.name).all()


@router.get("/armor", response_model=list[ArmorSchema])
def list_armor(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Armor)
    if category:
        q = q.filter(Armor.category == category)
    return q.order_by(Armor.category, Armor.name).all()


@router.get("/classes", response_model=list[ClassSchema])
def list_classes(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ClassDef)
    if category:
        q = q.filter(ClassDef.category == category)
    return q.order_by(ClassDef.category, ClassDef.name).all()


@router.get("/classes/{class_name}/progression", response_model=list[ClassProgressionSchema])
def get_class_progression(class_name: str, db: Session = Depends(get_db)):
    progs = db.query(ClassProgression).filter(
        ClassProgression.class_name == class_name
    ).order_by(ClassProgression.level).all()
    if not progs:
        raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found")
    return progs


@router.get("/feats", response_model=list[str])
def list_feats(db: Session = Depends(get_db)):
    feats = db.query(Feat).order_by(Feat.name).all()
    return [f.name for f in feats]


@router.get("/types")
def list_types(db: Session = Depends(get_db)):
    types = db.query(TypeRule).order_by(TypeRule.type_name).all()
    return [{"name": t.type_name, "hd": t.hd_type, "bab": t.bab_progression,
             "skill_points": t.skill_point_base} for t in types]


@router.get("/sizes")
def list_sizes():
    return SIZE_ORDER
