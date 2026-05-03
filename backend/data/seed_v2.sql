-- seed_v2.sql — atomic monster schema (Phase C).
--
-- Applied AFTER seed.sql by build_db.py. Adds new tables alongside the
-- legacy `monsters` / `attacks` / `armor_class_components` tables; the
-- legacy tables remain populated and are still read by the running app.
--
-- Two-file layout:
--   base.db  — gets these tables PLUS `monster_presets` (read-only catalog).
--   prod.db  — gets these tables PLUS `monsters` (mutable user data).
--
-- The DDL below uses a placeholder identifier "{ROOT}" that build_db.py
-- substitutes for either "monster_presets" (base.db) or "monsters" (prod.db).
-- Catalog tables (weapons, armor, feats, ...) come from seed.sql; this file
-- only adds the monster-instance tables and one ALTER on `feats`.

BEGIN TRANSACTION;

-- Catalog change: parameter discriminator on feats.
-- Backfilled by migrate_to_v2.py based on observed parenthetical usage.
--   NULL     → no parameter (e.g. Power Attack)
--   weapon   → Weapon Focus, Weapon Specialization, Improved Critical, Greater Weapon Focus, Improved Sunder
--   school   → Spell Focus, Greater Spell Focus
--   skill    → Skill Focus
--   ability  → Ability Focus
--   exotic   → Exotic Weapon Proficiency
ALTER TABLE feats ADD COLUMN parameter_options TEXT;

