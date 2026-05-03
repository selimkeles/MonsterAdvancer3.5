"""
Backwards-compatibility façade.

The original `calculator.py` was a single 900-line module containing the
SRD math, dataclasses, and stat-block formatting. The codebase has since
been split into:

    app/rules/         — pure SRD rule functions (BAB, saves, sizes, …)
    app/domain/        — `AdvancedMonster`, `AttackData`, `ClassLevel`
    app/services/advancement.py — orchestrator + stat-block formatting

This module re-exports the symbols the rest of the app (notably
`app.routers.monsters`) imports, so external callers keep working
unchanged. Prefer the underlying modules for new code.
"""
from ..domain.monster import AdvancedMonster, AttackData, ClassLevel
from ..rules.abilities import ability_mod
from ..rules.bab import calc_bab
from ..rules.saves import calc_save
from ..rules.skills import apply_skill_increases, parse_skills
from ..rules.attacks import double_crit_range, has_feat_for_attack
from ..rules.sizes import (
    DAMAGE_SCALE_DOWN,
    DAMAGE_SCALE_UP,
    SIZE_AC_MOD,
    SIZE_GRAPPLE_MOD,
    SIZE_ORDER,
    SIZE_REACH_LONG,
    SIZE_REACH_TALL,
    SIZE_SPACE,
    SIZE_TRANSITIONS,
    get_size_transition,
    scale_damage,
)
from .advancement import (
    _build_attack_text,
    calc_attack_roll,
    calc_damage_bonus,
    format_attack_text,
    generate_stat_block,
)

__all__ = [
    # Dataclasses
    "AdvancedMonster", "AttackData", "ClassLevel",
    # Size tables
    "SIZE_ORDER", "SIZE_AC_MOD", "SIZE_GRAPPLE_MOD",
    "SIZE_SPACE", "SIZE_REACH_TALL", "SIZE_REACH_LONG",
    "SIZE_TRANSITIONS", "DAMAGE_SCALE_UP", "DAMAGE_SCALE_DOWN",
    # Pure rule functions
    "ability_mod", "calc_bab", "calc_save",
    "get_size_transition", "scale_damage",
    "parse_skills", "apply_skill_increases",
    "double_crit_range", "has_feat_for_attack",
    # Stat-block orchestration
    "calc_attack_roll", "calc_damage_bonus",
    "format_attack_text", "_build_attack_text",
    "generate_stat_block",
]
