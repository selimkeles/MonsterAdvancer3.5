# How the Calculator Works

> **Audience.** Read this if you've never seen the project before and want to
> understand exactly what happens when a user advances a monster — from the
> click in the browser, through the API, into the rule modules, and back into
> the rendered stat block. No prior knowledge is assumed.

---

## 1. The big picture

The Monster Advancer is a port of an Excel `.xlsm` tool that helped a Dungeon
Master apply the **D&D 3.5 SRD "Improving Monsters"** rules. The web version
keeps the data and the math, throws away the spreadsheet, and exposes
everything as a small REST API consumed by a single static HTML page.

```
┌────────────┐   HTTP    ┌─────────────┐   SQL    ┌────────────┐
│ frontend   │ ────────▶ │ FastAPI     │ ───────▶ │ SQLite DB  │
│ index.html │ ◀──────── │  routers    │ ◀─────── │ monsters.db│
└────────────┘   JSON    └──────┬──────┘  rows    └────────────┘
                                │
                                ▼
                       ┌───────────────────┐
                       │ services /        │
                       │   advancement.py  │  ← orchestrator
                       └────────┬──────────┘
                                │
                                ▼
                       ┌───────────────────┐
                       │ domain /          │
                       │   AdvancedMonster │  ← state object
                       └────────┬──────────┘
                                │
                                ▼
                       ┌───────────────────┐
                       │ rules /  bab,     │
                       │  saves, sizes,    │  ← pure SRD math,
                       │  feats, skills,   │    one module per topic
                       │  challenge_rating │
                       └───────────────────┘
```

There are three folders to keep separate in your head:

| Folder | What lives there | Pure / impure |
|---|---|---|
| `backend/app/rules/` | One file per SRD topic. Just functions and tables. | Pure (no DB, no I/O). |
| `backend/app/domain/` | `AdvancedMonster` — a dataclass that gathers all user choices and exposes computed stats as `@property` methods that delegate to `rules/`. | Pure. |
| `backend/app/services/advancement.py` | The orchestrator. Takes an `AdvancedMonster`, applies feat/size effects to its attacks, formats text (attack lines, AC breakdown), and returns a dict for the API. | Pure (acts on the dataclass). |

Plus:

* `backend/app/routers/monsters.py` — FastAPI handlers. **Only file that touches the DB.**
* `backend/app/models.py` — SQLAlchemy ORM declarations.
* `backend/app/schemas.py` — Pydantic request / response shapes.

---

## 2. The database

### 2.1 How `monsters.db` is created

`monsters.db` is **not committed** — it's a build artifact that the user
generates locally. The committed source of truth is `backend/data/seed.sql`,
a portable SQLite text dump.

```
backend/data/seed.sql           ← committed; ~20k lines of SQL
backend/data/build_db.py        ← `python build_db.py` regenerates monsters.db
backend/data/migrate_phase_b.py ← idempotent schema migration + data fixes
```

Running `build_db.py`:

1. Deletes the old `monsters.db` (if any).
2. `con.executescript(open("seed.sql").read())` — runs the full SQL dump.
3. Returns. The DB is now ready.

### 2.2 What seed data came from

The `seed.sql` was originally produced from `srd35-db-v1.3/monster.xml` (a
public OGL dump of every SRD 3.5 monster — 562 creatures, 1179 attacks).
Equipment, feats, and class-progression tables were seeded from the SRD
PDFs by hand-extracted SQL.

### 2.3 The monster table — what's stored vs. what's parsed

Each row in `monsters` mixes three kinds of data:

| Kind | Examples | Source |
|---|---|---|
| **Raw stat-block text** | `armor_class`, `hit_dice`, `attack`, `full_attack`, `saves`, `abilities` | Verbatim from the SRD XML. The strings are reference / display only — the calculator does not parse them. |
| **Atomic numbers** | `hd_count`, `challenge_rating`, `str/dex/con/int/wis/cha`, `base_attack`, `ac_total/touch/flat_footed` | Either present in the XML directly (ability scores) or parsed once at seed time (`ac_total` from the AC text). |
| **Type flags / progressions** | `fort_save_type`, `ref_save_type`, `will_save_type` (`"goodSave"` / `"poorSave"`) | Per-row because the SRD type table marks Humanoid as "Varies". |

