"""Timeline aggregator — joins 5 Wellstar tables into structured daily summaries."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, time
from typing import Any

from sqlalchemy.orm import Session

from backend.models_wellstar import (
    CircData,
    ConcentAddLoss,
    Equipment,
    Report,
    Sample,
)
from backend.services.chemical_categorizer import categorize


# ── Date / time parsing helpers ──────────────────────────────────────────────

_DATE_PATTERNS = [
    re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})"),  # M/D/YYYY ...
]


def parse_report_date(raw: str | None) -> date | None:
    """Parse Wellstar ReportDate string → Python date.

    Typical format: "1/15/2018 12:00:00 AM"
    """
    if not raw or not raw.strip():
        return None
    for pat in _DATE_PATTERNS:
        m = pat.match(raw.strip())
        if m:
            try:
                return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            except ValueError:
                continue
    return None


def parse_sample_time(raw: str | None) -> time | None:
    """Extract time-of-day from SampleTime OLE date string.

    Typical format: "12/30/1899 9:00:00 AM"
    The date portion is the OLE epoch and should be ignored.
    """
    if not raw or not raw.strip():
        return None
    # Try to grab the time portion after the date
    parts = raw.strip().split(" ", 1)
    if len(parts) < 2:
        return None
    time_str = parts[1]  # e.g. "9:00:00 AM" or "14:00:00"
    for fmt in ("%I:%M:%S %p", "%H:%M:%S", "%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def assign_shift(t: time | None) -> str:
    """Assign a shift label based on time of day.

    Day:     06:00 – 13:59
    Evening: 14:00 – 21:59
    Night:   22:00 – 05:59
    """
    if t is None:
        return "unknown"
    if time(6, 0) <= t < time(14, 0):
        return "day"
    elif time(14, 0) <= t < time(22, 0):
        return "evening"
    else:
        return "night"


# ── Value parsing helpers ────────────────────────────────────────────────────

def parse_sand_content(raw: Any) -> float | None:
    """Parse Sand_Content which may use comma as decimal separator."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s:
        return None
    # Replace comma decimal with dot
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def safe_float(val: Any) -> float | None:
    """Convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val: Any) -> int | None:
    """Convert a value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ── Mud properties averaging ─────────────────────────────────────────────────

_MUD_PROP_FIELDS = [
    ("mud_weight", "MudWeight_PPG"),
    ("pv", "Plastic_Viscosity"),
    ("yp", "Yield_Point"),
    ("gel_10s", "Gel_Strength10sec"),
    ("gel_10m", "Gel_Strength10min"),
    ("gel_30m", "Gel_Strength30min"),
    ("solids", "Solids_Content"),
    ("lgs", "SolidsPct_GravLow"),
    ("hgs", "SolidsPct_GravHigh"),
    ("drill_solids", "SolidsPct_DrillSolids"),
    ("ph", "PH"),
    ("chloride", "Chloride"),
    ("filtrate", "Filtrate_API"),
    ("oil_ratio", "Oil_Ratio"),
    ("es", "ElectricalStability"),
]


def _average_mud_props(samples: list[Sample]) -> dict[str, Any]:
    """Average mud property fields across a set of samples."""
    if not samples:
        return {key: None for key, _ in _MUD_PROP_FIELDS}

    result: dict[str, Any] = {}
    for key, attr in _MUD_PROP_FIELDS:
        values = [safe_float(getattr(s, attr, None)) for s in samples]
        values = [v for v in values if v is not None]
        result[key] = round(sum(values) / len(values), 2) if values else None

    # Sand_Content handled separately (comma-decimal parsing)
    sand_vals = [parse_sand_content(s.Sand_Content) for s in samples]
    sand_vals = [v for v in sand_vals if v is not None]
    result["sand"] = round(sum(sand_vals) / len(sand_vals), 3) if sand_vals else None

    result["samples_count"] = len(samples)
    return result


# ── Equipment extraction ─────────────────────────────────────────────────────

def _extract_equipment(row: Equipment | None) -> dict[str, Any]:
    """Build equipment dict from an Equipment row."""
    if row is None:
        return {"shakers": [], "centrifuges": [], "hydrocyclones": {}}

    shakers = []
    for i in range(1, 6):
        hours = safe_float(getattr(row, f"ShakerHours{i}", None))
        name = getattr(row, f"ShakerName{i}", None) or f"Shaker {i}"
        mesh = [
            safe_float(getattr(row, f"ShakerSize{i}_{j}", None))
            for j in range(1, 5)
        ]
        # Only include shakers that have hours data or mesh data
        if hours is not None or any(m is not None for m in mesh):
            shakers.append({
                "name": name,
                "hours": hours,
                "mesh": mesh,
            })

    centrifuges = []
    for i in range(1, 4):
        hours = safe_float(getattr(row, f"Centrifuge{i}_Hours", None))
        c_type = getattr(row, f"Centrifuge{i}_Type", None)
        feed = safe_float(getattr(row, f"Centrifuge{i}_FeedRate", None))
        name = getattr(row, f"Centrifuge{i}Name", None) or f"Centrifuge {i}"
        if hours is not None or c_type:
            centrifuges.append({
                "name": name,
                "hours": hours,
                "feed_rate": feed,
                "type": c_type,
            })

    hydrocyclones = {
        "desander": {
            "hours": safe_float(row.DesanderHours),
            "size": safe_float(row.Desander_Size),
            "cones": safe_int(row.Desander_Cones),
        },
        "desilter": {
            "hours": safe_float(row.DesilterHours),
            "size": safe_float(row.Desilter_Size),
            "cones": safe_int(row.Desilter_Cones),
        },
        "mud_cleaner": {
            "hours": safe_float(row.MudCleanerHours),
            "size": safe_float(row.MudCleaner_Size),
            "cones": safe_int(row.MudCleaner_Cones),
        },
    }

    return {
        "shakers": shakers,
        "centrifuges": centrifuges,
        "hydrocyclones": hydrocyclones,
    }


