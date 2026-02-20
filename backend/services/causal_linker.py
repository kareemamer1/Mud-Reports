"""Causal linker — applies 7 rules to connect cause-effect event pairs.

Rules from design doc §5.4.  Each rule scans the sorted event list for
matching pairs within a specified time window, then creates CausalLink
objects and populates Event.related_events.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from backend.schemas_insights import CausalLink, Event, EventType


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(iso: str) -> date:
    return date.fromisoformat(iso)


def _events_of_type(events: list[Event], *types: EventType) -> list[Event]:
    return [e for e in events if e.event_type in types]


def _in_window(cause_date: str, effect_date: str, days_back: int, days_forward: int = 0) -> bool:
    """Check if cause_date falls within [effect_date - days_back, effect_date + days_forward]."""
    cd = _parse_date(cause_date)
    ed = _parse_date(effect_date)
    return (ed - timedelta(days=days_back)) <= cd <= (ed + timedelta(days=days_forward))


def _link(cause: Event, effect: Event, rule: str, explanation: str, confidence: str) -> CausalLink:
    """Create a CausalLink and wire up related_events on both sides."""
    if effect.id not in cause.related_events:
        cause.related_events.append(effect.id)
    if cause.id not in effect.related_events:
        effect.related_events.append(cause.id)
    return CausalLink(
        cause_event_id=cause.id,
        effect_event_id=effect.id,
        rule_name=rule,
        explanation=explanation,
        confidence=confidence,
    )


# ── Rules ────────────────────────────────────────────────────────────────────

def _rule_screen_failure_from_solids(events: list[Event]) -> list[CausalLink]:
    """SolidsSpike/SandIncrease (N-1..N) → ShakerDown (N).  1-day lookback.  HIGH."""
    links: list[CausalLink] = []
    causes = _events_of_type(events, EventType.SOLIDS_SPIKE, EventType.SAND_INCREASE)
    effects = _events_of_type(events, EventType.SHAKER_DOWN)
    for effect in effects:
        for cause in causes:
            if _in_window(cause.date, effect.date, days_back=1):
                cause_label = "elevated solids" if cause.event_type == EventType.SOLIDS_SPIKE else "sand increase"
                links.append(_link(
                    cause, effect,
                    rule="screen_failure_from_solids",
                    explanation=(
                        f"{effect.title} likely caused by {cause_label} "
                        f"on {cause.date}."
                    ),
                    confidence="HIGH",
                ))
    return links


def _rule_lgs_from_centrifuge_down(events: list[Event]) -> list[CausalLink]:
    """CentrifugeDown (N-3..N-1) → LGSCreep (N-2..N).  3-day lookback.  HIGH."""
    links: list[CausalLink] = []
    causes = _events_of_type(events, EventType.CENTRIFUGE_DOWN)
    effects = _events_of_type(events, EventType.LGS_CREEP)
    for effect in effects:
        for cause in causes:
            if _in_window(cause.date, effect.date, days_back=3):
                links.append(_link(
                    cause, effect,
                    rule="lgs_from_centrifuge_down",
                    explanation=(
                        f"LGS accumulation correlates with {cause.values.get('centrifuge', 'centrifuge')} "
                        f"downtime on {cause.date}."
                    ),
                    confidence="HIGH",
                ))
    return links


def _rule_rheology_from_new_chemical(events: list[Event]) -> list[CausalLink]:
    """NewChemical (N-1..N) → RheologyShift (N).  1-day lookback.  HIGH."""
    links: list[CausalLink] = []
    causes = _events_of_type(events, EventType.NEW_CHEMICAL)
    effects = _events_of_type(events, EventType.RHEOLOGY_SHIFT)
    for effect in effects:
        for cause in causes:
            if _in_window(cause.date, effect.date, days_back=1):
                chem_name = cause.values.get("item_name", "new chemical")
                links.append(_link(
                    cause, effect,
                    rule="rheology_from_new_chemical",
                    explanation=(
                        f"Rheology change follows introduction of '{chem_name}' "
                        f"on {cause.date}."
                    ),
                    confidence="HIGH",
                ))
    return links


def _rule_rheology_from_lgs(events: list[Event]) -> list[CausalLink]:
    """LGSCreep (N-3..N) → RheologyShift(UP) (N).  3-day lookback.  MEDIUM."""
    links: list[CausalLink] = []
    causes = _events_of_type(events, EventType.LGS_CREEP)
    effects = [
        e for e in _events_of_type(events, EventType.RHEOLOGY_SHIFT)
        if e.values.get("direction") == "UP"
    ]
    for effect in effects:
        for cause in causes:
            if _in_window(cause.date, effect.date, days_back=3):
                links.append(_link(
                    cause, effect,
                    rule="rheology_from_lgs",
                    explanation=(
                        f"Increasing PV/YP consistent with LGS buildup "
                        f"(+{cause.values.get('delta', '?')}% over 3 days)."
                    ),
                    confidence="MEDIUM",
                ))
    return links


def _rule_weight_up_operation(events: list[Event]) -> list[CausalLink]:
    """WeightUp (N) + Weighting Agent addition (N) → same day.  HIGH.

    Note: we detect barite addition via NEW_CHEMICAL or CHEMICAL_SPIKE
    where category == 'Weighting Agent', but more reliably we check the
    timeline chemicals directly.  Since we only have events here, we look
    for new-chemical or chemical-spike events with Weighting Agent category.
    """
    links: list[CausalLink] = []
    effects = _events_of_type(events, EventType.WEIGHT_UP)
    causes = [
        e for e in events
        if e.event_type in (EventType.NEW_CHEMICAL, EventType.CHEMICAL_SPIKE)
        and e.values.get("category") == "Weighting Agent"
    ]
    for effect in effects:
        for cause in causes:
            if cause.date == effect.date:
                links.append(_link(
                    cause, effect,
                    rule="weight_up_operation",
                    explanation=(
                        f"Planned weight-up operation with "
                        f"{cause.values.get('item_name', 'weighting agent')}."
                    ),
                    confidence="HIGH",
                ))
    return links


def _rule_screen_change_preventive(events: list[Event]) -> list[CausalLink]:
    """SandIncrease (N-3..N-1) → ScreenChange (N).  3-day lookback.  MEDIUM."""
    links: list[CausalLink] = []
    causes = _events_of_type(events, EventType.SAND_INCREASE)
    effects = _events_of_type(events, EventType.SCREEN_CHANGE)
    for effect in effects:
        for cause in causes:
            cd = _parse_date(cause.date)
            ed = _parse_date(effect.date)
            # Cause must be strictly before effect, within 3 days
            if timedelta(days=1) <= (ed - cd) <= timedelta(days=3):
                links.append(_link(
                    cause, effect,
                    rule="screen_change_preventive",
                    explanation=(
                        f"Screen mesh changed in response to sand trend "
                        f"(sand increase on {cause.date})."
                    ),
                    confidence="MEDIUM",
                ))
    return links


def _rule_dilution_effective(events: list[Event]) -> list[CausalLink]:
    """Dilution (N) → RheologyShift(DOWN) (N..N+1).  1-day lookahead.  MEDIUM."""
    links: list[CausalLink] = []
    causes = _events_of_type(events, EventType.DILUTION)
    effects = [
        e for e in _events_of_type(events, EventType.RHEOLOGY_SHIFT)
        if e.values.get("direction") == "DOWN"
    ]
    for cause in causes:
        for effect in effects:
            if _in_window(cause.date, effect.date, days_back=0, days_forward=1):
                links.append(_link(
                    cause, effect,
                    rule="dilution_effective",
                    explanation="Dilution treatment successfully reduced rheology.",
                    confidence="MEDIUM",
                ))
    return links


# ── All rules ────────────────────────────────────────────────────────────────

_ALL_RULES: list[Callable[[list[Event]], list[CausalLink]]] = [
    _rule_screen_failure_from_solids,
    _rule_lgs_from_centrifuge_down,
    _rule_rheology_from_new_chemical,
    _rule_rheology_from_lgs,
    _rule_weight_up_operation,
    _rule_screen_change_preventive,
    _rule_dilution_effective,
]


def link_events(events: list[Event]) -> list[CausalLink]:
    """Apply all 7 causal rules.  Mutates events' related_events in-place.

    Returns the full list of CausalLink objects (de-duplicated by cause+effect pair).
    """
    all_links: list[CausalLink] = []
    seen_pairs: set[tuple[str, str]] = set()

    for rule_fn in _ALL_RULES:
        for link in rule_fn(events):
            pair = (link.cause_event_id, link.effect_event_id)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                all_links.append(link)

    return all_links