The database also has child tables:

| Table | One row per | Purpose |
|---|---|---|
| `attacks` | (monster, weapon) | Individual attacks with damage die, crit range, attack mode, group ID. The `attack` / `full_attack` text columns on the monster are *display* — `attacks` is what the calculator iterates. |
| `armor_class_components` | monster | Atomic AC pieces: `base_nat_armor`, `base_armor`, `base_shield`, `base_deflection`, `base_dodge`. |
| `type_rules` | creature type | `hd_type` (the die: d8/d10/d12), `bab_progression` (good/avg/poor), `skill_point_base`, `cr_mod` (the per-type CR divisor: 4 for Aberration, 3 for Animal, 2 for Dragon …). |
| `class_progression` | (class_name, level) | Per-level BAB, save bonuses, skill points, and feature text for each class (Fighter 1–20, Rogue 1–20, etc.). |
| `weapons`, `armor` | item | Equipment catalog used when the user equips a weapon/armor during advancement. |
| `feats` | feat | Just a name list — used for the autocomplete in the "Acquired Feats" UI input. |

### 2.4 Phase-B normalised columns

Three columns on `monsters` were added by `migrate_phase_b.py` to make the
messy `advancement` text queryable:

| Column | Values |
|---|---|
| `advancement_type` | `'hd'` / `'hd_or_class'` / `'class'` / `'special'` / `'none'` |
| `adv_max_hd` | INT cap, NULL when open-ended (e.g. `"38+ HD (Gargantuan)"`) or non-advancing |
| `adv_size_thresholds` | JSON string: `[[min_hd, "Size"], ...]` |

These power the HD stepper in the UI without any runtime parsing.

---

## 3. What happens when the user clicks "advance"

Two endpoints matter:

* **`GET /monsters/{id}`** — fetches the base creature for display.
* **`POST /monsters/advance`** — recomputes the full stat block given the user's choices.

### 3.1 Loading the base monster

When the user picks a creature from the list, the frontend calls
`GET /monsters/{id}` and stores the response as `state.selectedMonster`
(a `MonsterDetail` object — see `schemas.py`). This is the *un-advanced*
creature. The HD stepper, ability inputs, etc. are seeded from this data.

The handler in `routers/monsters.py:get_monster` joins:

* `monsters` row → all the columns described in §2.3
* `attacks` rows → `attacks: [AttackSchema]`
* `armor_class_components` row → `ac_components` dict
* `parse_advancement(monster)` → `can_advance_hd`, `advances_by_class`, `adv_max_hd`, `adv_size_thresholds` (read straight from the DB columns; no recomputation)

### 3.2 The user changes something in the UI

Every input in `frontend/index.html` writes into a single in-memory object:

```javascript
state.advState = {
  newHD:          null | int,       // null means "no HD change"
  abilityInc:     { str:0, dex:0, ... },
  skillInc:       { "Climb":2, ... },
  acquiredFeats:  "Toughness, Improved Initiative",
  equippedArmor:  "chain shirt" | null,
  equippedShield: "heavy steel shield" | null,
  isMWArmor:      bool,
  // …plus class levels, etc.
};
```

After every change, `doAdvance()` runs (see line ~1779 in `index.html`):

1. If nothing has been changed (everything is null/zero) — clear
   `state.advancedResult` and re-render the **base** stat block.
2. Otherwise build a JSON body and `POST /monsters/advance`.
3. Store the response as `state.advancedResult` and re-render.

The frontend never does any calculation itself. The only frontend "math"
is the HD stepper bounds (`maxHDFor(monster)` falls back to a soft cap when
`adv_max_hd` is NULL because the creature is open-ended). All numbers in
the rendered stat block come from the API response.

### 3.3 The advance handler — `routers/monsters.py:advance_monster`

This handler is the **only** place the DB is queried during advancement.
Once it has the rows, it builds a pure `AdvancedMonster` dataclass and
hands off to the rule layer.

