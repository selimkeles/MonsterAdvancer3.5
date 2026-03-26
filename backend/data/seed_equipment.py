"""
Seed D&D 3.5 weapon and armor data into SQLite.
Source: SRD 3.5 Equipment tables.
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "monsters.db")


WEAPONS = [
    # Simple Weapons - Unarmed
    ("Gauntlet", "Simple", "Unarmed", "2 gp", "1d2", "1d3", "x2", None, 1.0, "Bludgeoning", None),
    ("Unarmed Strike", "Simple", "Unarmed", None, "1d2", "1d3", "x2", None, 0.0, "Bludgeoning", "nonlethal"),

    # Simple Weapons - Light Melee
    ("Dagger", "Simple", "Light Melee", "2 gp", "1d3", "1d4", "19-20/x2", "10 ft.", 1.0, "Piercing or Slashing", None),
    ("Dagger, punching", "Simple", "Light Melee", "2 gp", "1d3", "1d4", "x3", None, 1.0, "Piercing", None),
    ("Gauntlet, spiked", "Simple", "Light Melee", "5 gp", "1d3", "1d4", "x2", None, 1.0, "Piercing", None),
    ("Mace, light", "Simple", "Light Melee", "5 gp", "1d4", "1d6", "x2", None, 4.0, "Bludgeoning", None),
    ("Sickle", "Simple", "Light Melee", "6 gp", "1d4", "1d6", "x2", None, 2.0, "Slashing", "trip"),

    # Simple Weapons - One-Handed Melee
    ("Club", "Simple", "One-Handed Melee", None, "1d4", "1d6", "x2", "10 ft.", 3.0, "Bludgeoning", None),
    ("Mace, heavy", "Simple", "One-Handed Melee", "12 gp", "1d6", "1d8", "x2", None, 8.0, "Bludgeoning", None),
    ("Morningstar", "Simple", "One-Handed Melee", "8 gp", "1d6", "1d8", "x2", None, 6.0, "Bludgeoning and Piercing", None),
    ("Shortspear", "Simple", "One-Handed Melee", "1 gp", "1d4", "1d6", "x2", "20 ft.", 3.0, "Piercing", None),

    # Simple Weapons - Two-Handed Melee
    ("Longspear", "Simple", "Two-Handed Melee", "5 gp", "1d6", "1d8", "x3", None, 9.0, "Piercing", "reach"),
    ("Quarterstaff", "Simple", "Two-Handed Melee", None, "1d4/1d4", "1d6/1d6", "x2", None, 4.0, "Bludgeoning", "double"),
    ("Spear", "Simple", "Two-Handed Melee", "2 gp", "1d6", "1d8", "x3", "20 ft.", 6.0, "Piercing", None),

    # Simple Weapons - Ranged
    ("Crossbow, heavy", "Simple", "Ranged", "50 gp", "1d8", "1d10", "19-20/x2", "120 ft.", 8.0, "Piercing", None),
    ("Crossbow, light", "Simple", "Ranged", "35 gp", "1d6", "1d8", "19-20/x2", "80 ft.", 4.0, "Piercing", None),
    ("Dart", "Simple", "Ranged", "5 sp", "1d3", "1d4", "x2", "20 ft.", 0.5, "Piercing", None),
    ("Javelin", "Simple", "Ranged", "1 gp", "1d4", "1d6", "x2", "30 ft.", 2.0, "Piercing", None),
    ("Sling", "Simple", "Ranged", None, "1d3", "1d4", "x2", "50 ft.", 0.0, "Bludgeoning", None),

    # Martial Weapons - Light Melee
    ("Axe, throwing", "Martial", "Light Melee", "8 gp", "1d4", "1d6", "x2", "10 ft.", 2.0, "Slashing", None),
    ("Hammer, light", "Martial", "Light Melee", "1 gp", "1d3", "1d4", "x2", "20 ft.", 2.0, "Bludgeoning", None),
    ("Handaxe", "Martial", "Light Melee", "6 gp", "1d4", "1d6", "x3", None, 3.0, "Slashing", None),
    ("Kukri", "Martial", "Light Melee", "8 gp", "1d3", "1d4", "18-20/x2", None, 2.0, "Slashing", None),
    ("Pick, light", "Martial", "Light Melee", "4 gp", "1d3", "1d4", "x4", None, 3.0, "Piercing", None),
    ("Sap", "Martial", "Light Melee", "1 gp", "1d4", "1d6", "x2", None, 2.0, "Bludgeoning", "nonlethal"),
    ("Shield, light", "Martial", "Light Melee", None, "1d2", "1d3", "x2", None, None, "Bludgeoning", None),
    ("Sword, short", "Martial", "Light Melee", "10 gp", "1d4", "1d6", "19-20/x2", None, 2.0, "Piercing", None),

    # Martial Weapons - One-Handed Melee
    ("Battleaxe", "Martial", "One-Handed Melee", "10 gp", "1d6", "1d8", "x3", None, 6.0, "Slashing", None),
    ("Flail", "Martial", "One-Handed Melee", "8 gp", "1d6", "1d8", "x2", None, 5.0, "Bludgeoning", "trip, disarm"),
    ("Longsword", "Martial", "One-Handed Melee", "15 gp", "1d6", "1d8", "19-20/x2", None, 4.0, "Slashing", None),
    ("Pick, heavy", "Martial", "One-Handed Melee", "8 gp", "1d4", "1d6", "x4", None, 6.0, "Piercing", None),
    ("Rapier", "Martial", "One-Handed Melee", "20 gp", "1d4", "1d6", "18-20/x2", None, 2.0, "Piercing", "finesse"),
    ("Scimitar", "Martial", "One-Handed Melee", "15 gp", "1d4", "1d6", "18-20/x2", None, 4.0, "Slashing", None),
    ("Shield, heavy", "Martial", "One-Handed Melee", None, "1d3", "1d4", "x2", None, None, "Bludgeoning", None),
    ("Trident", "Martial", "One-Handed Melee", "15 gp", "1d6", "1d8", "x2", "10 ft.", 4.0, "Piercing", "brace"),
    ("Warhammer", "Martial", "One-Handed Melee", "12 gp", "1d6", "1d8", "x3", None, 5.0, "Bludgeoning", None),

    # Martial Weapons - Two-Handed Melee
    ("Falchion", "Martial", "Two-Handed Melee", "75 gp", "1d6", "2d4", "18-20/x2", None, 8.0, "Slashing", None),
    ("Glaive", "Martial", "Two-Handed Melee", "8 gp", "1d8", "1d10", "x3", None, 10.0, "Slashing", "reach"),
    ("Greataxe", "Martial", "Two-Handed Melee", "20 gp", "1d10", "1d12", "x3", None, 12.0, "Slashing", None),
    ("Greatclub", "Martial", "Two-Handed Melee", "5 gp", "1d8", "1d10", "x2", None, 8.0, "Bludgeoning", None),
    ("Flail, heavy", "Martial", "Two-Handed Melee", "15 gp", "1d8", "1d10", "19-20/x2", None, 10.0, "Bludgeoning", "trip, disarm"),
    ("Greatsword", "Martial", "Two-Handed Melee", "50 gp", "1d10", "2d6", "19-20/x2", None, 8.0, "Slashing", None),
    ("Guisarme", "Martial", "Two-Handed Melee", "9 gp", "1d6", "2d4", "x3", None, 12.0, "Slashing", "reach, trip"),
    ("Halberd", "Martial", "Two-Handed Melee", "10 gp", "1d8", "1d10", "x3", None, 12.0, "Piercing or Slashing", "brace, trip"),
    ("Lance", "Martial", "Two-Handed Melee", "10 gp", "1d6", "1d8", "x3", None, 10.0, "Piercing", "reach, double damage mounted charge"),
    ("Ranseur", "Martial", "Two-Handed Melee", "10 gp", "1d6", "2d4", "x3", None, 12.0, "Piercing", "reach, disarm"),
    ("Scythe", "Martial", "Two-Handed Melee", "18 gp", "1d6", "2d4", "x4", None, 10.0, "Piercing or Slashing", "trip"),

    # Martial Weapons - Ranged
    ("Longbow", "Martial", "Ranged", "75 gp", "1d6", "1d8", "x3", "100 ft.", 3.0, "Piercing", None),
    ("Longbow, composite", "Martial", "Ranged", "100 gp", "1d6", "1d8", "x3", "110 ft.", 3.0, "Piercing", None),
    ("Shortbow", "Martial", "Ranged", "30 gp", "1d4", "1d6", "x3", "60 ft.", 2.0, "Piercing", None),
    ("Shortbow, composite", "Martial", "Ranged", "75 gp", "1d4", "1d6", "x3", "70 ft.", 2.0, "Piercing", None),

    # Exotic Weapons (common ones)
    ("Bastard sword", "Exotic", "One-Handed Melee", "35 gp", "1d8", "1d10", "19-20/x2", None, 6.0, "Slashing", None),
    ("Dwarven waraxe", "Exotic", "One-Handed Melee", "30 gp", "1d8", "1d10", "x3", None, 8.0, "Slashing", None),
    ("Whip", "Exotic", "One-Handed Melee", "1 gp", "1d2", "1d3", "x2", None, 2.0, "Slashing", "reach, disarm, trip, nonlethal"),
    ("Spiked chain", "Exotic", "Two-Handed Melee", "25 gp", "1d6", "2d4", "x2", None, 10.0, "Piercing", "reach, disarm, trip"),
    ("Hand crossbow", "Exotic", "Ranged", "100 gp", "1d3", "1d4", "19-20/x2", "30 ft.", 2.0, "Piercing", None),
    ("Net", "Exotic", "Ranged", "20 gp", None, None, None, "10 ft.", 6.0, None, "entangle"),
]


ARMOR = [
    # Light Armor
    ("Padded", "Light", 1, 8, 0, 5, "30 ft.", "20 ft.", 10.0, "5 gp"),
    ("Leather", "Light", 2, 6, 0, 10, "30 ft.", "20 ft.", 15.0, "10 gp"),
    ("Studded leather", "Light", 3, 5, -1, 15, "30 ft.", "20 ft.", 20.0, "25 gp"),
    ("Chain shirt", "Light", 4, 4, -2, 20, "30 ft.", "20 ft.", 25.0, "100 gp"),

    # Medium Armor
    ("Hide", "Medium", 3, 4, -3, 20, "20 ft.", "15 ft.", 25.0, "15 gp"),
    ("Scale mail", "Medium", 4, 3, -4, 25, "20 ft.", "15 ft.", 30.0, "50 gp"),
    ("Chainmail", "Medium", 5, 2, -5, 30, "20 ft.", "15 ft.", 40.0, "150 gp"),
    ("Breastplate", "Medium", 5, 3, -4, 25, "20 ft.", "15 ft.", 30.0, "200 gp"),

    # Heavy Armor
    ("Splint mail", "Heavy", 6, 0, -7, 40, "20 ft.", "15 ft.", 45.0, "200 gp"),
    ("Banded mail", "Heavy", 6, 1, -6, 35, "20 ft.", "15 ft.", 35.0, "250 gp"),
    ("Half-plate", "Heavy", 7, 0, -7, 40, "20 ft.", "15 ft.", 50.0, "600 gp"),
    ("Full plate", "Heavy", 8, 1, -6, 35, "20 ft.", "15 ft.", 50.0, "1500 gp"),

    # Shields
    ("Buckler", "Shield", 1, None, -1, 5, None, None, 5.0, "15 gp"),
    ("Shield, light wooden", "Shield", 1, None, -1, 5, None, None, 5.0, "3 gp"),
    ("Shield, light steel", "Shield", 1, None, -1, 5, None, None, 6.0, "9 gp"),
    ("Shield, heavy wooden", "Shield", 2, None, -2, 15, None, None, 10.0, "7 gp"),
    ("Shield, heavy steel", "Shield", 2, None, -2, 15, None, None, 15.0, "20 gp"),
    ("Shield, tower", "Shield", 4, 2, -10, 50, None, None, 45.0, "30 gp"),
]


def seed_weapons(conn):
    c = conn.cursor()
    for w in WEAPONS:
        c.execute("""
            INSERT OR REPLACE INTO weapons (
                name, category, subcategory, cost, dmg_small, dmg_medium,
                critical, range_increment, weight, damage_type, special
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, w)
    conn.commit()
    print(f"  Seeded {len(WEAPONS)} weapons")


def seed_armor(conn):
    c = conn.cursor()
    for a in ARMOR:
        c.execute("""
            INSERT OR REPLACE INTO armor (
                name, category, ac_bonus, max_dex, check_penalty,
                spell_failure, speed_30, speed_20, weight, cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, a)
    conn.commit()
    print(f"  Seeded {len(ARMOR)} armor/shields")


def main():
    print("Seeding equipment data...")
    conn = sqlite3.connect(DB_PATH)
    seed_weapons(conn)
    seed_armor(conn)
    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
