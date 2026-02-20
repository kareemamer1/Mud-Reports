"""Insights router — endpoints for job listing, summary, timeline, events, chemicals, insights, report."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.database import get_wellstar_db
from backend.models_wellstar import (
    ConcentAddLoss,
    Equipment,
    Report,
    Sample,
)
from backend.services.chemical_categorizer import categorize, categorize_batch
from backend.services.timeline import get_timeline, get_previous_day
from backend.services.event_detector import detect_all_events
from backend.services.causal_linker import link_events
from backend.services.narrative_generator import generate_insights
from backend.services.pdf_generator import generate_pdf
from backend.schemas_insights import EventSeverity

router = APIRouter()


# ── GET /api/insights/jobs ───────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(
    min_reports: int = Query(10, ge=1, description="Only include jobs with at least this many reports"),
    db: Session = Depends(get_wellstar_db),
):
    """List all jobs with basic stats. Filtered to jobs with >= min_reports reports."""
    from backend.services.timeline import parse_report_date
    from sqlalchemy.orm import aliased

    # Build subqueries for sample and chemical counts
    sample_counts = (
        db.query(
            Sample.Job.label("job"),
            func.count(Sample.ID).label("cnt"),
        )
        .group_by(Sample.Job)
        .subquery()
    )

    chem_counts = (
        db.query(
            ConcentAddLoss.Job.label("job"),
            func.count(ConcentAddLoss.ID).label("cnt"),
        )
        .group_by(ConcentAddLoss.Job)
        .subquery()
    )

    # Single query: report stats + LEFT JOIN sample & chemical counts
    rows = (
        db.query(
            Report.Job,
            func.count(Report.ID).label("report_count"),
            func.min(Report.ReportDate).label("first_date_raw"),
            func.max(Report.ReportDate).label("last_date_raw"),
            func.coalesce(sample_counts.c.cnt, 0).label("sample_count"),
            func.coalesce(chem_counts.c.cnt, 0).label("chemical_txn_count"),
        )
        .outerjoin(sample_counts, Report.Job == sample_counts.c.job)
        .outerjoin(chem_counts, Report.Job == chem_counts.c.job)
        .group_by(Report.Job)
        .having(func.count(Report.ID) >= min_reports)
        .order_by(Report.Job)
        .all()
    )

    jobs = []
    for row in rows:
        first_date = parse_report_date(row.first_date_raw)
        last_date = parse_report_date(row.last_date_raw)
        jobs.append({
            "job_id": row.Job,
            "first_date": first_date.isoformat() if first_date else row.first_date_raw,
            "last_date": last_date.isoformat() if last_date else row.last_date_raw,
            "report_count": row.report_count,
            "sample_count": row.sample_count,
            "chemical_txn_count": row.chemical_txn_count,
        })

    return {"jobs": jobs}


# ── GET /api/insights/jobs/{job_id}/summary ──────────────────────────────────

@router.get("/jobs/{job_id}/summary")
def get_job_summary(job_id: str, db: Session = Depends(get_wellstar_db)):
    """Return aggregate stats for a single job."""
    from backend.services.timeline import parse_report_date

    # Report stats
    reports = db.query(Report).filter(Report.Job == job_id).all()
    if not reports:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    dates = [parse_report_date(r.ReportDate) for r in reports]
    dates = sorted([d for d in dates if d is not None])

    max_md = max((r.MDDepth for r in reports if r.MDDepth is not None), default=None)
    max_tvd = max((r.TVDDepth for r in reports if r.TVDDepth is not None), default=None)

    engineers = list({r.Engineer for r in reports if r.Engineer})
    engineers.sort()

    # Sample count
    sample_count = (
        db.query(func.count(Sample.ID))
        .filter(Sample.Job == job_id)
        .scalar()
    ) or 0

    # Equipment day count
    equipment_count = (
        db.query(func.count(Equipment.ID))
        .filter(Equipment.Job == job_id)
        .scalar()
    ) or 0

    # Chemical stats
    chemical_txn_count = (
        db.query(func.count(ConcentAddLoss.ID))
        .filter(ConcentAddLoss.Job == job_id)
        .scalar()
    ) or 0

    unique_chemicals = (
        db.query(func.count(func.distinct(ConcentAddLoss.ItemName)))
        .filter(ConcentAddLoss.Job == job_id)
        .scalar()
    ) or 0

    # Mud type from CircData
    from backend.models_wellstar import CircData
    mud_type_row = (
        db.query(CircData.MudVol_MudType)
        .filter(CircData.Job == job_id, CircData.MudVol_MudType.isnot(None))
        .first()
    )

    return {
        "job_id": job_id,
        "first_date": dates[0].isoformat() if dates else None,
        "last_date": dates[-1].isoformat() if dates else None,
        "total_days": len(dates),
        "max_depth_md": max_md,
        "max_depth_tvd": max_tvd,
        "mud_type": mud_type_row[0] if mud_type_row else None,
        "unique_chemicals": unique_chemicals,
        "total_samples": sample_count,
        "equipment_days": equipment_count,
        "chemical_transactions": chemical_txn_count,
        "engineers": engineers,
    }


# ── GET /api/insights/jobs/{job_id}/timeline ─────────────────────────────────

@router.get("/jobs/{job_id}/timeline")
def get_job_timeline(
    job_id: str,
    start: str | None = Query(None, description="Start date (ISO, inclusive)"),
    end: str | None = Query(None, description="End date (ISO, inclusive)"),
    db: Session = Depends(get_wellstar_db),
):
    """Return daily timeline data for a job."""
    timeline = get_timeline(db, job_id, start_date=start, end_date=end)
    return {"job_id": job_id, "days": len(timeline), "timeline": timeline}


# ── GET /api/insights/jobs/{job_id}/events ────────────────────────────────────

@router.get("/jobs/{job_id}/events")
def get_job_events(
    job_id: str,
    start: str | None = Query(None, description="Start date (ISO, inclusive)"),
    end: str | None = Query(None, description="End date (ISO, inclusive)"),
    severity: str | None = Query(None, description="Filter by severity: high, medium, low"),
    db: Session = Depends(get_wellstar_db),
):
    """Detect and return events for a job with causal links."""
    # Get full timeline (detectors need complete history for rolling avgs)
    timeline = get_timeline(db, job_id)

    # Run all 18 detectors
    events = detect_all_events(timeline, job_id)

    # Apply causal linking
    causal_links = link_events(events)

    # Apply filters on the output (after detection uses full history)
    if start:
        events = [e for e in events if e.date >= start]
        causal_links = [
            cl for cl in causal_links
            if any(e.id in (cl.cause_event_id, cl.effect_event_id) for e in events)
        ]
    if end:
        events = [e for e in events if e.date <= end]
        causal_links = [
            cl for cl in causal_links
            if any(e.id in (cl.cause_event_id, cl.effect_event_id) for e in events)
        ]
    if severity:
        try:
            sev = EventSeverity(severity.lower())
            events = [e for e in events if e.severity == sev]
            event_ids = {e.id for e in events}
            causal_links = [
                cl for cl in causal_links
                if cl.cause_event_id in event_ids or cl.effect_event_id in event_ids
            ]
        except ValueError:
            pass  # Invalid severity value — ignore filter

    return {
        "events": [e.model_dump() for e in events],
        "causal_links": [cl.model_dump() for cl in causal_links],
        "total": len(events),
        "filters": {"start": start, "end": end, "severity": severity},
    }


# ── GET /api/insights/jobs/{job_id}/chemicals/new ─────────────────────────────

@router.get("/jobs/{job_id}/chemicals/new")
def get_new_chemicals(
    job_id: str,
    db: Session = Depends(get_wellstar_db),
):
    """Return first-appearance date for each unique chemical in the job."""
    from backend.services.timeline import parse_report_date

    # Query all chemical transactions for this job, ordered by date
    rows = (
        db.query(ConcentAddLoss)
        .filter(ConcentAddLoss.Job == job_id)
        .all()
    )

    # Find first appearance of each ItemName
    first_seen: dict[str, dict] = {}
    for row in rows:
        item = row.ItemName
        if not item:
            continue
        d = parse_report_date(row.ReportDate)
        if d is None:
            continue
        if item not in first_seen or d < first_seen[item]["_date"]:
            first_seen[item] = {
                "_date": d,
                "item_name": item,
                "category": categorize(item),
                "first_date": d.isoformat(),
                "first_quantity": row.Quantity,
                "units": row.RepUnits,
            }

    chemicals = sorted(first_seen.values(), key=lambda x: x["first_date"])
    # Remove internal _date key
    for c in chemicals:
        c.pop("_date", None)

    return {
        "job_id": job_id,
        "new_chemicals": chemicals,
        "total": len(chemicals),
    }


# ── GET /api/insights/jobs/{job_id}/insights/{date} ──────────────────────────

@router.get("/jobs/{job_id}/insights/{date}")
def get_job_insights(
    job_id: str,
    date: str,
    db: Session = Depends(get_wellstar_db),
):
    """Return plain-English insights + recommendations for a specific date."""
    # Full timeline needed for event detection rolling windows
    timeline = get_timeline(db, job_id)

    if not timeline:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No timeline data for job '{job_id}'")

    # Find the target day and previous day
    target_day = None
    for day in timeline:
        if day["date"] == date:
            target_day = day
            break

    if target_day is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No data for date '{date}' in job '{job_id}'")

    prev_day = get_previous_day(timeline, date)

    # Run event detection and causal linking on full history
    all_events = detect_all_events(timeline, job_id)
    all_links = link_events(all_events)

    # Filter events to the target date
    day_events = [e for e in all_events if e.date == date]
    # Keep causal links that touch our day's events
    day_event_ids = {e.id for e in day_events}
    day_links = [
        cl for cl in all_links
        if cl.cause_event_id in day_event_ids or cl.effect_event_id in day_event_ids
    ]

    # Generate narratives
    result = generate_insights(date, day_events, day_links, target_day, prev_day)
    return result


# ── GET /api/insights/jobs/{job_id}/report/{date} ─────────────────────────────

@router.get("/jobs/{job_id}/report/{date}")
def get_job_report(
    job_id: str,
    date: str,
    format: str = Query("json", description="Output format: json or pdf"),
    shift: str = Query("day", description="Shift: day, evening, or night"),
    db: Session = Depends(get_wellstar_db),
):
    """Generate a shift handover report in JSON or PDF format."""
    # Validate shift
    if shift not in ("day", "evening", "night"):
        shift = "day"

    # Full timeline
    timeline = get_timeline(db, job_id)

    if not timeline:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No timeline data for job '{job_id}'")

    target_day = None
    for day in timeline:
        if day["date"] == date:
            target_day = day
            break

    if target_day is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No data for date '{date}' in job '{job_id}'")

    prev_day = get_previous_day(timeline, date)

    # Events + insights
    all_events = detect_all_events(timeline, job_id)
    all_links = link_events(all_events)
    day_events = [e for e in all_events if e.date == date]
    day_event_ids = {e.id for e in day_events}
    day_links = [
        cl for cl in all_links
        if cl.cause_event_id in day_event_ids or cl.effect_event_id in day_event_ids
    ]
    insights_data = generate_insights(date, day_events, day_links, target_day, prev_day)

    if format.lower() == "pdf":
        pdf_bytes = generate_pdf(
            job_id=job_id,
            target_date=date,
            shift=shift,
            timeline_day=target_day,
            prev_day=prev_day,
            insights_data=insights_data,
        )
        filename = f"shift_report_{job_id}_{date}_{shift}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # JSON format — include shift-specific mud props
    mud_by_shift = target_day.get("mud_properties_by_shift", {})
    shift_props = mud_by_shift.get(shift)
    if not shift_props or shift_props.get("samples_count", 0) == 0:
        shift_props = target_day.get("mud_properties", {})

    return {
        "job_id": job_id,
        "date": date,
        "shift": shift,
        "engineer": target_day.get("engineer"),
        "activity": target_day.get("activity"),
        "depth_md": target_day.get("depth_md"),
        "equipment": target_day.get("equipment"),
        "mud_properties_shift": shift_props,
        "mud_properties_daily": target_day.get("mud_properties"),
        "chemicals": target_day.get("chemicals"),
        "volumes": target_day.get("volumes"),
        "remarks": target_day.get("remarks"),
        "insights": insights_data,
    }
