# Improving Monsters (D&D 3.5 SRD)

> Source: [d20srd.org — Improving Monsters](https://www.d20srd.org/srd/improvingMonsters.htm)
> Local copy: [Improving Monsters __ d20srd.org.htm](../Improving%20Monsters%20__%20d20srd.org.htm)
> Open Game Content under the OGL v1.0a.

A monster entry describes a *typical* creature of its kind. Improved monsters are made by combining any of three methods:

1. **Adding character classes** (Class Levels)
2. **Increasing the creature's Hit Dice**
3. **Adding a template**

These methods are not mutually exclusive — a templated creature can have extra HD *and* class levels.

## When to use which method

| Method | Best for |
|---|---|
| Class levels | Intelligent humanoid-shaped creatures (Advancement entry: "By character class"). Represents experience and learned skill. |
| Increased HD | Intelligent non-humanoid creatures and nonintelligent monsters. Represents superior, larger specimens. |
| Templates | Creatures with unusual heritage or an inflicted nature change. Usually tougher with new capabilities. |

---

## Ability Score Arrays

A typical (un-improved) monster is assumed to have **10 or 11 in each ability**, modified by racial bonuses. Improved monsters use one of three arrays:

| Array | Scores | Use when |
|---|---|---|
| **Standard** | 11, 11, 11, 10, 10, 10 | Default / un-improved monsters |
| **Nonelite** | 13, 12, 11, 10, 9, 8 | Monster takes NPC class levels |
| **Elite** | 15, 14, 13, 12, 10, 8 | Monster takes PC class levels (or any monster "unique enough to be improved") |

Templated and HD-advanced monsters may use any of the three arrays. The elite array is "appropriate for monsters who add levels in a player character class".

### Ability Score Increase per HD

> Treat monster Hit Dice the same as character level for determining ability score increases. This **only applies to Hit Dice increases** — monsters do not gain ability score increases for levels they "already reached" with their racial Hit Dice.

In practice: when adding HD past the base, count threshold crossings of 4th, 8th, 12th, 16th, 20th *total* HD that the *base* HD did not already cross. Each crossing gives +1 to one ability of choice.

---

## Monsters and Class Levels

A creature with class levels follows multiclass rules. Its **Hit Dice = class levels + racial HD**. The creature's "monster class" is always its favored class (no XP penalty). Class HD never affect the creature's size.

### 1-HD Humanoids — the Replacement Rule

> Creatures with 1 or less HD **replace** their monster levels with their character levels. The monster loses the attack bonus, saving throw bonuses, skills, and feats granted by its 1 monster HD and gains the attack bonus, save bonuses, skills, feats, and other class abilities of a 1st-level character of the appropriate class.

Implication: a 1-HD humanoid taking Fighter 1 has the BAB / saves / HP / skills / feats of a level-1 Fighter, **not** the sum of monster HD + class HD.

### Level Adjustment and ECL

**ECL (Effective Character Level) = racial HD + class levels + level adjustment.**

The monster is treated as having XP equal to the minimum needed for a character of its ECL. ECL determines wealth/equipment when outfitting the creature.

NPC gear is given only to creatures with `Advancement: By character class`. Other class-leveled creatures use treasure tables for their adjusted CR.

### Feats and Ability Bumps

> A monster's **total Hit Dice**, not its ECL, govern its acquisition of feats and ability score increases.

So a 5-HD creature with LA +2 (ECL 7) still has 1 + 5/3 = 2 feats and one HD-bump (at 4th HD).

---

## Increasing Hit Dice

When you advance a creature with more HD, its attack bonus, saves, feats, and skills improve per its **type**, not class.

### Table: Creature Improvement by Type

| Type | Hit Die | BAB | Good Saves | Skill Points |
|---|---|---|---|---|
| Aberration | d8 | HD × ¾ (cleric) | Will | 2 + Int per HD |
| Animal | d8 | HD × ¾ | Fort, Ref (sometimes Will) | 2 + Int |
| Construct | d10 | HD × ¾ | — | 2 + Int¹ |
| Dragon | d12 | HD × 1 (fighter) | Fort, Ref, Will | 6 + Int |
| Elemental | d8 | HD × ¾ | Air/Fire → Ref; Earth/Water → Fort | 2 + Int |
| Fey | d6 | HD × ½ (wizard) | Ref, Will | 6 + Int |
| Giant | d8 | HD × ¾ | Fort | 2 + Int |
| Humanoid | d8 | HD × ¾ | **Varies (any one)** | 2 + Int |
| Magical Beast | d10 | HD × 1 | Fort, Ref | 2 + Int |
| Monstrous Humanoid | d8 | HD × 1 | Ref, Will | 2 + Int |
| Ooze | d10 | HD × ¾ | — | 2 + Int¹ |
| Outsider | d8 | HD × 1 | Fort, Ref, Will | 8 + Int |
| Plant | d8 | HD × ¾ | Fort | 2 + Int¹ |
| Undead | d12 | HD × ½ | Will | 4 + Int¹ |
| Vermin | d8 | HD × ¾ | Fort | 2 + Int¹ |

**Footnotes**

1. **All types** have feats equal to **1 + 1 per 3 Hit Dice**.
2. As long as a creature has **Int ≥ 1**, it gains a minimum of **1 skill point per HD**.
3. ¹ Creatures with Intelligence "—" gain **no skill points and no feats**.

If the creature acquires a character class, that class's progression is used for the class HD, not the type's progression.

---

## Size Increases

A creature may grow when its HD are increased (the new size is given parenthetically in the creature's `Advancement` entry).

A size change affects:
- Any size-dependent special ability
- Ability scores (Str/Dex/Con)
- Natural armor
- AC and attack bonus
- Damage values

### Table: Changes to Statistics by Size

Apply per **one-step** size change. Repeat for multi-step changes. Reverse signs to shrink.

| Old Size¹ → New Size | Str | Dex | Con | Nat. Armor | AC / Attack |
|---|---|---|---|---|---|
| Fine → Diminutive | — | -2 | — | — | -4 |
| Diminutive → Tiny | +2 | -2 | — | — | -2 |
| Tiny → Small | +4 | -2 | — | — | -1 |
| Small → Medium | +4 | -2 | +2 | — | -1 |
| Medium → Large | +8 | -2 | +4 | +2 | -1 |
| Large → Huge | +8 | -2 | +4 | +3 | -1 |
| Huge → Gargantuan | +8 | — | +4 | +4 | -2 |
| Gargantuan → Colossal | +8 | — | +4 | +5 | -4 |

### Table: Increased Damage By Size

Step damage one row per +1 size category. Anything not listed is unchanged.

| Old Damage | New Damage |
|---|---|
| 1d2 | 1d3 |
| 1d3 | 1d4 |
| 1d4 | 1d6 |
| 1d6 | 1d8 |
| 1d8 | 2d6 |
| 1d10 | 2d8 |
| 2d6 | 3d6 |
| 2d8 | 3d8 |

(House-rule extensions used in this project: 1d12→3d6, 2d10→4d8, 3d6→3d8, 3d8→4d8, 4d8→6d8, 6d8→8d8, 8d8→12d8.)

---

## Templates

A template is a set of instructions applied to a "base creature". Templates can represent freaks of nature, single-experimenter creations, or first-generation hybrids.

### Acquired vs. Inherited

| Type | Description |
|---|---|
| **Acquired** | Added to a creature anytime — the creature did not always have these traits. |
| **Inherited** | Part of the creature from birth. |

Some templates can be either type. **Apply inherited templates first, then acquired ones.**

### Reading a Template

A template's description tells you how to alter each line of the creature's stat block. Common entries:

| Stat | What a template may change |
|---|---|
| Size and Type | Often changes type. New type usually adds the **augmented** subtype paired with the original. New creature has the *traits* of the new type but *features* of the original. |
| Hit Dice | Most don't change HD. Some swap HD die size (via type change). Most that do change HD only modify *original* HD, not class HD. If the entry is missing, HD don't change unless Con changes. |
| Initiative | Changes only if Dex changes or if Improved Initiative is added/removed. |
| Speed | Template states any change. Often *adds* a new movement mode. |
| Armor Class | Use size-change table for size changes. Template overrides if it specifies a new AC method. |
| Base Attack/Grapple | Templates rarely change BAB. Str / size changes flow through to grapple. |
| Attack / Full Attack | Usually unchanged. Str/Dex changes flow through. Size changes affect attack bonus. |
| Damage | Damage uses Str: ×1.5 for two-handed or single natural attack; ×1 for primary; ×0.5 for secondary. |
| Space/Reach | Updated for size changes. May not capture exceptional reach. |
| Special Attacks / Qualities | Template adds or removes; provides DCs if applicable. New type's qualities still apply. |
| Base Saves | Adjusted for new Con/Dex/Wis modifiers. Template may declare a different "good" save. |
| Abilities | Per template description. |
| Skills | Skill points usually unchanged unless HD change or new key abilities. Treat base creature's listed skills as class skills. New skills added by template are also class skills. |
| Feats | Number of feats usually unchanged (HD usually unchanged). Some templates grant bonus feats. |
| Environment / Organization / Treasure / Alignment | Usually same as base creature unless template specifies. |
| Challenge Rating | Most templates increase CR. Modifier may be flat or vary by base creature's HD/CR. |
| Advancement | Usually same as base creature. |
| Level Adjustment | Modifier added to base's LA. **Meaningless unless Int ≥ 3** (cannot take class levels otherwise). |

### Stacking Templates

There's no theoretical limit. Apply one at a time, **inherited before acquired**. A template may change the type and disqualify the creature from another template you wanted to add — order matters.

---

## Advanced Monster Challenge Rating

When advancing a creature with **1 or fewer HD** by class levels, advance it as a character (use PC CR rules). For everything else, follow the rules below.

### Adding Class Levels

Decide whether each class level **plays to** the monster's existing strengths.

| Class type | CR effect |
|---|---|
| **Associated** (plays to strengths) | +1 CR per level |
| **Nonassociated** | +½ CR per level — until count of nonassociated levels equals the creature's *original* HD; subsequent levels are then treated as associated (+1 each) |
| **NPC class** | **Always nonassociated**, regardless of fit |

#### Associated class examples (SRD)

- A creature relying on its **fighting ability**: Barbarian, Fighter, Paladin, Ranger
- A creature relying on **stealth or skill**: Rogue, Ranger
- A creature that **already casts spells as that class**: the matching spellcasting class (levels stack with innate casting)

#### Suggested ability scores

| Improvement | Recommended ability scores |
|---|---|
| No class levels | Standard array (11, 11, 11, 10, 10, 10) |
| PC class levels | **Elite array** (15, 14, 13, 12, 10, 8) |
| NPC class levels | **Nonelite array** (13, 12, 11, 10, 9, 8) |

### Adding Hit Dice

Use **Table: Improved Monster CR Increase**. **Do not stack** this with class-level CR — pick whichever applies.

| Original Type | CR Increase |
|---|---|
| Aberration, Construct, Elemental, Fey, Giant, Humanoid, Ooze, Plant, Undead, Vermin | **+1 per 4 HD added** |
| Animal, Magical Beast, Monstrous Humanoid | **+1 per 3 HD added** |
| Dragon, Outsider — *and nonassociated class levels* | **+1 per 2 HD or 2 levels added** |
| Directly associated class levels | **+1 per level added** |

#### Other CR Modifiers (cumulative on top of the above)

| Modifier | CR Increase |
|---|---|
| Size increased to **Large or larger** | +1 |
| Monster uses **elite array** ¹ | +1 |
| New special attacks/qualities **significantly** improve combat | +2 |
| New special attacks/qualities **minorly** improve combat | +1 |
| Template added | + template's CR modifier |

¹ Don't apply if you advanced by class levels — class-leveled monsters are *assumed* to use the elite array.

#### Watch for diminishing returns

> In general, once you've doubled a creature's CR, you should closely watch any additional increases. Adding HD improves several abilities; radical increases might not follow this progression indefinitely.

Compare the improved BAB, saves, and special-ability DCs to typical characters of the appropriate level and adjust CR accordingly.

### Increasing Size

Generally, larger size **increases** combat effectiveness (more Str, more reach, etc.). Apply the +1 CR modifier when the creature is pushed past Medium.

Caveat: monsters that *benefit* from being small may **lose** effectiveness when enlarged. Monsters that don't benefit from size increases don't advance that way at all.

### Adding Special Abilities

You can add any spell-like, supernatural, or extraordinary ability. A coherent suite of related abilities counts as **one** modifier.

| Significance | CR effect |
|---|---|
| Significantly improves combat (e.g. ability that can incapacitate / cripple a target in one round, or seriously diminish vulnerability to common attacks) | +2 |
| Minor improvement | +1 |
| Trivial | +0 |

Stacks with HD or class CR if the abilities are not tied to those. Don't double-count if the monster has both special attacks **and** special qualities — apply the higher tier once.

Scale the evaluation by the monster's current CR — what's "significant" at CR 3 may be trivial at CR 18.

---

## Quick Reference: Key Formulas

```
Total HD       = racial HD + class levels (or class levels alone if base ≤ 1 HD)
ECL            = racial HD + class levels + level adjustment
Feats          = 1 + total_HD ÷ 3   (Int "—" creatures: 0 feats)
Skill points   = (type_rate + Int_mod) × HD   (min 1 if Int ≥ 1; 0 if Int "—")
HD ability bumps = floor(total_HD / 4) − floor(base_HD / 4)
Good save      = 2 + HD ÷ 2
Poor save      = HD ÷ 3
BAB (good)     = HD              (Fighter)
BAB (avg)      = HD × 3 ÷ 4      (Cleric)
BAB (poor)     = HD ÷ 2          (Wizard)
```

---

## See Also

- [Monsters as Races](https://www.d20srd.org/srd/monstersAsRaces.htm)
- [Types and Subtypes](https://www.d20srd.org/srd/typesSubtypes.htm)
- [Special Abilities](https://www.d20srd.org/srd/specialAbilities.htm)
- [Saving Throws](https://www.d20srd.org/srd/combat/combatStatistics.htm#savingThrows)