# ── Main timeline function ───────────────────────────────────────────────────

def get_timeline(
    db: Session,
    job_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Build a daily timeline for a job by joining all 5 Wellstar tables.

    Args:
        db: Wellstar database session.
        job_id: The Job identifier (e.g. "TK021").
        start_date: Optional ISO date string to filter from (inclusive).
        end_date: Optional ISO date string to filter to (inclusive).

    Returns:
        List of daily summary dicts, sorted by date ascending.
    """
    # ── Fetch all data for this job ──────────────────────────────────────
    equipment_rows = db.query(Equipment).filter(Equipment.Job == job_id).all()
    sample_rows = db.query(Sample).filter(Sample.Job == job_id).all()
    chemical_rows = db.query(ConcentAddLoss).filter(ConcentAddLoss.Job == job_id).all()
    report_rows = db.query(Report).filter(Report.Job == job_id).all()
    circ_rows = db.query(CircData).filter(CircData.Job == job_id).all()

    # ── Index by parsed date ─────────────────────────────────────────────
    equip_by_date: dict[date, Equipment] = {}
    for row in equipment_rows:
        d = parse_report_date(row.ReportDate)
        if d:
            equip_by_date[d] = row  # One row per job+date

    samples_by_date: dict[date, list[Sample]] = defaultdict(list)
    for row in sample_rows:
        d = parse_report_date(row.ReportDate)
        if d:
            samples_by_date[d].append(row)

    chems_by_date: dict[date, list[ConcentAddLoss]] = defaultdict(list)
    for row in chemical_rows:
        d = parse_report_date(row.ReportDate)
        if d:
            chems_by_date[d].append(row)

    reports_by_date: dict[date, Report] = {}
    for row in report_rows:
        d = parse_report_date(row.ReportDate)
        if d:
            reports_by_date[d] = row

    circ_by_date: dict[date, CircData] = {}
    for row in circ_rows:
        d = parse_report_date(row.ReportDate)
        if d:
            circ_by_date[d] = row

    # ── Collect all dates ────────────────────────────────────────────────
    all_dates = sorted(
        set(equip_by_date)
        | set(samples_by_date)
        | set(chems_by_date)
        | set(reports_by_date)
        | set(circ_by_date)
    )

    # ── Apply date filters ───────────────────────────────────────────────
    if start_date:
        try:
            sd = date.fromisoformat(start_date)
            all_dates = [d for d in all_dates if d >= sd]
        except ValueError:
            pass
    if end_date:
        try:
            ed = date.fromisoformat(end_date)
            all_dates = [d for d in all_dates if d <= ed]
        except ValueError:
            pass

    # ── Build daily summaries ────────────────────────────────────────────
    timeline: list[dict[str, Any]] = []

    for d in all_dates:
        report = reports_by_date.get(d)
        equip = equip_by_date.get(d)
        day_samples = samples_by_date.get(d, [])
        day_chems = chems_by_date.get(d, [])
        circ = circ_by_date.get(d)

        # Mud properties — overall daily average
        mud_props = _average_mud_props(day_samples)

        # Mud properties — by shift
        shift_buckets: dict[str, list[Sample]] = defaultdict(list)
        for s in day_samples:
            shift = assign_shift(parse_sample_time(s.SampleTime))
            shift_buckets[shift].append(s)
        mud_by_shift = {
            shift: _average_mud_props(shift_samples)
            for shift, shift_samples in shift_buckets.items()
        }

        # Chemicals
        chemicals = []
        for c in day_chems:
            chemicals.append({
                "item": c.ItemName,
                "add_loss": c.AddLoss,
                "quantity": safe_float(c.Quantity),
                "units": c.RepUnits,
                "category": categorize(c.ItemName),
            })

        # Volumes from CircData
        volumes = None
        if circ:
            volumes = {
                "total_circ": safe_float(circ.MudVol_totalcirc),
                "pits": safe_float(circ.MudVol_Pits),
                "in_storage": safe_float(circ.MudVol_InStorage),
                "mud_type": circ.MudVol_MudType,
            }

        entry: dict[str, Any] = {
            "date": d.isoformat(),
            "depth_md": safe_float(report.MDDepth) if report else None,
            "depth_tvd": safe_float(report.TVDDepth) if report else None,
            "activity": report.PresentActivity if report else None,
            "equipment": _extract_equipment(equip),
            "mud_properties": mud_props,
            "mud_properties_by_shift": mud_by_shift,
            "chemicals": chemicals,
            "volumes": volumes,
            "remarks": report.Remarks if report else None,
            "engineer": report.Engineer if report else None,
        }
        timeline.append(entry)

    return timeline


# ── Helpers for Phase 3 (Narrative / PDF) ────────────────────────────────────

SHIFT_LABELS = {
    "day": "Day (06:00\u201314:00)",
    "evening": "Evening (14:00\u201322:00)",
    "night": "Night (22:00\u201306:00)",
    "unknown": "Unknown Shift",
}


def get_shift_label(shift: str) -> str:
    """Return human-readable shift label."""
    return SHIFT_LABELS.get(shift, shift)


def get_previous_day(timeline: list[dict[str, Any]], target_date: str) -> dict[str, Any] | None:
    """Return the timeline entry for the day before *target_date*, or None."""
    for i, day in enumerate(timeline):
        if day["date"] == target_date and i > 0:
            return timeline[i - 1]
    return None