-- ── {ROOT}: monster instance / preset row ──────────────────────────────────
CREATE TABLE {ROOT} (
    id INTEGER PRIMARY KEY,
    preset_id INTEGER,                          -- if duplicated from a preset (NULL on the preset itself)
    needs_review INTEGER NOT NULL DEFAULT 0,    -- quarantine flag
    review_notes TEXT,                          -- comma-joined reasons

    -- identity
    name TEXT NOT NULL,
    altname TEXT,
    description TEXT,
    picture_path TEXT,
    token_path TEXT,
    token3d_path TEXT,
    reference TEXT,

    -- type line
    size TEXT NOT NULL,
    type TEXT NOT NULL,
    subtypes TEXT,
    alignment TEXT,

    -- ability scores (NULL allowed: class-leveled NPCs, mindless creatures, etc.)
    str INTEGER, dex INTEGER, con INTEGER,
    int INTEGER, wis INTEGER, cha INTEGER,

    -- racial HD only (class HD lives in {ROOT}_classes)
    racial_hd_count INTEGER NOT NULL DEFAULT 0,
    racial_hd_die INTEGER,
    hp INTEGER,

    -- speed components (feet)
    speed_land INTEGER DEFAULT 30,
    speed_fly INTEGER, fly_maneuverability TEXT,
    speed_swim INTEGER,
    speed_climb INTEGER,
    speed_burrow INTEGER,

    -- AC pieces (worn armor/shield resolved via {ROOT}_equipment.slot='armor'/'shield')
    natural_armor INTEGER DEFAULT 0,
    deflection_bonus INTEGER DEFAULT 0, deflection_desc TEXT,
    dodge_bonus INTEGER DEFAULT 0,      dodge_desc TEXT,
    ac_total INTEGER, ac_touch INTEGER, ac_flat INTEGER,

    -- combat geometry
    space TEXT, reach TEXT,
    initiative INTEGER,
    bab INTEGER, grapple INTEGER,

    -- saves
    fort_save INTEGER, ref_save INTEGER, will_save INTEGER,
    fort_save_type TEXT, ref_save_type TEXT, will_save_type TEXT,

    -- denormalized cache (composed from {ROOT}_special_traits)
    special_attacks TEXT,
    special_qualities TEXT,

    -- meta
    challenge_rating REAL,
    level_adjustment TEXT,
    environment TEXT,
    organization TEXT,
    treasure TEXT,
    advancement TEXT,
    advancement_type TEXT,
    adv_max_hd INTEGER,
    adv_size_thresholds TEXT,

    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX idx_{ROOT}_name ON {ROOT}(name);
CREATE INDEX idx_{ROOT}_type ON {ROOT}(type);
CREATE INDEX idx_{ROOT}_review ON {ROOT}(needs_review);

-- ── {ROOT}_classes ──────────────────────────────────────────────────────────
CREATE TABLE {ROOT}_classes (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    class_name TEXT,                            -- canonical name → FK classes(name); NULL if unrecognised
    class_name_raw TEXT,                        -- raw name as parsed from monster name
    levels INTEGER NOT NULL,
    order_index INTEGER,
    associated INTEGER NOT NULL DEFAULT 0       -- CR association flag (0=nonassociated, 1=associated)
);
CREATE INDEX idx_{ROOT}_classes_monster ON {ROOT}_classes(monster_id);

-- ── {ROOT}_equipment ────────────────────────────────────────────────────────
CREATE TABLE {ROOT}_equipment (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    slot TEXT NOT NULL,                         -- main_hand|off_hand|armor|shield|barding|ring|cloak|arrows|other
    weapon_id INTEGER REFERENCES weapons(id),
    armor_id INTEGER REFERENCES armor(id),
    enhancement_bonus INTEGER NOT NULL DEFAULT 0,
    special_properties TEXT,                    -- "frost, cold iron" / "dancing"
    composite_str_rating INTEGER,
    custom_name TEXT,                           -- when no catalog match
    notes TEXT
);
CREATE INDEX idx_{ROOT}_equipment_monster ON {ROOT}_equipment(monster_id);

-- ── {ROOT}_attacks ──────────────────────────────────────────────────────────
CREATE TABLE {ROOT}_attacks (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    routine TEXT NOT NULL,                      -- standard|full
    group_index INTEGER NOT NULL,               -- "or"-alternate routines share routine but differ here
    order_in_group INTEGER NOT NULL,
    source TEXT NOT NULL,                       -- natural|weapon
    weapon_link_id INTEGER REFERENCES {ROOT}_equipment(id),
    natural_name TEXT,                          -- "Claw" / "Bite" / "Slam" / "Tail slap" / "Tentacle"
    count INTEGER NOT NULL DEFAULT 1,
    is_primary INTEGER NOT NULL DEFAULT 1,
    attack_kind TEXT,                           -- melee|ranged|melee touch|ranged touch
    bonus_total INTEGER,
    iteratives TEXT,                            -- "+25/+20/+15/+10" override (for high BAB)
    damage_dice TEXT,                           -- "2d6"
    damage_bonus INTEGER,                       -- "+9"
    critical TEXT,                              -- "19-20" / "x3" / "19-20/x3"
    extra_effects TEXT                          -- "plus 1d8 fire" / "plus poison"
);
CREATE INDEX idx_{ROOT}_attacks_monster ON {ROOT}_attacks(monster_id);

-- ── {ROOT}_feats ────────────────────────────────────────────────────────────
CREATE TABLE {ROOT}_feats (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    feat_id INTEGER REFERENCES feats(id),
    feat_name_raw TEXT,                         -- raw text used when feat_id is NULL (catalog miss)
    is_bonus INTEGER NOT NULL DEFAULT 0,        -- renders "(B)"
    parameter TEXT,                             -- "bite" / "illusion" / "Tumble"
    order_index INTEGER
);
CREATE INDEX idx_{ROOT}_feats_monster ON {ROOT}_feats(monster_id);

-- ── {ROOT}_skill_ranks ──────────────────────────────────────────────────────
CREATE TABLE {ROOT}_skill_ranks (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,                   -- "Hide" / "Knowledge (arcana)" inline
    ranks INTEGER NOT NULL DEFAULT 0,
    misc_modifier INTEGER NOT NULL DEFAULT 0,
    total_bonus INTEGER,
    conditional_text TEXT                       -- "*" / "(+9 following tracks)"
);
CREATE INDEX idx_{ROOT}_skills_monster ON {ROOT}_skill_ranks(monster_id);

-- ── {ROOT}_special_traits ───────────────────────────────────────────────────
CREATE TABLE {ROOT}_special_traits (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,                         -- attack|quality
    name TEXT NOT NULL,
    short_label TEXT,
    ability_type TEXT,                          -- Ex|Su|Sp
    description TEXT,
    order_index INTEGER
);
CREATE INDEX idx_{ROOT}_traits_monster ON {ROOT}_special_traits(monster_id);

-- ── {ROOT}_spell_likes ──────────────────────────────────────────────────────
CREATE TABLE {ROOT}_spell_likes (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    frequency TEXT NOT NULL,                    -- "At will" / "3/day" / "1/day"
    spell_name TEXT NOT NULL,
    caster_level INTEGER,
    save_dc INTEGER,
    save_ability TEXT,                          -- Cha|Wis|Int
    notes TEXT,
    order_index INTEGER
);
CREATE INDEX idx_{ROOT}_spell_likes_monster ON {ROOT}_spell_likes(monster_id);

-- ── {ROOT}_spells ───────────────────────────────────────────────────────────
CREATE TABLE {ROOT}_spells (
    id INTEGER PRIMARY KEY,
    monster_id INTEGER NOT NULL REFERENCES {ROOT}(id) ON DELETE CASCADE,
    class_id INTEGER REFERENCES classes(id),
    spell_level INTEGER NOT NULL,
    spell_name TEXT NOT NULL,
    prepared INTEGER NOT NULL DEFAULT 1,
    is_domain INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);
CREATE INDEX idx_{ROOT}_spells_monster ON {ROOT}_spells(monster_id);

COMMIT;
