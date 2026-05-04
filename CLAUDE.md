# Monster Advancer — Project Guide for Claude

A web port of a D&D 3.5 Monster Advancer Excel tool. Implements the SRD 3.5 "Improving Monsters" rules: HD advancement, class levels, templates, size changes, CR recalculation.

## Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, SQLite. Entry: [backend/app/main.py](backend/app/main.py).
- **Frontend:** single-file vanilla JS in [frontend/index.html](frontend/index.html). React was abandoned 2026-05-02.
- **Run:** `start.bat` from project root (checks venv + deps, launches uvicorn on :8000).

## Architecture (post-refactor, layered)
Read [docs/calculator-pipeline.md](docs/calculator-pipeline.md) first — it is the authoritative end-to-end walkthrough.

| Layer | Path | Purity |
|---|---|---|
| FastAPI routes (only DB access) | [backend/app/routers/monsters.py](backend/app/routers/monsters.py) | impure |
| ORM models | [backend/app/models.py](backend/app/models.py) | — |
| Pydantic schemas | [backend/app/schemas.py](backend/app/schemas.py) | — |
| Orchestrator | [backend/app/services/advancement.py](backend/app/services/advancement.py) | pure |
| Legacy import shim | [backend/app/services/calculator.py](backend/app/services/calculator.py) | pure |
| Domain dataclasses (`AdvancedMonster`, `AttackData`, `ClassLevel`) | [backend/app/domain/monster.py](backend/app/domain/monster.py) | pure |
| SRD rule modules (one topic per file) | [backend/app/rules/](backend/app/rules/) | pure |

Rule modules: [abilities.py](backend/app/rules/abilities.py), [advancement.py](backend/app/rules/advancement.py), [attacks.py](backend/app/rules/attacks.py), [bab.py](backend/app/rules/bab.py), [challenge_rating.py](backend/app/rules/challenge_rating.py), [class_levels.py](backend/app/rules/class_levels.py), [feats.py](backend/app/rules/feats.py), [hit_dice.py](backend/app/rules/hit_dice.py), [saves.py](backend/app/rules/saves.py), [sizes.py](backend/app/rules/sizes.py), [skills.py](backend/app/rules/skills.py), [templates.py](backend/app/rules/templates.py).

## Database
- `backend/data/monsters.db` is **build artifact, gitignored**. Source of truth: [backend/data/seed.sql](backend/data/seed.sql) (committed).
- Rebuild: `venv\Scripts\python backend\data\build_db.py`.
- Migrations: [migrate_phase_a.py](backend/data/migrate_phase_a.py), [migrate_phase_b.py](backend/data/migrate_phase_b.py) (idempotent).
- Seed scripts: [seed_classes.py](backend/data/seed_classes.py), [seed_equipment.py](backend/data/seed_equipment.py).
- Tables: `monsters`, `attacks`, `armor_class_components`, `type_rules`, `class_progression`, `weapons`, `armor`, `feats`.
- Phase-B columns on `monsters`: `advancement_type`, `adv_max_hd`, `adv_size_thresholds` (JSON).

## SRD Reference Sources (trusted)
- **SRD rules transcribed:** [docs/improving-monsters.md](docs/improving-monsters.md) — formulas, tables, CR rules. Cite this when implementing rules.
- **SRD XML dump (OGL v1.3):** [srd35-db-v1.3/](srd35-db-v1.3/) — `monster.xml` (562 monsters, 1179 attacks), `feat.xml`, `class.xml`, `class_table.xml`, `equipment.xml`, `item.xml`, `skill.xml`, `spell.xml`, `power.xml`, `domain.xml`. Original seed source.
- **Online SRD:** https://www.d20srd.org/srd/improvingMonsters.htm

## Critical Rule Invariants (don't get these wrong)
- **1-HD replacement:** creatures with ≤1 racial HD taking class levels REPLACE racial HD; ≥2 HD ADD class levels on top. See [rules/hit_dice.py](backend/app/rules/hit_dice.py) `replaces_monster_hd`.
- **Feats = 1 + total_HD ÷ 3.** Fighter levels add `1 + level/2` bonus feats. Int "—" → 0 feats.
- **Saves:** good = `2 + HD/2`, poor = `HD/3`. Saves stored as TYPE strings (`"goodSave"`/`"poorSave"`), not values.
- **BAB:** good = HD, avg = HD×3/4, poor = HD/2 — by creature type, not class, unless class levels added.
- **CR:** `floor(hd_added / cr_mod)` where `cr_mod` lives on `type_rules` (2 Dragon/Outsider, 3 Animal/MagicalBeast/MonstrousHumanoid, 4 default). Add class-level CR (associated +1, nonassociated +½ until count=base_HD then +1). NPC classes always nonassociated.
- **Ability bumps:** count 4th/8th/12th/16th/20th HD crossings *past base HD* — not ECL.
- **Construct/Undead Con = None.** Int "—" creatures get no skill points and no feats.

## Implemented Classes (9)
- NPC: Warrior, Aristocrat, Expert, Commoner, Adept
- Base: Fighter, Rogue, Barbarian, Ranger
- 57 weapons + 18 armor/shields seeded from SRD.

## Phase Status
- Phase 1 (Data + Backend): COMPLETE
- Phase 2 (React frontend): abandoned — server-rendered HTML in use
- Phase 3 (NPC class levels): backend ready, UI partial
- Phase 4 (Martial base classes): backend seeded, UI partial
- Open TODOs in [TODO.txt](TODO.txt): UI fixes, Level Advancement block bug, Fantasy Grounds XML export.

## Working Conventions
- All SRD math is **pure** — `rules/` and `domain/` never touch the DB. Only [routers/monsters.py](backend/app/routers/monsters.py) queries.
- `AdvancedMonster` is immutable user intent — built once in the router, properties delegate to rule modules.
- Frontend does no SRD math — every number comes from `/monsters/advance`.
- When fixing a calculation bug, write/update unit tests against the rule module, not via the router.
- Cite the SRD section in commit messages when porting a rule.

## Commands
- Start server: `start.bat` (Windows) — checks deps, runs `uvicorn app.main:app --reload --port 8000` from `backend/`.
- API docs: http://localhost:8000/docs
- Frontend: open [frontend/index.html](frontend/index.html) in browser.
- Rebuild DB: `venv\Scripts\python backend\data\build_db.py`.
