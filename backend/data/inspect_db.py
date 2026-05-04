import sqlite3
con = sqlite3.connect("backend/data/base.db")
con.row_factory = sqlite3.Row

# --- armor_class_components schema and FKs ---
print("=== armor_class_components columns ===")
for row in con.execute("PRAGMA table_info(armor_class_components)"):
    print(f"  {row[1]:30s} {row[2]}")

print("\n=== armor_class_components foreign keys ===")
fks = con.execute("PRAGMA foreign_key_list(armor_class_components)").fetchall()
print(f"  {len(fks)} FK(s) defined" if fks else "  None — no FKs to armor/weapons tables")

# Azer sample (has scale mail + heavy shield in the SRD)
az = con.execute("SELECT id, name FROM monsters WHERE name='Azer'").fetchone()
if az:
    ac = con.execute("SELECT * FROM armor_class_components WHERE monster_id=?", (az["id"],)).fetchone()
    print(f"\n  Azer armor_class_components: nat={ac['base_nat_armor']} armor={ac['base_armor']} "
          f"armor_desc={ac['base_armor_description']!r} shield={ac['base_shield']}")

# --- attacks table: design clarification ---
print("\n=== attacks table: Choker (monster_id=1) ===")
for a in con.execute("SELECT id, monster_id, att_name, att_count, weapon_nature, group_id FROM attacks WHERE monster_id=1"):
    print(f"  row id={a['id']}  monster_id={a['monster_id']}  name={a['att_name']}  "
          f"count={a['att_count']}  nature={a['weapon_nature']}  group={a['group_id']}")

bite_total = con.execute("SELECT COUNT(*) FROM attacks WHERE att_name='Bite'").fetchone()[0]
bite_monsters = con.execute("SELECT COUNT(*) FROM (SELECT monster_id FROM attacks WHERE att_name='Bite' GROUP BY monster_id)").fetchone()[0]
print(f"\n  'Bite' rows total: {bite_total} across {bite_monsters} different monsters")

# --- ID relationship across tables ---
print("\n=== ID relationships (Choker) ===")
ch = con.execute("SELECT id FROM monster_presets WHERE name='Choker'").fetchone()
print(f"  monster_presets.id = {ch['id']}  (Choker's monster ID)")
feats = con.execute("SELECT id, monster_id, feat_id FROM monster_presets_feats WHERE monster_id=?", (ch["id"],)).fetchall()
for f in feats:
    print(f"  monster_presets_feats row: id={f['id']} (own PK)  monster_id={f['monster_id']} (FK -> monster_presets.id)  feat_id={f['feat_id']}")

# --- named_lists contents ---
print("\n=== named_lists (all list_name values) ===")
for row in con.execute("SELECT list_name, COUNT(*) n FROM named_lists GROUP BY list_name ORDER BY list_name"):
    print(f"  {row[0]:25s} {row[1]} values")

# --- which catalog tables are actually used by FK from anything ---
print("\n=== which ruleset tables have FKs pointing TO them ===")
for tbl in ["armor", "weapons", "feats", "type_rules", "classes", "class_progression"]:
    referencing = []
    for other_tbl in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        fks = con.execute(f"PRAGMA foreign_key_list({other_tbl['name']})").fetchall()
        for fk in fks:
            if fk["table"] == tbl:
                referencing.append(f"{other_tbl['name']}.{fk['from']}")
    print(f"  {tbl:25s} <- {referencing if referencing else 'nothing (unused as FK target)'}")

con.close()
