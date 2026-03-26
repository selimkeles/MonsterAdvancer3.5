"""
Seed D&D 3.5 class progression data into SQLite.
Covers 5 NPC classes + 4 martial base classes.
"""
import os
import sqlite3
import math

DB_PATH = os.path.join(os.path.dirname(__file__), "monsters.db")


def good_bab(level):
    """Full BAB progression: +1 per level"""
    return level


def average_bab(level):
    """3/4 BAB progression"""
    return int(level * 3 / 4)


def poor_bab(level):
    """1/2 BAB progression"""
    return level // 2


def good_save(level):
    """Good save progression: +2 at 1st, +1 every 2 levels"""
    return 2 + level // 2


def poor_save(level):
    """Poor save progression: +1 every 3 levels"""
    return level // 3


# Class definitions: name, category, hd, bab_func, fort_func, ref_func, will_func, skill_pts, wpn_prof, armor_prof, desc
CLASS_DEFS = [
    # NPC Classes
    {
        "name": "Warrior",
        "category": "NPC",
        "hd_type": 8,
        "bab": good_bab,
        "fort": good_save,
        "ref": poor_save,
        "will": poor_save,
        "skill_points": 2,
        "weapon_proficiency": "Simple, Martial",
        "armor_proficiency": "All armor, Shields",
        "description": "NPC warrior class. Simple combatants with no special abilities.",
    },
    {
        "name": "Aristocrat",
        "category": "NPC",
        "hd_type": 8,
        "bab": average_bab,
        "fort": poor_save,
        "ref": poor_save,
        "will": good_save,
        "skill_points": 4,
        "weapon_proficiency": "Simple, Martial",
        "armor_proficiency": "All armor, Shields",
        "description": "NPC noble/leader class. All saves poor except Will.",
    },
    {
        "name": "Expert",
        "category": "NPC",
        "hd_type": 6,
        "bab": average_bab,
        "fort": poor_save,
        "ref": poor_save,
        "will": good_save,
        "skill_points": 6,
        "weapon_proficiency": "Simple",
        "armor_proficiency": "Light armor",
        "description": "NPC skilled class. Any 10 skills as class skills.",
    },
    {
        "name": "Commoner",
        "category": "NPC",
        "hd_type": 4,
        "bab": poor_bab,
        "fort": poor_save,
        "ref": poor_save,
        "will": poor_save,
        "skill_points": 2,
        "weapon_proficiency": "One simple weapon",
        "armor_proficiency": "None",
        "description": "NPC commoner class. Weakest class, no special abilities.",
    },
    {
        "name": "Adept",
        "category": "NPC",
        "hd_type": 6,
        "bab": poor_bab,
        "fort": poor_save,
        "ref": poor_save,
        "will": good_save,
        "skill_points": 2,
        "weapon_proficiency": "Simple",
        "armor_proficiency": "None",
        "description": "NPC spellcaster class. Simplified divine spellcasting.",
    },
    # Base Classes (Martial)
    {
        "name": "Fighter",
        "category": "Base",
        "hd_type": 10,
        "bab": good_bab,
        "fort": good_save,
        "ref": poor_save,
        "will": poor_save,
        "skill_points": 2,
        "weapon_proficiency": "Simple, Martial",
        "armor_proficiency": "All armor, Shields (including tower)",
        "description": "Bonus feat at 1st level and every even level. Weapon Specialization access.",
    },
    {
        "name": "Rogue",
        "category": "Base",
        "hd_type": 6,
        "bab": average_bab,
        "fort": poor_save,
        "ref": good_save,
        "will": poor_save,
        "skill_points": 8,
        "weapon_proficiency": "Simple, hand crossbow, rapier, sap, shortbow, short sword",
        "armor_proficiency": "Light armor",
        "description": "Sneak Attack, Evasion, Uncanny Dodge, Trap Sense.",
    },
    {
        "name": "Barbarian",
        "category": "Base",
        "hd_type": 12,
        "bab": good_bab,
        "fort": good_save,
        "ref": poor_save,
        "will": poor_save,
        "skill_points": 4,
        "weapon_proficiency": "Simple, Martial",
        "armor_proficiency": "Light armor, Medium armor, Shields (except tower)",
        "description": "Rage, Fast Movement, Uncanny Dodge, Damage Reduction, Trap Sense.",
    },
    {
        "name": "Ranger",
        "category": "Base",
        "hd_type": 8,
        "bab": good_bab,
        "fort": good_save,
        "ref": good_save,
        "will": poor_save,
        "skill_points": 6,
        "weapon_proficiency": "Simple, Martial",
        "armor_proficiency": "Light armor, Shields (except tower)",
        "description": "Favored Enemy, Track, Combat Style, Animal Companion, spells from level 4.",
    },
]


