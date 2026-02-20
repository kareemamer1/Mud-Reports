"""Narrative generator — converts events + causal links into plain-English insights.

Template-based: one narrative template per EventType, filled from event.values.
Causal links inject "Likely caused by …" sentences.  Shift notes summarise
mud properties per shift.  Recommendations are directional (not prescriptive).
"""

from __future__ import annotations

from typing import Any

from backend.schemas_insights import CausalLink, Event, EventSeverity, EventType


# ═══════════════════════════════════════════════════════════════════════════════
#  Narrative templates  (one per EventType)
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATES: dict[str, dict[str, str]] = {
    # ── Equipment ────────────────────────────────────────────────────────
    "shaker_down": {
        "title": "Shaker Underperformance",
        "narrative": (
            "{shaker} hours dropped to {hours}h, {drop_pct}% below the "
            "7-day average of {prev_avg}h."
        ),
        "recommendation": (
            "Inspect {shaker} screens for blinding or damage. "
            "If hours remain low, consider a screen change or equipment review."
        ),
    },
    "screen_change": {
        "title": "Screen Mesh Change",
        "narrative": (
            "{shaker} mesh changed from {prev_mesh} to {new_mesh}."
        ),
        "recommendation": (
            "Monitor shaker performance for improved solids removal with the new mesh configuration."
        ),
    },
    "centrifuge_down": {
        "title": "Centrifuge Downtime",
        "narrative": (
            "{centrifuge} hours dropped to {hours}h, {drop_pct}% below the "
            "7-day average of {prev_avg}h."
        ),
        "recommendation": (
            "Check centrifuge for mechanical issues. Monitor LGS levels \u2014 "
            "reduced centrifuge capacity may cause LGS accumulation."
        ),
    },
    "centrifuge_feed_change": {
        "title": "Centrifuge Feed Rate Change",
        "narrative": (
            "Centrifuge feed rate changed ({change_pct}% change)."
        ),
        "recommendation": (
            "Verify the feed rate adjustment is producing the desired separation. "
            "Monitor overflow and underflow quality."
        ),
    },
    "hydrocyclone_down": {
        "title": "Hydrocyclone Downtime",
        "narrative": (
            "{equipment} hours dropped to {hours}h, {drop_pct}% below the "
            "7-day average of {prev_avg}h."
        ),
        "recommendation": (
            "Inspect {equipment} cones for plugging or wear. "
            "Reduced hydrocyclone time may impact fine solids removal."
        ),
    },
    "equipment_startup": {
        "title": "Equipment Started",
        "narrative": "{equipment} was brought online ({hours}h recorded).",
        "recommendation": (
            "Verify {equipment} is operating within expected parameters after startup."
        ),
    },

    # ── Mud Properties ───────────────────────────────────────────────────
    "solids_spike": {
        "title": "Solids Content Spike",
        "narrative": (
            "Total solids increased {change_pct}% in one day "
            "(from {prev}% to {curr}%)."
        ),
        "recommendation": (
            "Increase solids-control equipment run time. "
            "If drilling rate is high, consider additional centrifuge capacity."
        ),
    },
    "sand_increase": {
        "title": "Sand Content Increase",
        "narrative": "Sand content reached {curr}% (previous: {prev}%).",
        "recommendation": (
            "Check shaker screen integrity — elevated sand indicates "
            "possible screen bypass or coarser formation."
        ),
    },
    "lgs_creep": {
        "title": "Low-Gravity Solids Creep",
        "narrative": (
            "LGS increased by {delta}% over the last {window_days} days "
            "(from {base}% to {curr}%)."
        ),
        "recommendation": (
            "Increase centrifuge feed rate or runtime to manage LGS build-up. "
            "Consider adding a second centrifuge if available."
        ),
    },
    "drill_solids_rise": {
        "title": "Drill Solids Rise",
        "narrative": (
            "Drill solids rose from {prev}% to {curr}% in one day "
            "(+{delta}%)."
        ),
        "recommendation": (
            "Evaluate ROP vs. solids-control capacity. "
            "Optimize centrifuge and shaker settings to manage drill solids."
        ),
    },
    "rheology_shift": {
        "title": "Rheology Shift",
        "narrative": (
            "Rheology shifted {direction}: PV {pv} cP (avg {pv_avg}), "
            "YP {yp} (avg {yp_avg})."
        ),
        "recommendation": (
            "Monitor rheology trend. If PV continues {dir_verb}, "
            "evaluate dilution or chemical treatment."
        ),
    },
    "weight_up": {
        "title": "Mud Weight Increase",
        "narrative": (
            "Mud weight increased from {prev} to {curr} ppg "
            "(+{delta} ppg)."
        ),
        "recommendation": (
            "Confirm weight-up was planned. Monitor equivalent circulating density (ECD) "
            "and hole-cleaning efficiency at the new weight."
        ),
    },
    "dilution": {
        "title": "Dilution Treatment",
        "narrative": (
            "Mud weight decreased from {prev} to {curr} ppg with simultaneous "
            "water addition detected."
        ),
        "recommendation": (
            "Check post-dilution rheology. Verify mud weight and solids are "
            "trending toward target."
        ),
    },
    "ph_shift": {
        "title": "pH Shift",
        "narrative": (
            "pH changed from {prev} to {curr} ({delta} units)."
        ),
        "recommendation": (
            "Review chemical additions that may have affected pH. "
            "Ensure pH remains within the target range (9.0\u201310.5)."
        ),
    },

    # ── Inventory ────────────────────────────────────────────────────────
    "new_chemical": {
        "title": "New Chemical Introduced",
        "narrative": (
            "'{item_name}' ({category}) was used for the first time on this job "
            "({quantity} {units})."
        ),
        "recommendation": (
            "Monitor mud properties over the next 1\u20132 days for impact from "
            "the new chemical addition."
        ),
    },
    "chemical_spike": {
        "title": "Chemical Usage Spike",
        "narrative": (
            "'{item_name}' usage spiked to {quantity}, "
            "{multiple}\u00d7 the 7-day average of {avg_7d}."
        ),
        "recommendation": (
            "Verify the high usage was intentional. Check for any correlation "
            "with mud property changes."
        ),
    },
    "large_formation_loss": {
        "title": "Large Formation Loss",
        "narrative": (
            "Formation loss of {quantity} {units} recorded — "
            "exceeds 100 bbl threshold."
        ),
        "recommendation": (
            "Evaluate lost circulation material (LCM) pill. "
            "Monitor pit levels and maintain adequate reserves."
        ),
    },
    "high_sc_removal": {
        "title": "High Solids-Control Removal",
        "narrative": (
            "Solids-control equipment removed {daily_removal}, "
            "above the 7-day baseline of {avg_7d}."
        ),
        "recommendation": (
            "Positive signal — equipment is actively removing solids. "
            "Verify removal volume matches centrifuge/screen discharge estimates."
        ),
    },
}