```python
def advance_monster(req: AdvancementRequest, db: Session):
    # 1. Fetch the base monster, its attacks, and AC components
    monster   = db.query(Monster).filter(Monster.id == req.monster_id).first()
    ac_comp   = db.query(ArmorClassComponent).filter(...).first()
    attacks_db = db.query(Attack).filter(...).all()

    # 2. Look up type rules (BAB progression, HD die, CR divisor, …)
    type_rule = db.query(TypeRule).filter(TypeRule.type_name == monster.type).first()

    # 3. Resolve the HD change and figure out the new size
    new_hd  = req.new_hd or monster.hd_count
    new_size = bumped_one_step if new_hd >= base_hd * 2 else monster.size
    size_delta = get_size_transition(monster.size, new_size)

    # 4. Resolve every requested class level (DB lookup against class_progression)
    class_level_objs = [ClassLevel(...) for cl_req in req.class_levels]

    # 5. Resolve equipped armor/shield (DB lookup against the armor table)
    armor_bonus, shield_bonus, armor_max_dex = ...

    # 6. Build the AdvancedMonster
    adv = AdvancedMonster(
        name=..., type=..., base_hd=..., current_hd=new_hd,
        base_str=..., str_inc=req.ability_increases.get("str", 0),
        size_str=size_delta["str"], ...
        bab_type=type_rule.bab_progression,
        fort_type=monster.fort_save_type, ...
        attacks=[AttackData(...) for a in attacks_db],
        class_levels=class_level_objs,
        ...
    )

    # 7. Hand off to the orchestrator
    return generate_stat_block(adv)
```

Three things to internalise:

* **The handler does *no* SRD math.** It only translates DB rows + the
  request into the inputs of `AdvancedMonster`.
* **`AdvancedMonster` is immutable user intent.** Once built, it never
  hits the DB again.
* **All progression is by *type*, not by class** unless class levels were
  requested. The `bab_type` / `fort_type` / etc. fields come from the
  monster's *type* (Animal → cleric BAB, Dragon → fighter BAB) — class
  levels add their own contribution on top.

### 3.4 The rule layer — what each module computes

Once `generate_stat_block(adv)` runs, it asks the dataclass for every
derived value via `@property`. Each property delegates to a rule module:

| Property on `AdvancedMonster` | Rule module | What it computes |
|---|---|---|
| `total_str/dex/con/int/wis/cha`, `*_mod` | `rules/abilities.py` | Final ability scores (base + size delta + manual bumps), 3.5 modifier `(score - 10) // 2`. Returns `None` for Construct/Undead Con and Int-"—" creatures. |
| `total_hd` | `rules/hit_dice.py` | Monster HD + class HD. Applies the **1-HD humanoid replacement rule**: when a creature with ≤1 racial HD takes class levels, racial HD is **replaced**, not added. |
| `current_bab` | `rules/bab.py` | Fighter (good): `HD × 1`. Cleric (avg): `HD × 3 / 4`. Wizard (poor): `HD ÷ 2`. Class levels add their own BAB on top. |
| `fort_save / ref_save / will_save` | `rules/saves.py` | Good: `2 + HD/2`. Poor: `HD/3`. Plus ability mod (Con/Dex/Wis), feat bonuses (Great Fortitude, Lightning Reflexes, Iron Will), and class save bonuses. |
| `total_ac / touch_ac / flat_footed_ac` | inline in `domain/monster.py` | `10 + size + Dex (capped by armor max-Dex) + natural + armor + shield + deflection + dodge`. Touch drops armor/shield/natural; flat-footed drops Dex bonus and dodge. Tiny-or-smaller halves manufactured armor. |
| `grapple` | `rules/sizes.py` (for `SIZE_GRAPPLE_MOD`) | `BAB + Str mod + size grapple modifier`. |
| `hp_average / hp_text` | `rules/hit_dice.py` | Average roll per HD = `(die + 1) / 2`. Plus Con × HD, plus Toughness × 3, plus desecrating-aura × 2 × HD, plus a fixed Construct bonus by size. |
| `max_feats` | `rules/feats.py` | `1 + total_HD ÷ 3` for sane creatures, `0` for Int-"—". Fighter levels add `1 + level/2` bonus feats. |
| `total_skill_points`, `bonus_skill_points`, `spent_skill_points` | `rules/skills.py` | `(type_skill_rate + Int_mod) × HD`, min 1 if Int ≥ 1, 0 if Int "—". Class levels add `class_rate + Int_mod` per level. |
| `current_cr` | `rules/challenge_rating.py` | See §3.6 below. |
| `available_ability_points` | `rules/abilities.py` | Counts how many 4th/8th/12th/… HD thresholds the creature crossed *past* its base HD. The user spends these by setting the `*_inc` fields. |
| `sneak_attack_dice`, `barbarian_rage_per_day`, `damage_reduction` | `rules/class_levels.py` | Class-feature pass-throughs based on Rogue/Barbarian level totals. |