# Class features by class and level
CLASS_FEATURES = {
    "Fighter": {
        1: "Bonus feat",
        2: "Bonus feat",
        4: "Bonus feat",
        6: "Bonus feat",
        8: "Bonus feat",
        10: "Bonus feat",
        12: "Bonus feat",
        14: "Bonus feat",
        16: "Bonus feat",
        18: "Bonus feat",
        20: "Bonus feat",
    },
    "Rogue": {
        1: "Sneak Attack +1d6, Trapfinding",
        2: "Evasion",
        3: "Sneak Attack +2d6, Trap Sense +1",
        4: "Uncanny Dodge",
        5: "Sneak Attack +3d6",
        6: "Trap Sense +2",
        7: "Sneak Attack +4d6",
        8: "Improved Uncanny Dodge",
        9: "Sneak Attack +5d6, Trap Sense +3",
        10: "Special ability",
        11: "Sneak Attack +6d6",
        12: "Trap Sense +4",
        13: "Sneak Attack +7d6, Special ability",
        14: "",
        15: "Sneak Attack +8d6, Trap Sense +5",
        16: "Special ability",
        17: "Sneak Attack +9d6",
        18: "Trap Sense +6",
        19: "Sneak Attack +10d6, Special ability",
        20: "",
    },
    "Barbarian": {
        1: "Fast Movement, Illiteracy, Rage 1/day",
        2: "Uncanny Dodge",
        3: "Trap Sense +1",
        4: "Rage 2/day",
        5: "Improved Uncanny Dodge",
        6: "Trap Sense +2",
        7: "Damage Reduction 1/-",
        8: "Rage 3/day",
        9: "Trap Sense +3",
        10: "Damage Reduction 2/-",
        11: "Greater Rage",
        12: "Rage 4/day, Trap Sense +4",
        13: "Damage Reduction 3/-",
        14: "Indomitable Will",
        15: "Trap Sense +5",
        16: "Damage Reduction 4/-, Rage 5/day",
        17: "Tireless Rage",
        18: "Trap Sense +6",
        19: "Damage Reduction 5/-",
        20: "Mighty Rage, Rage 6/day",
    },
    "Ranger": {
        1: "1st Favored Enemy, Track, Wild Empathy",
        2: "Combat Style",
        3: "Endurance",
        4: "Animal Companion",
        5: "2nd Favored Enemy",
        6: "Improved Combat Style",
        7: "",
        8: "",
        9: "Evasion",
        10: "3rd Favored Enemy",
        11: "Combat Style Mastery",
        12: "",
        13: "Camouflage",
        14: "",
        15: "4th Favored Enemy",
        16: "",
        17: "Hide in Plain Sight",
        18: "",
        19: "",
        20: "5th Favored Enemy",
    },
    "Adept": {
        2: "Summon Familiar",
    },
}

