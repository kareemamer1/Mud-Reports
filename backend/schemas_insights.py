"""Pydantic response schemas for the Insights API (Phase 2+)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


# ── Enums ────────────────────────────────────────────────────────────────────

class EventSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventType(str, Enum):
    # Equipment (§5.1)
    SHAKER_DOWN = "shaker_down"
    SCREEN_CHANGE = "screen_change"
    CENTRIFUGE_DOWN = "centrifuge_down"
    CENTRIFUGE_FEED_CHANGE = "centrifuge_feed_change"
    HYDROCYCLONE_DOWN = "hydrocyclone_down"
    EQUIPMENT_STARTUP = "equipment_startup"
    # Mud properties (§5.2)
    SOLIDS_SPIKE = "solids_spike"
    SAND_INCREASE = "sand_increase"
    LGS_CREEP = "lgs_creep"
    DRILL_SOLIDS_RISE = "drill_solids_rise"
    RHEOLOGY_SHIFT = "rheology_shift"
    WEIGHT_UP = "weight_up"
    DILUTION = "dilution"
    PH_SHIFT = "ph_shift"
    # Inventory (§5.3)
    NEW_CHEMICAL = "new_chemical"
    CHEMICAL_SPIKE = "chemical_spike"
    LARGE_FORMATION_LOSS = "large_formation_loss"
    HIGH_SC_REMOVAL = "high_sc_removal"


# ── Core models ──────────────────────────────────────────────────────────────

class Event(BaseModel):
    id: str
    event_type: EventType
    severity: EventSeverity
    date: str  # ISO date
    title: str
    description: str
    values: dict
    related_events: list[str] = []


class CausalLink(BaseModel):
    cause_event_id: str
    effect_event_id: str
    rule_name: str
    explanation: str
    confidence: str  # "HIGH" | "MEDIUM"


# ── Response models ──────────────────────────────────────────────────────────

class TimelineDay(BaseModel):
    date: str
    depth_md: float | None = None
    depth_tvd: float | None = None
    activity: str | None = None
    equipment: dict
    mud_properties: dict
    mud_properties_by_shift: dict
    chemicals: list[dict]
    volumes: dict | None = None
    remarks: str | None = None
    engineer: str | None = None


class JobSummary(BaseModel):
    job_id: str
    first_date: str | None = None
    last_date: str | None = None
    total_days: int
    max_depth_md: float | None = None
    max_depth_tvd: float | None = None
    mud_type: str | None = None
    unique_chemicals: int
    total_samples: int
    equipment_days: int = 0
    chemical_transactions: int = 0
    engineers: list[str] = []


class ChemicalFirstAppearance(BaseModel):
    item_name: str
    category: str
    first_date: str
    first_quantity: float | None = None
    units: str | None = None


class EventsResponse(BaseModel):
    events: list[Event]
    causal_links: list[CausalLink]
    total: int
    filters: dict


class NewChemicalsResponse(BaseModel):
    job_id: str
    new_chemicals: list[ChemicalFirstAppearance]
    total: int


# ── Phase 3: Narrative + PDF models ──────────────────────────────────────────

class InsightItem(BaseModel):
    severity: str
    title: str
    narrative: str
    cause: str | None = None
    recommendation: str


class InsightsResponse(BaseModel):
    date: str
    summary: str
    insights: list[InsightItem]
    shift_notes: dict[str, str]
    recommendations: list[str]