### 3.5 The orchestrator — `services/advancement.py`

After all the simple stats are computed via properties, the orchestrator
does three things the dataclass can't do alone:

**(a) Apply feat + size modifiers to attacks.** `_apply_attack_modifiers`
walks each attack and:

1. Bumps damage one die step if **Improved Natural Attack** is taken on it.
2. Bumps damage one die step if size increased (natural attacks only).
3. Doubles the crit range (e.g. 19–20 → 17–20) if **Improved Critical** is taken on it.

**(b) Format attack text.** `format_attack_text` produces strings like
`"2 claws +11 melee (1d8+7)"` from an `AttackData` object plus the
monster's BAB / Str / size mod / Weapon Focus / Multiattack penalties.
Attacks in the same `group_id` are joined with `" and "`; different
groups are joined with `" or "` (alternative routines).

**(c) Format the AC breakdown.** `total_ac (+1 size, +2 Dex, +4 natural)`
is built inline from the AC component fields.

The output is a flat dictionary matching `schemas.StatBlockResponse`.

### 3.6 Challenge Rating in detail

CR is the most complex calc, so it deserves its own breakdown.

```
final_CR = base_CR
         + cr_from_hd_advancement(hd_added, cr_mod)
         + cr_from_class_levels(associated, nonassociated, base_hd)
         + extra_cr_modifiers(size_to_large+, elite_array, special_abs)
```

* **`cr_from_hd_advancement`** — `floor(hd_added / cr_mod)`. `cr_mod` is the
  per-type divisor stored on `type_rules`: 2 for Dragon/Outsider, 3 for
  Animal/Magical Beast/Monstrous Humanoid, 4 for everyone else.