# Adept spell slots per level
ADEPT_SPELLS = {
    1: {"0": 3, "1": 1},
    2: {"0": 3, "1": 1},
    3: {"0": 3, "1": 2},
    4: {"0": 3, "1": 2, "2": 0},
    5: {"0": 3, "1": 2, "2": 1},
    6: {"0": 3, "1": 3, "2": 1},
    7: {"0": 3, "1": 3, "2": 2},
    8: {"0": 3, "1": 3, "2": 2, "3": 0},
    9: {"0": 3, "1": 3, "2": 2, "3": 1},
    10: {"0": 3, "1": 3, "2": 3, "3": 1},
    11: {"0": 3, "1": 3, "2": 3, "3": 2},
    12: {"0": 3, "1": 3, "2": 3, "3": 2, "4": 0},
    13: {"0": 3, "1": 3, "2": 3, "3": 2, "4": 1},
    14: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 1},
    15: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 2},
    16: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 2, "5": 0},
    17: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 2, "5": 1},
    18: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 3, "5": 1},
    19: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 3, "5": 2},
    20: {"0": 3, "1": 3, "2": 3, "3": 3, "4": 3, "5": 2},
}

# Ranger spell slots per level
RANGER_SPELLS = {
    4: {"1": 0},
    5: {"1": 0},
    6: {"1": 1},
    7: {"1": 1},
    8: {"1": 1, "2": 0},
    9: {"1": 1, "2": 0},
    10: {"1": 1, "2": 1},
    11: {"1": 1, "2": 1, "3": 0},
    12: {"1": 1, "2": 1, "3": 1},
    13: {"1": 1, "2": 1, "3": 1},
    14: {"1": 2, "2": 1, "3": 1, "4": 0},
    15: {"1": 2, "2": 1, "3": 1, "4": 1},
    16: {"1": 2, "2": 2, "3": 1, "4": 1},
    17: {"1": 2, "2": 2, "3": 2, "4": 1},
    18: {"1": 3, "2": 2, "3": 2, "4": 1},
    19: {"1": 3, "2": 3, "3": 3, "4": 2},
    20: {"1": 3, "2": 3, "3": 3, "4": 3},
}


def seed_classes(conn):
    c = conn.cursor()

    for cls in CLASS_DEFS:
        bab_name = {good_bab: "good", average_bab: "average", poor_bab: "poor"}
        save_name = {good_save: "good", poor_save: "poor"}

        c.execute("""
            INSERT OR REPLACE INTO classes (
                name, category, hd_type, bab_progression,
                fort_progression, ref_progression, will_progression,
                skill_points_base, weapon_proficiency, armor_proficiency, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cls["name"], cls["category"], cls["hd_type"],
            bab_name[cls["bab"]],
            save_name[cls["fort"]],
            save_name[cls["ref"]],
            save_name[cls["will"]],
            cls["skill_points"],
            cls["weapon_proficiency"],
            cls["armor_proficiency"],
            cls["description"],
        ))

        features_map = CLASS_FEATURES.get(cls["name"], {})

        for level in range(1, 21):
            features = features_map.get(level, "")

            # Add spell slot info for casters
            if cls["name"] == "Adept" and level in ADEPT_SPELLS:
                spells = ADEPT_SPELLS[level]
                spell_text = ", ".join(f"L{k}: {v}" for k, v in spells.items())
                if features:
                    features += f"; Spells/day: {spell_text}"
                else:
                    features = f"Spells/day: {spell_text}"
            elif cls["name"] == "Ranger" and level in RANGER_SPELLS:
                spells = RANGER_SPELLS[level]
                spell_text = ", ".join(f"L{k}: {v}" for k, v in spells.items())
                if features:
                    features += f"; Spells/day: {spell_text}"
                else:
                    features = f"Spells/day: {spell_text}"

            c.execute("""
                INSERT OR REPLACE INTO class_progression (
                    class_name, level, bab, fort_save, ref_save, will_save,
                    hd_type, skill_points_per_level, features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cls["name"], level,
                cls["bab"](level),
                cls["fort"](level),
                cls["ref"](level),
                cls["will"](level),
                cls["hd_type"],
                cls["skill_points"],
                features,
            ))

    conn.commit()
    c.execute("SELECT COUNT(*) FROM classes")
    print(f"  Seeded {c.fetchone()[0]} class definitions")
    c.execute("SELECT COUNT(*) FROM class_progression")
    print(f"  Seeded {c.fetchone()[0]} class progression entries")


def main():
    print("Seeding class data...")
    conn = sqlite3.connect(DB_PATH)
    seed_classes(conn)
    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
