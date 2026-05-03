"""
D&D 3.5 monster-advancement rules, organized by SRD section.

Each module begins with a verbatim quote of the SRD passage it implements
(see "Improving Monsters" — d20srd.org). Functions here are pure and
stateless: they take inputs and return values, never mutate.

The orchestration that ties these rules to a concrete monster instance
lives in `app.services.advancement` (and the `AdvancedMonster` dataclass
in `app.models.monster`).
"""
