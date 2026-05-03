"""SRD: parse a creature's Advancement text entry.

The Advancement column in the DB is messy.  This module normalises it into a
structured object that the rest of the app can query without touching raw text.

Known value categories (from a full scan of the DB):
  1. Sentinels  : None, "-", "Special (see below)"
                  → creature has no standard advancement
  2. By class   : "By character class"
                  → creature takes class levels, no HD increase
  3. Open-ended : "37+ HD (Gargantuan)"
                  → can advance, but SRD gives no upper cap
  4. Normal     : "4-6 HD (Small); 7-9 HD (Medium)"   (most common)
                  → bounded range with size thresholds
  5. Malformed  : "13-24 (Medium); 25-36 HD (Large)"
                  → "HD" keyword is missing in some segments; still parseable
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Sentinel values that mean "no advancement" ──────────────────────────────

_NO_ADV_SENTINELS = {None, "", "-", "none", "special (see below)"}
_BY_CLASS_SENTINEL = "by character class"


@dataclass(frozen=True)
class AdvancementInfo:
    """Structured result of parsing an Advancement column entry.

    Attributes
    ----------
    can_advance_hd : bool
        True if the creature can gain extra racial Hit Dice.
        False for sentinels, "By character class", and open-ended entries
        that we treat as uncapped.  (Open-ended *can* advance; the cap is
        just None rather than a concrete number — see max_hd.)
    by_class : bool
        True when the creature's only advancement path is class levels.
    max_hd : int | None
        The highest HD value found in the advancement text, or None when
        advancement is open-ended, by class, or a sentinel.
    size_thresholds : list[tuple[int, str]]
        Ordered list of (min_hd, size_name) pairs extracted from the text.
        e.g. "4-6 HD (Small); 7-9 HD (Medium)"
              → [(4, "Small"), (7, "Medium")]
    raw : str | None
        The original text for display purposes.
    """

    can_advance_hd: bool
    by_class: bool
    max_hd: Optional[int]
    size_thresholds: list = field(default_factory=list)  # list[tuple[int,str]]
    raw: Optional[str] = None


# ── Internal helpers ─────────────────────────────────────────────────────────

# Matches a single segment like:
#   "4-6 HD (Small)"  "3 HD (Medium)"  "37+ HD (Gargantuan)"
#   "13-24 (Medium)"  (missing HD keyword — malformed but real)
# Group layout: (lower) (upper|None) (plus_sign|None) (size)
_SEGMENT_RE = re.compile(
    r'(\d+)'                        # group 1: lower bound
    r'(?:\s*[-–]\s*(\d+)|(\+))?'   # group 2: range upper  OR  group 3: open "+"
    r'\s*(?:HD\s*)?'                # optional "HD" keyword
    r'\((\w[\w ]*)\)',              # group 4: size name
    re.IGNORECASE,
)


def parse_advancement(text: Optional[str]) -> AdvancementInfo:
    """Parse an Advancement column value into an AdvancementInfo.

    Examples
    --------
    >>> parse_advancement("4-6 HD (Small); 7-9 HD (Medium)").max_hd
    9
    >>> parse_advancement("37+ HD (Gargantuan)").max_hd is None
    True
    >>> parse_advancement("37+ HD (Gargantuan)").can_advance_hd
    True
    >>> parse_advancement("By character class").by_class
    True
    >>> parse_advancement("-").can_advance_hd
    False
    """
    raw = text
    normalised = (text or "").strip().lower()

    # ── Sentinels ────────────────────────────────────────────────────────────
    if normalised in _NO_ADV_SENTINELS:
        return AdvancementInfo(
            can_advance_hd=False, by_class=False,
            max_hd=None, size_thresholds=[], raw=raw,
        )

    # ── By character class ───────────────────────────────────────────────────
    if normalised.startswith(_BY_CLASS_SENTINEL):
        return AdvancementInfo(
            can_advance_hd=False, by_class=True,
            max_hd=None, size_thresholds=[], raw=raw,
        )

    # ── HD range segments ────────────────────────────────────────────────────
    thresholds: list[tuple[int, str]] = []
    max_hd: Optional[int] = None
    open_ended = False

    for m in _SEGMENT_RE.finditer(text or ""):
        lower = int(m.group(1))
        upper_str = m.group(2)       # e.g. "6" from "4-6 HD"
        is_open = m.group(3) is not None  # explicit "+" suffix
        size = m.group(4).strip().capitalize()

        thresholds.append((lower, size))

        if upper_str is not None:
            candidate = int(upper_str)
            if max_hd is None or candidate > max_hd:
                max_hd = candidate
        elif is_open:
            # "N+ HD (Size)" — genuinely no upper cap
            open_ended = True
        else:
            # "N HD (Size)" — single allowed value; the lower IS the max
            if max_hd is None or lower > max_hd:
                max_hd = lower

    if not thresholds:
        # Unrecognised format — treat as no standard advancement
        return AdvancementInfo(
            can_advance_hd=False, by_class=False,
            max_hd=None, size_thresholds=[], raw=raw,
        )

    # Open-ended means no firm cap; discard any partial max
    if open_ended:
        max_hd = None

    thresholds.sort(key=lambda t: t[0])

    return AdvancementInfo(
        can_advance_hd=True,
        by_class=False,
        max_hd=max_hd,
        size_thresholds=thresholds,
        raw=raw,
    )


def size_for_hd(info: AdvancementInfo, hd: int) -> Optional[str]:
    """Return the size the creature should be at *hd* Hit Dice.

    Returns None if advancement info has no thresholds.
    """
    if not info.size_thresholds:
        return None
    result = None
    for min_hd, size in info.size_thresholds:
        if hd >= min_hd:
            result = size
    return result
