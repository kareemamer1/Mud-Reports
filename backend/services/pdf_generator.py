"""PDF generator — renders a 2-page shift handover report using reportlab.

Layout follows wireframe §4.2:
  Page 1: Header → Equipment Summary → Mud Properties → Key Insights
  Page 2: Chemical Inventory → Volume Accounting → Recommendations → Remarks → Footer
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.services.timeline import get_shift_label


# ═══════════════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════════════

_VERSION = "1.0"

# Status thresholds for equipment (hours vs 7-day avg)
_STATUS_OK = "[OK]"
_STATUS_WARN = "[WARN]"
_STATUS_CRIT = "[CRIT]"
_STATUS_OFF = "[OFF]"

# Colours
_CLR_GREEN = colors.Color(0.13, 0.55, 0.13)     # dark green
_CLR_ORANGE = colors.Color(0.85, 0.55, 0.0)     # orange
_CLR_RED = colors.Color(0.80, 0.10, 0.10)        # red
_CLR_GREY = colors.Color(0.55, 0.55, 0.55)       # grey
_CLR_HEADER_BG = colors.Color(0.12, 0.18, 0.28)  # dark navy
_CLR_HEADER_FG = colors.white
_CLR_ROW_ALT = colors.Color(0.95, 0.95, 0.97)    # light blue-grey
_CLR_SECTION_BG = colors.Color(0.20, 0.30, 0.45) # section header

# WBM default target ranges
_TARGETS: dict[str, tuple[str, str]] = {
    "mud_weight": ("8.5 - 9.0", "ppg"),
    "pv":         ("8 - 15", "cP"),
    "yp":         ("30 - 50", "lb"),
    "gel_10s":    ("15 - 35", "lb"),
    "solids":     ("< 5", "%"),
    "sand":       ("< 0.5", "%"),
    "lgs":        ("< 4", "%"),
    "hgs":        ("\u2014", "%"),
    "drill_solids": ("< 3", "%"),
    "ph":         ("9.0 - 10.5", ""),
    "filtrate":   ("< 15", "ml"),
}

_PROP_LABELS: dict[str, str] = {
    "mud_weight": "Mud Weight",
    "pv": "PV",
    "yp": "YP",
    "gel_10s": "Gel 10s",
    "gel_10m": "Gel 10m",
    "solids": "Total Solids",
    "sand": "Sand",
    "lgs": "LGS",
    "hgs": "HGS",
    "drill_solids": "Drill Solids",
    "ph": "pH",
    "chloride": "Chloride",
    "filtrate": "Filtrate API",
    "oil_ratio": "Oil Ratio",
    "es": "Elec. Stability",
}

# Mud property keys to display in the PDF table (ordered)
_DISPLAY_PROPS = [
    "mud_weight", "pv", "yp", "gel_10s", "solids", "sand",
    "lgs", "hgs", "drill_solids", "ph", "filtrate",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Custom styles
# ═══════════════════════════════════════════════════════════════════════════════

def _get_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PDFTitle", parent=base["Title"],
            fontSize=16, spaceAfter=4, textColor=_CLR_HEADER_BG,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "PDFSubtitle", parent=base["Normal"],
            fontSize=10, spaceAfter=6, textColor=colors.grey,
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "PDFSection", parent=base["Heading2"],
            fontSize=11, spaceBefore=10, spaceAfter=4,
            textColor=_CLR_HEADER_BG,
        ),
        "body": ParagraphStyle(
            "PDFBody", parent=base["Normal"],
            fontSize=9, leading=12,
        ),
        "body_small": ParagraphStyle(
            "PDFBodySmall", parent=base["Normal"],
            fontSize=8, leading=10,
        ),
        "insight_high": ParagraphStyle(
            "InsightHigh", parent=base["Normal"],
            fontSize=9, leading=12, textColor=_CLR_RED,
            leftIndent=8, spaceBefore=2, spaceAfter=2,
        ),
        "insight_med": ParagraphStyle(
            "InsightMed", parent=base["Normal"],
            fontSize=9, leading=12, textColor=_CLR_ORANGE,
            leftIndent=8, spaceBefore=2, spaceAfter=2,
        ),
        "insight_low": ParagraphStyle(
            "InsightLow", parent=base["Normal"],
            fontSize=9, leading=12, textColor=_CLR_GREEN,
            leftIndent=8, spaceBefore=2, spaceAfter=2,
        ),
        "rec": ParagraphStyle(
            "PDFRec", parent=base["Normal"],
            fontSize=9, leading=12, leftIndent=16, bulletIndent=8,
            spaceBefore=2, spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "PDFFooter", parent=base["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "CellStyle", parent=base["Normal"],
            fontSize=8, leading=10,
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper builders
# ═══════════════════════════════════════════════════════════════════════════════

def _delta_str(curr: float | None, prev: float | None) -> str:
    """Format delta arrow string."""
    if curr is None or prev is None:
        return "\u2014"
    d = round(curr - prev, 2)
    if d > 0:
        return f"\u25b2 +{d}"
    elif d < 0:
        return f"\u25bc {d}"
    return "\u2014 0"


def _equip_status(hours: float | None) -> tuple[str, colors.Color]:
    """Determine equipment status label and colour."""
    if hours is None or hours == 0:
        return _STATUS_OFF, _CLR_GREY
    if hours >= 16:
        return _STATUS_OK, _CLR_GREEN
    if hours >= 8:
        return _STATUS_WARN, _CLR_ORANGE
    return _STATUS_CRIT, _CLR_RED


def _make_table(data: list[list], col_widths: list[float] | None = None) -> Table:
    """Build a styled table with alternating rows."""
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), _CLR_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _CLR_HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    # Alternating row colours
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), _CLR_ROW_ALT))
    t.setStyle(TableStyle(style_cmds))
    return t


def _fv(val: Any, decimals: int = 1) -> str:
    """Format value for display."""
    if val is None:
        return "\u2014"
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)


# ═══════════════════════════════════════════════════════════════════════════════
#  Page-level builders
# ═══════════════════════════════════════════════════════════════════════════════

def _build_header(
    styles: dict,
    job_id: str,
    target_date: str,
    shift: str,
    timeline_day: dict[str, Any],
) -> list:
    """Build header block elements."""
    elements: list = []
    elements.append(Paragraph("SOLIDS CONTROL \u2014 SHIFT HANDOVER REPORT", styles["title"]))
    elements.append(Spacer(1, 4))

    engineer = timeline_day.get("engineer") or "\u2014"
    depth = _fv(timeline_day.get("depth_md"))
    activity = timeline_day.get("activity") or "\u2014"
    shift_label = get_shift_label(shift)

    info_data = [
        [f"Job: {job_id}", f"Date: {target_date}", f"Shift: {shift_label}"],
        [f"Engineer: {engineer}", f"Depth: {depth}m MD", f"Activity: {activity}"],
    ]
    info_table = Table(info_data, colWidths=[2.2 * inch, 2.3 * inch, 2.5 * inch])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8))
    return elements


def _build_equipment_table(
    styles: dict,
    equipment: dict[str, Any],
) -> list:
    """Build the equipment summary table."""
    elements: list = []
    elements.append(Paragraph("EQUIPMENT SUMMARY", styles["section"]))

    header = ["Equipment", "Hours", "Feed/Size", "Mesh", "Status"]
    rows = [header]

    # Shakers
    for s in equipment.get("shakers", []):
        hours = s.get("hours")
        name = s.get("name", "Shaker")
        mesh_vals = s.get("mesh", [])
        mesh_str = "/".join(str(int(m)) for m in mesh_vals if m is not None) or "\u2014"
        status_lbl, _ = _equip_status(hours)
        rows.append([name, _fv(hours, 0) + "h" if hours is not None else "\u2014",
                      "\u2014", mesh_str, status_lbl])

    # Centrifuges
    for c in equipment.get("centrifuges", []):
        hours = c.get("hours")
        name = c.get("name", "Centrifuge")
        feed = c.get("feed_rate")
        c_type = c.get("type") or ""
        feed_str = f"{_fv(feed, 0)} GPM" if feed else "\u2014"
        status_lbl, _ = _equip_status(hours)
        rows.append([f"{name} ({c_type})" if c_type else name,
                      _fv(hours, 0) + "h" if hours is not None else "\u2014",
                      feed_str, "\u2014", status_lbl])

    # Hydrocyclones
    hydros = equipment.get("hydrocyclones", {})
    for key, label in [("desander", "Desander"), ("desilter", "Desilter"), ("mud_cleaner", "Mud Cleaner")]:
        h = hydros.get(key, {})
        hours = h.get("hours")
        size = h.get("size")
        cones = h.get("cones")
        size_str = f'{_fv(size, 0)}"' if size else "\u2014"
        if cones:
            size_str += f" x{cones}"
        status_lbl, _ = _equip_status(hours)
        rows.append([label, _fv(hours, 0) + "h" if hours is not None else "\u2014",
                      size_str, "\u2014", status_lbl])

    if len(rows) == 1:
        elements.append(Paragraph("No equipment data available.", styles["body"]))
    else:
        col_w = [1.8 * inch, 0.8 * inch, 1.2 * inch, 1.0 * inch, 0.9 * inch]
        elements.append(_make_table(rows, col_w))

    elements.append(Spacer(1, 8))
    return elements


def _build_mud_props_table(
    styles: dict,
    timeline_day: dict[str, Any],
    prev_day: dict[str, Any] | None,
    shift: str,
) -> list:
    """Build the mud properties table with delta and target columns."""
    elements: list = []
    shift_label = get_shift_label(shift)
    elements.append(Paragraph(f"MUD PROPERTIES ({shift_label})", styles["section"]))

    # Use shift-specific props if available, else daily average
    mud_by_shift = timeline_day.get("mud_properties_by_shift", {})
    shift_props = mud_by_shift.get(shift)
    if not shift_props or shift_props.get("samples_count", 0) == 0:
        # Fall back to daily average
        shift_props = timeline_day.get("mud_properties", {})

    prev_props = prev_day.get("mud_properties", {}) if prev_day else {}

    header = ["Property", "Value", "Prev Day", "Delta", "Target Range"]
    rows = [header]

    for prop_key in _DISPLAY_PROPS:
        label = _PROP_LABELS.get(prop_key, prop_key)
        curr_val = shift_props.get(prop_key)
        prev_val = prev_props.get(prop_key)
        target_info = _TARGETS.get(prop_key, ("\u2014", ""))
        target_str = target_info[0]
        unit = target_info[1]

        val_str = f"{_fv(curr_val)} {unit}".strip() if curr_val is not None else "\u2014"
        prev_str = f"{_fv(prev_val)} {unit}".strip() if prev_val is not None else "\u2014"
        delta = _delta_str(curr_val, prev_val)

        rows.append([label, val_str, prev_str, delta, target_str])

    col_w = [1.3 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch, 1.2 * inch]
    elements.append(_make_table(rows, col_w))
    elements.append(Spacer(1, 8))
    return elements


def _build_key_insights(
    styles: dict,
    insights_data: dict[str, Any],
) -> list:
    """Build the key insights section."""
    elements: list = []
    elements.append(Paragraph("KEY INSIGHTS", styles["section"]))

    insight_items = insights_data.get("insights", [])
    if not insight_items:
        elements.append(Paragraph(
            "Normal operations. All equipment and mud properties within expected parameters.",
            styles["body"],
        ))
    else:
        for ins in insight_items[:6]:  # Limit to 6 insights on page 1
            severity = ins.get("severity", "low")
            style_key = f"insight_{severity}" if f"insight_{severity}" in styles else "body"
            sev_icon = {"high": "!!", "medium": "!", "low": "~"}.get(severity, "")
            title = ins.get("title", "")
            narrative = ins.get("narrative", "")
            cause = ins.get("cause")

            text = f"<b>[{sev_icon}] {title}</b>: {narrative}"
            if cause:
                text += f"<br/><i>{cause}</i>"
            elements.append(Paragraph(text, styles[style_key]))

    elements.append(Spacer(1, 6))
    return elements


def _build_chemicals_section(
    styles: dict,
    chemicals: list[dict[str, Any]],
) -> list:
    """Build chemical inventory tables (Additions and Losses)."""
    elements: list = []
    elements.append(Paragraph("CHEMICAL INVENTORY CHANGES", styles["section"]))

    additions = [c for c in chemicals if str(c.get("add_loss", "")).strip().lower() in ("add", "addition", "added")]
    losses = [c for c in chemicals if c not in additions]

    col_w = [2.0 * inch, 0.9 * inch, 0.8 * inch, 2.0 * inch]

    # Additions table
    elements.append(Paragraph("Additions", styles["body"]))
    if additions:
        add_rows = [["Item", "Qty", "Units", "Category"]]
        for c in additions:
            add_rows.append([
                str(c.get("item", "\u2014")),
                _fv(c.get("quantity"), 1),
                str(c.get("units") or "\u2014"),
                str(c.get("category") or "\u2014"),
            ])
        elements.append(_make_table(add_rows, col_w))
    else:
        elements.append(Paragraph("No additions recorded.", styles["body_small"]))
    elements.append(Spacer(1, 6))

    # Losses table
    elements.append(Paragraph("Losses", styles["body"]))
    if losses:
        loss_rows = [["Item", "Qty", "Units", "Category"]]
        for c in losses:
            loss_rows.append([
                str(c.get("item", "\u2014")),
                _fv(c.get("quantity"), 1),
                str(c.get("units") or "\u2014"),
                str(c.get("category") or "\u2014"),
            ])
        elements.append(_make_table(loss_rows, col_w))
    else:
        elements.append(Paragraph("No losses recorded.", styles["body_small"]))
    elements.append(Spacer(1, 8))

    return elements


def _build_volumes_section(
    styles: dict,
    volumes: dict[str, Any] | None,
) -> list:
    """Build volume accounting section."""
    elements: list = []
    elements.append(Paragraph("VOLUME ACCOUNTING", styles["section"]))

    if not volumes:
        elements.append(Paragraph("No volume data available.", styles["body"]))
    else:
        vol_data = [
            ["Total Circ", _fv(volumes.get("total_circ"), 0) + " bbl",
             "In Storage", _fv(volumes.get("in_storage"), 0) + " bbl"],
            ["Pits", _fv(volumes.get("pits"), 0) + " bbl",
             "Mud Type", str(volumes.get("mud_type") or "\u2014")],
        ]
        vt = Table(vol_data, colWidths=[1.3 * inch, 1.5 * inch, 1.3 * inch, 1.5 * inch])
        vt.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ]))
        elements.append(vt)

    elements.append(Spacer(1, 8))
    return elements


def _build_recommendations(
    styles: dict,
    recommendations: list[str],
) -> list:
    """Build recommendations section."""
    elements: list = []
    elements.append(Paragraph("RECOMMENDATIONS FOR INCOMING SHIFT", styles["section"]))

    if not recommendations:
        elements.append(Paragraph("No specific recommendations. Continue normal operations.", styles["body"]))
    else:
        for i, rec in enumerate(recommendations, 1):
            elements.append(Paragraph(f"{i}. {rec}", styles["rec"]))

    elements.append(Spacer(1, 8))
    return elements


def _build_remarks(
    styles: dict,
    remarks: str | None,
) -> list:
    """Build operational remarks section."""
    elements: list = []
    elements.append(Paragraph("OPERATIONAL REMARKS", styles["section"]))

    if remarks:
        # Strip any HTML tags for safety
        import re
        clean = re.sub(r"<[^>]+>", "", str(remarks))
        elements.append(Paragraph(clean, styles["body"]))
    else:
        elements.append(Paragraph("No remarks recorded.", styles["body"]))

    elements.append(Spacer(1, 6))
    return elements


def _build_footer(styles: dict) -> list:
    """Build footer with timestamp and version."""
    now = datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")
    elements: list = []
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"Generated: {now}  |  Solids Control Insight System v{_VERSION}",
        styles["footer"],
    ))
    return elements


# ═══════════════════════════════════════════════════════════════════════════════
#  Main entry point
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf(
    job_id: str,
    target_date: str,
    shift: str,
    timeline_day: dict[str, Any],
    prev_day: dict[str, Any] | None,
    insights_data: dict[str, Any],
) -> bytes:
    """Generate a 2-page PDF shift handover report.

    Args:
        job_id: Job identifier (e.g. "TK021").
        target_date: ISO date string.
        shift: Shift label ("day", "evening", "night").
        timeline_day: Complete timeline dict for the target date.
        prev_day: Timeline dict for the previous day (for deltas), or None.
        insights_data: Output of narrative_generator.generate_insights().

    Returns:
        PDF content as bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title=f"Shift Report - {job_id} - {target_date}",
    )

    styles = _get_styles()
    story: list = []

    # ── Page 1 ───────────────────────────────────────────────────────────
    story.extend(_build_header(styles, job_id, target_date, shift, timeline_day))
    story.extend(_build_equipment_table(styles, timeline_day.get("equipment", {})))
    story.extend(_build_mud_props_table(styles, timeline_day, prev_day, shift))
    story.extend(_build_key_insights(styles, insights_data))

    # ── Page break ───────────────────────────────────────────────────────
    story.append(PageBreak())

    # ── Page 2 ───────────────────────────────────────────────────────────
    story.extend(_build_chemicals_section(styles, timeline_day.get("chemicals", [])))
    story.extend(_build_volumes_section(styles, timeline_day.get("volumes")))
    story.extend(_build_recommendations(styles, insights_data.get("recommendations", [])))
    story.extend(_build_remarks(styles, timeline_day.get("remarks")))
    story.extend(_build_footer(styles))

    doc.build(story)
    return buf.getvalue()
