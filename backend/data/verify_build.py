"""Quick verification of the built DB files."""
import sqlite3

for db_name, root in [("base.db", "monster_presets"), ("prod.db", "monster_builds")]:
    con = sqlite3.connect(f"backend/data/{db_name}")
    con.row_factory = sqlite3.Row
    print(f"=== {db_name} (root={root}) ===")
    tables = [root, f"{root}_classes", f"{root}_attacks", f"{root}_feats",
              f"{root}_skill_ranks", f"{root}_special_traits"]
    for tbl in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n} rows")

    total    = con.execute(f"SELECT COUNT(*) FROM {root}").fetchone()[0]
    flagged  = con.execute(f"SELECT COUNT(*) FROM {root} WHERE needs_review=1").fetchone()[0]
    print(f"  needs_review: {flagged}/{total} flagged")

    print("  Sample flagged:")
    for row in con.execute(f"SELECT name, review_notes FROM {root} WHERE needs_review=1 LIMIT 8"):
        print(f"    [{row['name']}]: {row['review_notes']}")

    # Spot-check Choker
    choker = con.execute(f"SELECT * FROM {root} WHERE name='Choker'").fetchone()
    if choker:
        print(f"  Choker: size={choker['size']} type={choker['type']} "
              f"str={choker['str']} hd={choker['racial_hd_count']}d{choker['racial_hd_die']} "
              f"ac={choker['ac_total']}")
        feats = con.execute(f"SELECT * FROM {root}_feats WHERE monster_id=?", (choker["id"],)).fetchall()
        print(f"  Choker feats: {[(f['feat_id'], f['feat_name_raw'], f['is_bonus']) for f in feats]}")
        skills = con.execute(f"SELECT * FROM {root}_skill_ranks WHERE monster_id=?", (choker["id"],)).fetchall()
        print(f"  Choker skills: {[(s['skill_name'], s['total_bonus']) for s in skills]}")
        atks = con.execute(f"SELECT * FROM {root}_attacks WHERE monster_id=?", (choker["id"],)).fetchall()
        print(f"  Choker attacks: {[(a['natural_name'], a['count'], a['damage_dice']) for a in atks]}")

    # Spot-check Aboleth Mage (class-leveled, multi-HD)
    ab = con.execute(f"SELECT * FROM {root} WHERE name LIKE 'Aboleth Mage%'").fetchone()
    if ab:
        cls_rows = con.execute(f"SELECT * FROM {root}_classes WHERE monster_id=?", (ab["id"],)).fetchall()
        print(f"  Aboleth Mage: hd={ab['racial_hd_count']}d{ab['racial_hd_die']} classes={[(c['class_name_raw'], c['levels']) for c in cls_rows]}")

    con.close()
    print()