* **`cr_from_class_levels`** — Associated levels (the class plays to the
  monster's strengths) add +1 each. Nonassociated levels add +½ each
  *until* their count equals the creature's original HD; subsequent
  nonassociated levels add +1 each. NPC-class levels are *always*
  nonassociated regardless of fit.
* **`extra_cr_modifiers`** — flat adders: +1 if size pushed past Medium,
  +1 if elite array (only when not class-advanced — class-advanced
  monsters are *assumed* to use elite), +2 for significant new special
  abilities, +1 for minor.

### 3.7 The response shape

`StatBlockResponse` (see `schemas.py`) has ~50 fields. The frontend reads
them directly — the renderer is a tagged template literal that pulls out
`adv.armor_class`, `adv.hit_points`, `adv.full_attack`, etc. The
`renderSingleStatBlock(monster, adv)` function in `index.html` decides
whether to display the base monster or the advanced one based on whether
`adv` was set.

---

## 4. End-to-end example: advance a Wolf to 6 HD

Inputs:
* Wolf: base HD 2, Medium, Animal type, base_cr 1, advancement = `"3 HD (Medium); 4-6 HD (Large)"`.
* User opens the stat block, clicks the HD stepper up four times → `newHD = 6`.

Frontend posts:
```json
{ "monster_id": 535, "new_hd": 6, "ability_increases": {}, ... }
```

Router (`advance_monster`):

1. Fetches the Wolf row, its `attacks` (bite +3 melee 1d6+1), and AC components (nat 2).
2. Looks up `type_rules` for Animal: `bab=averageBAB`, `hd_type=8`, `cr_mod=3`, `skill_point_base=2`.
3. `new_hd = 6`. `6 >= 2 * 2`, so the size auto-bumps Medium → Large. `size_delta = get_size_transition("Medium","Large") = {str:+8, dex:-2, con:+4, nat_ac:+2, ac:-1, atk:-1}`.
4. Builds `AdvancedMonster(base_hd=2, current_hd=6, base_str=13, size_str=8, ...)`.

Rule layer evaluates properties:

* `total_str = 13 + 8 + 0 = 21`, `str_mod = +5`
* `total_dex = 15 - 2 = 13`, `dex_mod = +1`
* `current_bab = (6 * 3) // 4 = 4` (cleric BAB at 6 HD)
* `fort_save = 2 + 6//2 + con_mod + Great-Fortitude-bonus = 2+3+3+0 = 8`
* `current_nat_armor = 2 + 2 = 4`
* `total_ac = 10 + (-1 size) + 1 (Dex) + 4 (natural) = 14`
* `hp_average = 6 × ((8+1)/2 + 3 con) = 6 × 7.5 = 45`
* `current_cr = 1 + (6-2)//3 = 1 + 1 = 2`. With size bumped past Medium: `+1`. Final **CR 3**.
* `max_feats = 1 + 6//3 = 3`
* `total_skill_points = (2 + 1 int_mod) × 6 = 18`

Orchestrator:

* Bumps `bite 1d6` → `1d8` (size step).
* Formats: `"Bite +9 melee (1d8+7)"` (BAB 4 + Str 5 + size −1 + 1 = 9; damage +5 × 1.5 = +7).
* AC breakdown: `"14 (-1 size, +1 Dex, +4 natural), touch 10, flat-footed 13"`.

Returns the dictionary. Frontend renders it.

---

## 5. Where to look when things break

| Symptom | First place to check |
|---|---|
| HD stepper goes past the SRD cap | `frontend/index.html: maxHDFor()` and `monsters.adv_max_hd` in DB |
| Wrong AC after advancement | `domain/monster.py: total_ac / touch_ac / flat_footed_ac` |
| Wrong CR after advancement | `rules/challenge_rating.py` and `domain/monster.py: current_cr` |
| Attack damage die isn't scaling | `services/advancement.py: _apply_attack_modifiers` and `rules/sizes.py: scale_damage` |
| 1-HD humanoid + class level math is wrong | `rules/hit_dice.py: replaces_monster_hd` |
| Construct/Ooze gets feats it shouldn't | `domain/monster.py: has_intelligence` flag wiring in the router |
| Garbage in the `advancement` text column | `migrate_phase_b.py` parses it into `advancement_type` / `adv_max_hd` |

---

## 6. Quick reference — file map

```
backend/
├── data/
│   ├── seed.sql              ← committed source of truth
│   ├── build_db.py           ← rebuilds monsters.db from seed.sql
│   └── migrate_phase_b.py    ← schema migration + data fixes
└── app/
    ├── main.py               ← FastAPI app, route registration
    ├── database.py           ← SQLAlchemy session factory
    ├── models.py             ← ORM declarations
    ├── schemas.py            ← Pydantic request / response shapes
    ├── routers/
    │   └── monsters.py       ← /monsters, /monsters/{id}, /monsters/advance, /weapons, /armor, /classes, /feats, /types
    ├── domain/
    │   └── monster.py        ← AdvancedMonster, AttackData, ClassLevel
    ├── services/
    │   ├── advancement.py    ← orchestrator (generate_stat_block)
    │   └── calculator.py     ← legacy import shim — re-exports the dataclasses + generate_stat_block under their old names
    └── rules/
        ├── advancement.py    ← parse_advancement (utility)
        ├── abilities.py      ← ability_mod, hd_increase_ability_points
        ├── attacks.py        ← Improved Critical, Improved Natural Attack, Multiattack penalties
        ├── bab.py            ← good/avg/poor BAB
        ├── challenge_rating.py
        ├── class_levels.py   ← NPC class set, sneak attack, barbarian rage/DR, fighter bonus feats
        ├── feats.py          ← feat_count
        ├── hit_dice.py       ← 1-HD replacement rule, average HP, Construct bonus HP
        ├── saves.py          ← good / poor save progressions
        ├── sizes.py          ← SIZE_ORDER, transition deltas, damage scaling, AC/grapple/space/reach mods
        ├── skills.py         ← skill_points_per_hd, parse_skills, apply_skill_increases
        └── templates.py      ← stub for SRD templates (not yet implemented)

frontend/
└── index.html                ← single-file vanilla JS app; doAdvance() is the entry point

docs/
├── improving-monsters.md     ← SRD rules transcribed
└── calculator-pipeline.md    ← this file
```