# Fallback template for any unmapped event type
_FALLBACK = {
    "title": "Event Detected",
    "narrative": "{description}",
    "recommendation": "Review the event data and take appropriate action.",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Shift note builder
# ═══════════════════════════════════════════════════════════════════════════════

_SHIFT_PROP_LABELS = [
    ("mud_weight", "MW", "ppg"),
    ("pv", "PV", "cP"),
    ("yp", "YP", "lb"),
    ("solids", "Solids", "%"),
    ("sand", "Sand", "%"),
    ("lgs", "LGS", "%"),
    ("ph", "pH", ""),
]


def _build_shift_note(shift_props: dict[str, Any] | None, shift_name: str) -> str:
    """Build a one-line narrative for a shift's mud properties."""
    if not shift_props or shift_props.get("samples_count", 0) == 0:
        return f"No samples recorded during {shift_name} shift."

    parts: list[str] = []
    for key, label, unit in _SHIFT_PROP_LABELS:
        val = shift_props.get(key)
        if val is not None:
            parts.append(f"{label} {val}{' ' + unit if unit else ''}")
    count = shift_props.get("samples_count", 0)
    summary = ", ".join(parts[:5])  # limit to 5 props for brevity
    return f"{shift_name.capitalize()} shift ({count} sample{'s' if count != 1 else ''}): {summary}."


# ═══════════════════════════════════════════════════════════════════════════════
#  Main generator
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_format(template: str, values: dict[str, Any]) -> str:
    """Format template with values, gracefully handling missing keys."""
    try:
        return template.format(**values)
    except (KeyError, ValueError, IndexError):
        # If template has keys not in values, do a partial fill
        result = template
        for k, v in values.items():
            result = result.replace("{" + k + "}", str(v))
        return result


def _get_causal_text(
    event: Event,
    causal_links: list[CausalLink],
) -> str | None:
    """Find causal explanations where this event is the effect."""
    causes = [
        cl for cl in causal_links
        if cl.effect_event_id == event.id
    ]
    if not causes:
        return None
    # Take the highest-confidence cause
    causes.sort(key=lambda c: (0 if c.confidence == "HIGH" else 1))
    return f"Likely cause: {causes[0].explanation}"


def generate_insights(
    target_date: str,
    events: list[Event],
    causal_links: list[CausalLink],
    timeline_day: dict[str, Any],
    prev_day: dict[str, Any] | None,
) -> dict[str, Any]:
    """Generate structured narratives for a single day.

    Args:
        target_date: ISO date string.
        events: Events for this date (already filtered).
        causal_links: All causal links (will be filtered to relevant ones).
        timeline_day: Timeline dict for *target_date*.
        prev_day: Timeline dict for the previous day (for delta context).

    Returns:
        Dict matching the InsightsResponse schema.
    """
    # Sort events: HIGH first, then MEDIUM, then LOW
    _sev_order = {EventSeverity.HIGH: 0, EventSeverity.MEDIUM: 1, EventSeverity.LOW: 2}
    day_events = sorted(events, key=lambda e: (_sev_order.get(e.severity, 9), e.date))

    insights: list[dict[str, Any]] = []

    for evt in day_events:
        tmpl = _TEMPLATES.get(evt.event_type.value, _FALLBACK)

        # Merge event.values with extra fields the template might need
        fill = {**evt.values, "description": evt.description}

        # For rheology_shift, add direction verb
        if evt.event_type == EventType.RHEOLOGY_SHIFT:
            direction = evt.values.get("direction", "")
            fill["dir_verb"] = "increasing" if direction == "UP" else "decreasing"

        narrative_text = _safe_format(tmpl["narrative"], fill)
        rec_text = _safe_format(tmpl["recommendation"], fill)

        causal_text = _get_causal_text(evt, causal_links)

        insights.append({
            "severity": evt.severity.value,
            "title": _safe_format(tmpl["title"], fill),
            "narrative": narrative_text,
            "cause": causal_text,
            "recommendation": rec_text,
            "event_type": evt.event_type.value,
            "values": evt.values,
        })

    # ── Shift notes ──────────────────────────────────────────────────────
    mud_by_shift = timeline_day.get("mud_properties_by_shift", {})
    shift_notes = {}
    for shift_key in ("day", "evening", "night"):
        shift_props = mud_by_shift.get(shift_key)
        shift_notes[shift_key] = _build_shift_note(shift_props, shift_key)

    # ── Recommendations (aggregated, de-duplicated, top 5) ───────────────
    seen_recs: set[str] = set()
    recs: list[str] = []
    for ins in insights:
        rec = ins["recommendation"]
        if rec and rec not in seen_recs:
            seen_recs.add(rec)
            recs.append(rec)
    recs = recs[:5]

    # ── Summary ──────────────────────────────────────────────────────────
    if not day_events:
        summary = ("Normal operations. All equipment and mud properties "
                   "within expected parameters.")
    else:
        high_count = sum(1 for e in day_events if e.severity == EventSeverity.HIGH)
        total = len(day_events)
        severity_text = f"{high_count} high-severity" if high_count else ""
        summary_parts = [f"{total} event{'s' if total != 1 else ''} detected"]
        if severity_text:
            summary_parts.append(f"including {severity_text}")
        # Mention the most notable event
        top_evt = day_events[0]
        summary_parts.append(f"— {top_evt.title}")
        summary = " ".join(summary_parts) + "."

    return {
        "date": target_date,
        "summary": summary,
        "insights": insights,
        "shift_notes": shift_notes,
        "recommendations": recs,
    }
