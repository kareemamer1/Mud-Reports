"""Event detectors — analyse consecutive timeline days to detect anomalies.

Organised in three sections:
  1. Equipment event detectors   (§5.1)
  2. Mud property event detectors (§5.2)
  3. Inventory event detectors   (§5.3)

Each detector receives the full timeline (list[dict]) and returns list[Event].
The orchestrator `detect_all_events` calls every detector and merges results.
"""

from __future__ import annotations

from typing import Any

from backend.schemas_insights import Event, EventSeverity, EventType


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _evt_id(job: str, date: str, etype: str, detail: str = "") -> str:
    """Generate a deterministic event ID."""
    parts = [f"evt_{job}_{date}_{etype}"]
    if detail:
        parts[0] += f"_{detail}"
    return parts[0]


def _rolling_avg(values: list[float | None], window: int) -> float | None:
    """Compute rolling average of the last *window* non-None values."""
    valid = [v for v in values[-window:] if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _pct_change(prev: float | None, curr: float | None) -> float | None:
    """Percentage change from prev → curr.  Returns None if either is None or prev is 0."""
    if prev is None or curr is None or prev == 0:
        return None
    return ((curr - prev) / abs(prev)) * 100


def _get_shaker_map(equip: dict) -> dict[str, dict]:
    """Index shakers by name for stable cross-day matching."""
    return {s["name"]: s for s in equip.get("shakers", [])}


def _get_centrifuge_map(equip: dict) -> dict[str, dict]:
    return {c["name"]: c for c in equip.get("centrifuges", [])}


# ═══════════════════════════════════════════════════════════════════════════════
#  1.  EQUIPMENT EVENT DETECTORS  (§5.1)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_shaker_down(timeline: list[dict], job: str) -> list[Event]:
    """ShakerHours drops >50% from 7-day rolling average → HIGH."""
    events: list[Event] = []
    # Collect per-shaker hours history keyed by name
    shaker_history: dict[str, list[float | None]] = {}

    for i, day in enumerate(timeline):
        equip = day.get("equipment", {})
        day_shakers = _get_shaker_map(equip)

        for name, info in day_shakers.items():
            hours = info.get("hours")
            history = shaker_history.setdefault(name, [])

            if i > 0 and len(history) >= 1:
                avg = _rolling_avg(history, 7)
                if avg is not None and avg > 0 and hours is not None and hours < avg * 0.5:
                    drop_pct = round(((avg - hours) / avg) * 100, 1)
                    events.append(Event(
                        id=_evt_id(job, day["date"], "shaker_down", name.replace(" ", "")),
                        event_type=EventType.SHAKER_DOWN,
                        severity=EventSeverity.HIGH,
                        date=day["date"],
                        title=f"{name} Down",
                        description=(
                            f"{name} hours dropped to {hours}h, "
                            f"{drop_pct}% below 7-day average of {round(avg, 1)}h."
                        ),
                        values={"shaker": name, "hours": hours, "prev_avg": round(avg, 1), "drop_pct": drop_pct},
                    ))
            history.append(hours)

    return events


def detect_screen_change(timeline: list[dict], job: str) -> list[Event]:
    """ShakerSize values differ from previous day → MEDIUM."""
    events: list[Event] = []
    prev_shakers: dict[str, dict] = {}

    for i, day in enumerate(timeline):
        equip = day.get("equipment", {})
        curr_shakers = _get_shaker_map(equip)

        if i > 0:
            for name, curr in curr_shakers.items():
                prev = prev_shakers.get(name)
                if prev is None:
                    continue
                curr_mesh = curr.get("mesh", [])
                prev_mesh = prev.get("mesh", [])
                # Compare non-None mesh values
                if (curr_mesh and prev_mesh and
                        any(c is not None and p is not None and c != p
                            for c, p in zip(curr_mesh, prev_mesh))):
                    events.append(Event(
                        id=_evt_id(job, day["date"], "screen_change", name.replace(" ", "")),
                        event_type=EventType.SCREEN_CHANGE,
                        severity=EventSeverity.MEDIUM,
                        date=day["date"],
                        title=f"{name} Screen Change",
                        description=(
                            f"{name} mesh changed from {prev_mesh} to {curr_mesh}."
                        ),
                        values={"shaker": name, "prev_mesh": prev_mesh, "new_mesh": curr_mesh},
                    ))

        prev_shakers = curr_shakers

    return events


def detect_centrifuge_down(timeline: list[dict], job: str) -> list[Event]:
    """Centrifuge hours = 0 or drops >50% from 7-day avg → HIGH."""
    events: list[Event] = []
    cent_history: dict[str, list[float | None]] = {}

    for i, day in enumerate(timeline):
        equip = day.get("equipment", {})
        day_cents = _get_centrifuge_map(equip)

        for name, info in day_cents.items():
            hours = info.get("hours")
            history = cent_history.setdefault(name, [])

            if i > 0 and len(history) >= 1:
                avg = _rolling_avg(history, 7)
                if avg is not None and avg > 0:
                    if hours is not None and (hours == 0 or hours < avg * 0.5):
                        drop_pct = round(((avg - hours) / avg) * 100, 1)
                        events.append(Event(
                            id=_evt_id(job, day["date"], "centrifuge_down", name.replace(" ", "")),
                            event_type=EventType.CENTRIFUGE_DOWN,
                            severity=EventSeverity.HIGH,
                            date=day["date"],
                            title=f"{name} Down",
                            description=(
                                f"{name} hours dropped to {hours}h "
                                f"({drop_pct}% below 7-day avg of {round(avg, 1)}h)."
                            ),
                            values={"centrifuge": name, "hours": hours, "prev_avg": round(avg, 1), "drop_pct": drop_pct},
                        ))
            history.append(hours)

    return events


def detect_centrifuge_feed_change(timeline: list[dict], job: str) -> list[Event]:
    """Centrifuge feed rate changes >25% → MEDIUM."""
    events: list[Event] = []
    prev_cents: dict[str, dict] = {}

    for i, day in enumerate(timeline):
        equip = day.get("equipment", {})
        curr_cents = _get_centrifuge_map(equip)

        if i > 0:
            for name, curr in curr_cents.items():
                prev = prev_cents.get(name)
                if prev is None:
                    continue
                curr_feed = curr.get("feed_rate")
                prev_feed = prev.get("feed_rate")
                pct = _pct_change(prev_feed, curr_feed)
                if pct is not None and abs(pct) > 25:
                    events.append(Event(
                        id=_evt_id(job, day["date"], "centrifuge_feed_change", name.replace(" ", "")),
                        event_type=EventType.CENTRIFUGE_FEED_CHANGE,
                        severity=EventSeverity.MEDIUM,
                        date=day["date"],
                        title=f"{name} Feed Rate Change",
                        description=(
                            f"{name} feed rate changed from {prev_feed} to {curr_feed} "
                            f"({round(pct, 1):+}%)."
                        ),
                        values={
                            "centrifuge": name,
                            "prev_feed_rate": prev_feed,
                            "new_feed_rate": curr_feed,
                            "change_pct": round(pct, 1),
                        },
                    ))

        prev_cents = curr_cents

    return events


def detect_hydrocyclone_down(timeline: list[dict], job: str) -> list[Event]:
    """Desander/desilter hours drops >50% from 7-day avg → MEDIUM."""
    events: list[Event] = []
    history: dict[str, list[float | None]] = {}

    for i, day in enumerate(timeline):
        hydro = day.get("equipment", {}).get("hydrocyclones", {})

        for unit_name in ("desander", "desilter", "mud_cleaner"):
            unit = hydro.get(unit_name, {})
            hours = unit.get("hours")
            hist = history.setdefault(unit_name, [])

            if i > 0 and len(hist) >= 1:
                avg = _rolling_avg(hist, 7)
                if avg is not None and avg > 0 and hours is not None and hours < avg * 0.5:
                    drop_pct = round(((avg - hours) / avg) * 100, 1)
                    events.append(Event(
                        id=_evt_id(job, day["date"], "hydrocyclone_down", unit_name),
                        event_type=EventType.HYDROCYCLONE_DOWN,
                        severity=EventSeverity.MEDIUM,
                        date=day["date"],
                        title=f"{unit_name.replace('_', ' ').title()} Down",
                        description=(
                            f"{unit_name.replace('_', ' ').title()} hours dropped to {hours}h "
                            f"({drop_pct}% below 7-day avg of {round(avg, 1)}h)."
                        ),
                        values={"unit": unit_name, "hours": hours, "prev_avg": round(avg, 1), "drop_pct": drop_pct},
                    ))
            hist.append(hours)

    return events


def detect_equipment_startup(timeline: list[dict], job: str) -> list[Event]:
    """Equipment hours goes 0 → >0 → LOW."""
    events: list[Event] = []

    for i, day in enumerate(timeline):
        if i == 0:
            continue
        prev_day = timeline[i - 1]
        equip = day.get("equipment", {})
        prev_equip = prev_day.get("equipment", {})

        # Shakers
        curr_shakers = _get_shaker_map(equip)
        prev_shakers = _get_shaker_map(prev_equip)
        for name, curr in curr_shakers.items():
            prev = prev_shakers.get(name)
            if (prev and (prev.get("hours") or 0) == 0
                    and curr.get("hours") is not None and curr["hours"] > 0):
                events.append(Event(
                    id=_evt_id(job, day["date"], "equipment_startup", name.replace(" ", "")),
                    event_type=EventType.EQUIPMENT_STARTUP,
                    severity=EventSeverity.LOW,
                    date=day["date"],
                    title=f"{name} Started",
                    description=f"{name} started operating ({curr['hours']}h).",
                    values={"equipment": name, "hours": curr["hours"]},
                ))

        # Centrifuges
        curr_cents = _get_centrifuge_map(equip)
        prev_cents = _get_centrifuge_map(prev_equip)
        for name, curr in curr_cents.items():
            prev = prev_cents.get(name)
            if (prev and (prev.get("hours") or 0) == 0
                    and curr.get("hours") is not None and curr["hours"] > 0):
                events.append(Event(
                    id=_evt_id(job, day["date"], "equipment_startup", name.replace(" ", "")),
                    event_type=EventType.EQUIPMENT_STARTUP,
                    severity=EventSeverity.LOW,
                    date=day["date"],
                    title=f"{name} Started",
                    description=f"{name} started operating ({curr['hours']}h).",
                    values={"equipment": name, "hours": curr["hours"]},
                ))

        # Hydrocyclones
        hydro = equip.get("hydrocyclones", {})
        prev_hydro = prev_equip.get("hydrocyclones", {})
        for unit_name in ("desander", "desilter", "mud_cleaner"):
            curr_h = hydro.get(unit_name, {}).get("hours")
            prev_h = prev_hydro.get(unit_name, {}).get("hours")
            if (prev_h is not None and prev_h == 0
                    and curr_h is not None and curr_h > 0):
                label = unit_name.replace("_", " ").title()
                events.append(Event(
                    id=_evt_id(job, day["date"], "equipment_startup", unit_name),
                    event_type=EventType.EQUIPMENT_STARTUP,
                    severity=EventSeverity.LOW,
                    date=day["date"],
                    title=f"{label} Started",
                    description=f"{label} started operating ({curr_h}h).",
                    values={"equipment": unit_name, "hours": curr_h},
                ))

    return events


# ═══════════════════════════════════════════════════════════════════════════════
#  2.  MUD PROPERTY EVENT DETECTORS  (§5.2)
# ═══════════════════════════════════════════════════════════════════════════════

def _mp(day: dict, key: str) -> float | None:
    """Shorthand: extract a mud property value from a timeline day."""
    return day.get("mud_properties", {}).get(key)


def detect_solids_spike(timeline: list[dict], job: str) -> list[Event]:
    """Solids_Content increases >15% in 1 day → HIGH."""
    events: list[Event] = []
    for i in range(1, len(timeline)):
        prev_val = _mp(timeline[i - 1], "solids")
        curr_val = _mp(timeline[i], "solids")
        pct = _pct_change(prev_val, curr_val)
        if pct is not None and pct > 15:
            events.append(Event(
                id=_evt_id(job, timeline[i]["date"], "solids_spike"),
                event_type=EventType.SOLIDS_SPIKE,
                severity=EventSeverity.HIGH,
                date=timeline[i]["date"],
                title="Solids Spike",
                description=(
                    f"Solids content increased from {prev_val}% to {curr_val}% "
                    f"(+{round(pct, 1)}%)."
                ),
                values={"prev": prev_val, "curr": curr_val, "change_pct": round(pct, 1)},
            ))
    return events


def detect_sand_increase(timeline: list[dict], job: str) -> list[Event]:
    """Sand >0.5% or doubles → HIGH."""
    events: list[Event] = []
    for i in range(1, len(timeline)):
        prev_val = _mp(timeline[i - 1], "sand")
        curr_val = _mp(timeline[i], "sand")
        if curr_val is None:
            continue
        exceeded_abs = curr_val > 0.5
        doubled = (prev_val is not None and prev_val > 0 and curr_val >= prev_val * 2)
        if exceeded_abs or doubled:
            desc_parts = []
            if exceeded_abs:
                desc_parts.append(f"Sand content at {curr_val}% (threshold 0.5%)")
            if doubled:
                desc_parts.append(f"doubled from {prev_val}%")
            events.append(Event(
                id=_evt_id(job, timeline[i]["date"], "sand_increase"),
                event_type=EventType.SAND_INCREASE,
                severity=EventSeverity.HIGH,
                date=timeline[i]["date"],
                title="Sand Increase",
                description=". ".join(desc_parts) + ".",
                values={"prev": prev_val, "curr": curr_val, "threshold": 0.5},
            ))
    return events


def detect_lgs_creep(timeline: list[dict], job: str) -> list[Event]:
    """LGS increases >0.5% over 3 days → MEDIUM."""
    events: list[Event] = []
    for i in range(3, len(timeline)):
        curr_val = _mp(timeline[i], "lgs")
        base_val = _mp(timeline[i - 3], "lgs")
        if curr_val is not None and base_val is not None:
            delta = curr_val - base_val
            if delta > 0.5:
                events.append(Event(
                    id=_evt_id(job, timeline[i]["date"], "lgs_creep"),
                    event_type=EventType.LGS_CREEP,
                    severity=EventSeverity.MEDIUM,
                    date=timeline[i]["date"],
                    title="LGS Creep",
                    description=(
                        f"Low-gravity solids increased by {round(delta, 2)}% over 3 days "
                        f"({base_val}% → {curr_val}%)."
                    ),
                    values={"base": base_val, "curr": curr_val, "delta": round(delta, 2), "window_days": 3},
                ))
    return events


def detect_drill_solids_rise(timeline: list[dict], job: str) -> list[Event]:
    """Drill solids increases >0.3% in 1 day → MEDIUM."""
    events: list[Event] = []
    for i in range(1, len(timeline)):
        prev_val = _mp(timeline[i - 1], "drill_solids")
        curr_val = _mp(timeline[i], "drill_solids")
        if prev_val is not None and curr_val is not None:
            delta = curr_val - prev_val
            if delta > 0.3:
                events.append(Event(
                    id=_evt_id(job, timeline[i]["date"], "drill_solids_rise"),
                    event_type=EventType.DRILL_SOLIDS_RISE,
                    severity=EventSeverity.MEDIUM,
                    date=timeline[i]["date"],
                    title="Drill Solids Rise",
                    description=(
                        f"Drill solids increased by {round(delta, 2)}% in 1 day "
                        f"({prev_val}% → {curr_val}%)."
                    ),
                    values={"prev": prev_val, "curr": curr_val, "delta": round(delta, 2)},
                ))
    return events


def detect_rheology_shift(timeline: list[dict], job: str) -> list[Event]:
    """PV or YP changes >20% from 3-day avg → MEDIUM.  Tracks direction."""
    events: list[Event] = []
    pv_history: list[float | None] = []
    yp_history: list[float | None] = []

    for i, day in enumerate(timeline):
        pv = _mp(day, "pv")
        yp = _mp(day, "yp")

        if i >= 3:
            pv_avg = _rolling_avg(pv_history, 3)
            yp_avg = _rolling_avg(yp_history, 3)

            triggers: list[str] = []
            direction = None
            values: dict[str, Any] = {}

            pv_pct = _pct_change(pv_avg, pv)
            if pv_pct is not None and abs(pv_pct) > 20:
                direction = "UP" if pv_pct > 0 else "DOWN"
                triggers.append(f"PV {round(pv_pct, 1):+}% vs 3-day avg")
                values["pv"] = pv
                values["pv_avg"] = round(pv_avg, 1) if pv_avg else None
                values["pv_change_pct"] = round(pv_pct, 1)

            yp_pct = _pct_change(yp_avg, yp)
            if yp_pct is not None and abs(yp_pct) > 20:
                d = "UP" if yp_pct > 0 else "DOWN"
                if direction is None:
                    direction = d
                triggers.append(f"YP {round(yp_pct, 1):+}% vs 3-day avg")
                values["yp"] = yp
                values["yp_avg"] = round(yp_avg, 1) if yp_avg else None
                values["yp_change_pct"] = round(yp_pct, 1)

            if triggers:
                values["direction"] = direction
                events.append(Event(
                    id=_evt_id(job, day["date"], "rheology_shift"),
                    event_type=EventType.RHEOLOGY_SHIFT,
                    severity=EventSeverity.MEDIUM,
                    date=day["date"],
                    title=f"Rheology Shift ({direction})",
                    description="Rheology shift detected: " + "; ".join(triggers) + ".",
                    values=values,
                ))

        pv_history.append(pv)
        yp_history.append(yp)

    return events


def detect_weight_up(timeline: list[dict], job: str) -> list[Event]:
    """Mud weight increases >0.3 ppg → MEDIUM."""
    events: list[Event] = []
    for i in range(1, len(timeline)):
        prev_mw = _mp(timeline[i - 1], "mud_weight")
        curr_mw = _mp(timeline[i], "mud_weight")
        if prev_mw is not None and curr_mw is not None:
            delta = curr_mw - prev_mw
            if delta > 0.3:
                events.append(Event(
                    id=_evt_id(job, timeline[i]["date"], "weight_up"),
                    event_type=EventType.WEIGHT_UP,
                    severity=EventSeverity.MEDIUM,
                    date=timeline[i]["date"],
                    title="Weight Up",
                    description=(
                        f"Mud weight increased by {round(delta, 2)} ppg "
                        f"({prev_mw} → {curr_mw} ppg)."
                    ),
                    values={"prev": prev_mw, "curr": curr_mw, "delta": round(delta, 2)},
                ))
    return events


def detect_dilution(timeline: list[dict], job: str) -> list[Event]:
    """Mud weight drops AND water additions detected → LOW."""
    events: list[Event] = []
    for i in range(1, len(timeline)):
        prev_mw = _mp(timeline[i - 1], "mud_weight")
        curr_mw = _mp(timeline[i], "mud_weight")
        if prev_mw is None or curr_mw is None:
            continue
        mw_drop = prev_mw - curr_mw
        if mw_drop <= 0:
            continue

        # Check for water/base-fluid additions on this day
        water_adds = [
            c for c in timeline[i].get("chemicals", [])
            if c.get("category") == "Base Fluid"
            and c.get("add_loss", "").lower() in ("add", "mud")
            and (c.get("quantity") or 0) > 0
        ]
        if water_adds:
            total_water = sum(c.get("quantity", 0) for c in water_adds)
            events.append(Event(
                id=_evt_id(job, timeline[i]["date"], "dilution"),
                event_type=EventType.DILUTION,
                severity=EventSeverity.LOW,
                date=timeline[i]["date"],
                title="Dilution",
                description=(
                    f"Mud weight dropped {round(mw_drop, 2)} ppg ({prev_mw} → {curr_mw}) "
                    f"with {round(total_water, 1)} units of base fluid added."
                ),
                values={
                    "prev_mw": prev_mw,
                    "curr_mw": curr_mw,
                    "mw_drop": round(mw_drop, 2),
                    "water_added": round(total_water, 1),
                },
            ))
    return events


def detect_ph_shift(timeline: list[dict], job: str) -> list[Event]:
    """pH changes >0.5 units → MEDIUM."""
    events: list[Event] = []
    for i in range(1, len(timeline)):
        prev_ph = _mp(timeline[i - 1], "ph")
        curr_ph = _mp(timeline[i], "ph")
        if prev_ph is not None and curr_ph is not None:
            delta = curr_ph - prev_ph
            if abs(delta) > 0.5:
                direction = "UP" if delta > 0 else "DOWN"
                events.append(Event(
                    id=_evt_id(job, timeline[i]["date"], "ph_shift"),
                    event_type=EventType.PH_SHIFT,
                    severity=EventSeverity.MEDIUM,
                    date=timeline[i]["date"],
                    title=f"pH Shift ({direction})",
                    description=(
                        f"pH changed by {round(delta, 2)} units "
                        f"({prev_ph} → {curr_ph})."
                    ),
                    values={"prev": prev_ph, "curr": curr_ph, "delta": round(delta, 2), "direction": direction},
                ))
    return events


# ═══════════════════════════════════════════════════════════════════════════════
#  3.  INVENTORY EVENT DETECTORS  (§5.3)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_new_chemical(timeline: list[dict], job: str) -> list[Event]:
    """ItemName first appearance for this job → HIGH."""
    events: list[Event] = []
    seen: set[str] = set()

    for day in timeline:
        for chem in day.get("chemicals", []):
            item = chem.get("item")
            if not item or item in seen:
                continue
            seen.add(item)
            events.append(Event(
                id=_evt_id(job, day["date"], "new_chemical", item.replace(" ", "_")[:20]),
                event_type=EventType.NEW_CHEMICAL,
                severity=EventSeverity.HIGH,
                date=day["date"],
                title=f"New Chemical: {item}",
                description=(
                    f"First appearance of '{item}' (category: {chem.get('category', 'Unknown')}) "
                    f"— {chem.get('quantity', 0)} {chem.get('units', '')}."
                ),
                values={
                    "item_name": item,
                    "category": chem.get("category"),
                    "quantity": chem.get("quantity"),
                    "units": chem.get("units"),
                    "add_loss": chem.get("add_loss"),
                },
            ))
    return events


def detect_chemical_spike(timeline: list[dict], job: str) -> list[Event]:
    """Quantity for an item >3× its 7-day avg → MEDIUM."""
    events: list[Event] = []
    # Track per-item daily totals
    item_history: dict[str, list[float]] = {}

    for i, day in enumerate(timeline):
        # Aggregate daily totals per item
        daily_totals: dict[str, float] = {}
        for chem in day.get("chemicals", []):
            item = chem.get("item")
            qty = chem.get("quantity") or 0
            if item and chem.get("add_loss", "").lower() in ("add", "mud"):
                daily_totals[item] = daily_totals.get(item, 0) + qty

        for item, qty in daily_totals.items():
            hist = item_history.setdefault(item, [])
            if len(hist) >= 7:
                avg = _rolling_avg(hist, 7)
                if avg is not None and avg > 0 and qty > avg * 3:
                    events.append(Event(
                        id=_evt_id(job, day["date"], "chemical_spike", item.replace(" ", "_")[:20]),
                        event_type=EventType.CHEMICAL_SPIKE,
                        severity=EventSeverity.MEDIUM,
                        date=day["date"],
                        title=f"Chemical Spike: {item}",
                        description=(
                            f"'{item}' quantity ({qty}) is {round(qty / avg, 1)}× "
                            f"the 7-day average ({round(avg, 1)})."
                        ),
                        values={
                            "item_name": item,
                            "quantity": qty,
                            "avg_7d": round(avg, 1),
                            "multiple": round(qty / avg, 1),
                        },
                    ))
            hist.append(qty)

        # Pad items not seen today with 0
        for item in item_history:
            if item not in daily_totals:
                item_history[item].append(0)

    return events


def detect_large_formation_loss(timeline: list[dict], job: str) -> list[Event]:
    """Loss with category 'Downhole Loss' and qty >100 → HIGH."""
    events: list[Event] = []
    for day in timeline:
        for chem in day.get("chemicals", []):
            category = chem.get("category", "")
            add_loss = (chem.get("add_loss") or "").lower()
            qty = chem.get("quantity") or 0
            if category == "Downhole Loss" and add_loss == "loss" and qty > 100:
                events.append(Event(
                    id=_evt_id(job, day["date"], "large_formation_loss"),
                    event_type=EventType.LARGE_FORMATION_LOSS,
                    severity=EventSeverity.HIGH,
                    date=day["date"],
                    title="Large Formation Loss",
                    description=(
                        f"Formation loss of {qty} {chem.get('units', 'bbl')} detected."
                    ),
                    values={
                        "item_name": chem.get("item"),
                        "quantity": qty,
                        "units": chem.get("units"),
                    },
                ))
    return events


def detect_high_sc_removal(timeline: list[dict], job: str) -> list[Event]:
    """SC Removal losses exceed 7-day baseline → LOW (positive signal)."""
    events: list[Event] = []
    sc_history: list[float] = []

    for i, day in enumerate(timeline):
        daily_sc = sum(
            (c.get("quantity") or 0)
            for c in day.get("chemicals", [])
            if c.get("category") == "SC Removal"
        )
        if i >= 7 and daily_sc > 0:
            avg = _rolling_avg(sc_history, 7)
            if avg is not None and avg > 0 and daily_sc > avg * 1.5:
                events.append(Event(
                    id=_evt_id(job, day["date"], "high_sc_removal"),
                    event_type=EventType.HIGH_SC_REMOVAL,
                    severity=EventSeverity.LOW,
                    date=day["date"],
                    title="High SC Removal",
                    description=(
                        f"Solids control removal ({daily_sc}) exceeds "
                        f"7-day avg ({round(avg, 1)}) by {round((daily_sc / avg - 1) * 100, 1)}%."
                    ),
                    values={
                        "daily_removal": daily_sc,
                        "avg_7d": round(avg, 1),
                    },
                ))
        sc_history.append(daily_sc)

    return events


# ═══════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

_ALL_DETECTORS = [
    # Equipment
    detect_shaker_down,
    detect_screen_change,
    detect_centrifuge_down,
    detect_centrifuge_feed_change,
    detect_hydrocyclone_down,
    detect_equipment_startup,
    # Mud properties
    detect_solids_spike,
    detect_sand_increase,
    detect_lgs_creep,
    detect_drill_solids_rise,
    detect_rheology_shift,
    detect_weight_up,
    detect_dilution,
    detect_ph_shift,
    # Inventory
    detect_new_chemical,
    detect_chemical_spike,
    detect_large_formation_loss,
    detect_high_sc_removal,
]


def detect_all_events(timeline: list[dict], job: str) -> list[Event]:
    """Run all 18 detectors and return a merged, date-sorted event list."""
    all_events: list[Event] = []
    for detector in _ALL_DETECTORS:
        all_events.extend(detector(timeline, job))

    # Sort by date, then severity (HIGH first)
    severity_order = {EventSeverity.HIGH: 0, EventSeverity.MEDIUM: 1, EventSeverity.LOW: 2}
    all_events.sort(key=lambda e: (e.date, severity_order.get(e.severity, 9)))
    return all_events
