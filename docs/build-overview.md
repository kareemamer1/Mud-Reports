# Solids Control Insight System — MVP Build Overview

> **Version**: 1.0 — Feb 20, 2026
> **Reference**: [solids-control-insight-system-design.md](solids-control-insight-system-design.md) (v2.1)
> **Pilot Job**: TK021 — 74 equipment days, 247 samples, 17,206 inventory txns, 21 unique chemicals

---

## Build Strategy

The MVP is divided into **5 phases** with strict sequential dependency — each phase builds on the outputs of the previous one. Within each phase, tasks are ordered by their internal dependencies.

```
Phase 1          Phase 2          Phase 3          Phase 4          Phase 5
Data Foundation → Event Detection → Narrative + PDF → Dashboard UI  → Agent + Polish
   (Backend)        (Backend)         (Backend)       (Frontend)      (Full Stack)
     │                 │                  │               │               │
     ▼                 ▼                  ▼               ▼               ▼
  DB + Models      Detectors +       Templates +     React App +     LangChain Stub
  Timeline Svc     Causal Links      reportlab PDF   Recharts         + Final QA
  Chem Categorizer Pydantic Schemas  Shift Grouping  11 Components
  3 API Endpoints  2 API Endpoints   2 API Endpoints Responsive CSS   3 API Endpoints
```

### Dependency Chain

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  1.1 DB Connection ──► 1.2 Models ──► 1.4 Timeline Svc ──► 1.6 Router      │
│                                    ├──► 1.3 Indexes                         │
│                         1.5 Chem Categorizer ──────────┘                    │
│                                                                              │
│  1.6 Router ──► 2.1 Schemas ──► 2.2 Equip Detector ──► 2.5 Causal Linker  │
│                              ├──► 2.3 Mud Detector    ──┘                  │
│                              ├──► 2.4 Inventory Detector ──┘               │
│                              └──► 2.6 Events Router                        │
│                                                                              │
│  2.5 Causal Linker ──► 3.1 Narrative Generator ──► 3.3 Insights Router     │
│                     ├──► 3.2 PDF Generator ────────► 3.4 Report Router      │
│                     └──► 3.5 Shift Grouping Logic (used by 3.1, 3.2)       │
│                                                                              │
│  3.3 + 3.4 Routers ──► 4.1 Install Deps ──► 4.2 API Client ──► 4.3-4.13  │
│                                                                              │
│  4.* Components ──► 5.1 Agent Stub ──► 5.2 Agent Router ──► 5.3 Chat UI   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Data Foundation (Backend)

**Goal**: Establish read-only access to Wellstar.db, model the schema in SQLAlchemy, aggregate daily timeline data, and categorize chemicals.

**Endpoints delivered**: `GET /jobs`, `GET /jobs/{id}/summary`, `GET /jobs/{id}/timeline`

| Task | Description | Depends On | Complexity |
|------|-------------|------------|------------|
| 1.1 | Database connection setup | — | Low |
| 1.2 | Wellstar SQLAlchemy models | 1.1 | Medium |
| 1.3 | Performance indexes | 1.1 | Low |
| 1.4 | Timeline aggregator service | 1.2 | High |
| 1.5 | Chemical categorizer service | — | Medium |
| 1.6 | Insights router + registration | 1.4, 1.5 | Medium |
| 1.7 | Phase 1 verification | 1.6 | Low |

---

### Task 1.1 — Database Connection Setup

**File**: `backend/database.py`

**What**: Add a second SQLAlchemy engine for `Wellstar.db` alongside the existing `app.db` engine. The Wellstar engine must be **read-only** (no writes to source data).

**Implementation**:
```python
# Add to existing database.py
WELLSTAR_DB_PATH = Path(__file__).parent / "db" / "Wellstar.db"

wellstar_engine = create_engine(
    f"sqlite:///{WELLSTAR_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

WellstarSession = sessionmaker(autocommit=False, autoflush=False, bind=wellstar_engine)

def get_wellstar_db():
    db = WellstarSession()
    try:
        yield db
    finally:
        db.close()
```

**Acceptance Criteria**:
- [ ] `get_wellstar_db()` yields a working session that can query Wellstar.db
- [ ] Existing `get_db()` for app.db still works
- [ ] No import errors when backend starts

**Gotchas**:
- Path must resolve correctly for both local dev and Linux VPS deployment
- `check_same_thread=False` is required for SQLite + FastAPI async

---

### Task 1.2 — Wellstar SQLAlchemy Models

**File**: `backend/models_wellstar.py` (new)

**What**: Define SQLAlchemy ORM models that reflect the existing Wellstar.db tables. These are read-only — no `Base.metadata.create_all()` needed.

**Models to define**:

| Model | Table | Key Fields (subset — full schema from design doc §2) |
|-------|-------|------|
| `Equipment` | `Equipment` | Job, ReportDate, ShakerHours1-5, ShakerSize1_1..5_4, Centrifuge1-3_Hours/_FeedRate/_Type, DesanderHours, DesilterHours, MudCleanerHours |
| `Sample` | `Sample` | Job, ReportDate, SampleTime, MudWeight_PPG, Plastic_Viscosity, Yield_Point, Gel_Strength10sec/10min/30min, Solids_Content, Sand_Content, SolidsPct_GravHigh/GravLow/DrillSolids, PH, Chloride, Filtrate_API, Oil_Ratio, ElectricalStability |
| `ConcentAddLoss` | `ConcentAddLoss` | Job, ReportDate, AddLoss, ItemName, Quantity, RepUnits, Location, ItemType, Notes |
| `Report` | `Report` | Job, ReportDate, PresentActivity, MDDepth, TVDDepth, Remarks, Engineer |
| `CircData` | `CircData` | Job, ReportDate, MudVol_totalcirc, MudVol_Pits, MudVol_InStorage, MudVol_MudType |

**Implementation approach**:
- Use `autoload_with=wellstar_engine` or manually define columns to match source schema
- Use a separate `WellstarBase = declarative_base()` — do NOT mix with the app.db Base
- All models should be read-only (no create/update/delete operations)

**Acceptance Criteria**:
- [ ] `session.query(Equipment).filter_by(Job="TK021").count()` returns 74
- [ ] `session.query(Sample).filter_by(Job="TK021").count()` returns 247
- [ ] `session.query(ConcentAddLoss).filter_by(Job="TK021").count()` returns 17,206
- [ ] All column names match the actual Wellstar.db schema

**Gotchas**:
- Column names in Wellstar.db may have mixed cases — SQLAlchemy column names must match exactly
- Some columns may have unusual data types (TEXT for everything in SQLite)
- Need to query actual table schema via `PRAGMA table_info(Equipment)` to get exact column names

---

### Task 1.3 — Performance Indexes

**File**: `backend/init_db.py` or a one-time migration script

**What**: Apply performance indexes to Wellstar.db for the join patterns used by the timeline aggregator. These are `CREATE INDEX IF NOT EXISTS` so they're safe to re-run.

```sql
CREATE INDEX IF NOT EXISTS idx_equipment_job_date ON Equipment(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_sample_job_date ON Sample(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_concentaddloss_job_date ON ConcentAddLoss(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_report_job_date ON Report(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_sample_time ON Sample(Job, ReportDate, SampleTime);
```

**Acceptance Criteria**:
- [ ] Indexes exist after running the script
- [ ] Query `SELECT * FROM Equipment WHERE Job='TK021'` is visibly faster (or stays fast)

**Gotchas**:
- This is the ONE write operation we make to Wellstar.db — indexes only
- Run once, not on every app startup (check if index exists first)

---

### Task 1.4 — Timeline Aggregator Service

**File**: `backend/services/timeline.py` (new)

**What**: The core data engine. Joins Equipment + Sample + ConcentAddLoss + Report + CircData by `Job + ReportDate` and produces a structured daily summary.

**Inputs**: `job_id: str`, optional `start_date: str`, `end_date: str`

**Output schema** (per day):
```python
{
    "date": "2018-01-15",              # ISO date
    "depth_md": 1250.0,                # from Report
    "depth_tvd": 1200.0,
    "activity": "Perforando",          # from Report.PresentActivity
    "equipment": {
        "shakers": [
            {"name": "Shaker1", "hours": 18.0, "mesh": [60, 60, 60, 60]},
            ...
        ],
        "centrifuges": [
            {"name": "Cent1", "hours": 22.0, "feed_rate": 30.0, "type": "Barite Recovery"},
            ...
        ],
        "hydrocyclones": {
            "desander": {"hours": 18.0, "size": "12\"", "cones": 2},
            "desilter": {"hours": 0.0, "size": "4\"", "cones": 16},
            "mud_cleaner": {"hours": 0.0, "size": null, "cones": null}
        }
    },
    "mud_properties": {                # Averaged across shift samples
        "mud_weight": 8.7,
        "pv": 14.0,
        "yp": 38.0,
        "gel_10s": 21.0,
        "gel_10m": 12.0,
        "gel_30m": null,
        "solids": 2.8,
        "sand": 0.1,
        "lgs": 2.8,
        "hgs": 0.0,
        "drill_solids": 0.8,
        "ph": 9.2,
        "chloride": 250.0,
        "filtrate": 8.0,
        "oil_ratio": null,             # Only for OBM
        "es": null,                    # Only for OBM
        "samples_count": 3             # How many samples this day
    },
    "mud_properties_by_shift": {       # Shift-level breakdown
        "day": { ... },               # 06:00-14:00
        "evening": { ... },           # 14:00-22:00
        "night": { ... }              # 22:00-06:00
    },
    "chemicals": [
        {"item": "Agua", "add_loss": "Add", "quantity": 120.0, "units": "bbl", "category": "Base Fluid"},
        ...
    ],
    "volumes": {                       # from CircData
        "total_circ": 450.0,
        "pits": 270.0,
        "in_storage": 200.0,
        "mud_type": "WBM"
    },
    "remarks": "Perfora fase 36\"...", # from Report.Remarks
    "engineer": "J. Rodriguez"
}
```

**Key logic**:
1. Query each table filtered by Job (+ date range if provided)
2. Parse `ReportDate` strings → Python date objects (format: "M/D/YYYY 12:00:00 AM")
3. Parse `SampleTime` strings → shift assignment (Day/Evening/Night based on §1.4)
4. Parse `Sand_Content` comma decimals → float ("0,1" → 0.1)
5. Average mud properties across all samples for daily, and group by shift for shift-level
6. Call `ChemicalCategorizer` to tag each `ItemName`
7. Detect mud type from CircData.MudVol_MudType or Sample OBM fields
8. Sort by date ascending

**Acceptance Criteria**:
- [ ] `get_timeline("TK021")` returns 74 daily rows (one per ReportDate where data exists, though the actual date range may differ)
- [ ] Each row has complete equipment, mud_properties, chemicals, volumes
- [ ] Sand_Content values are correctly parsed (no commas in output)
- [ ] Shift grouping correctly assigns samples to Day/Evening/Night
- [ ] Chemical items have category labels from the categorizer

**Gotchas**:
- Some days may have equipment data but no samples (or vice versa) — handle gracefully with nulls
- `ReportDate` format may vary across jobs — test with TK021 first
- Sand_Content comma-decimal issue is critical — must be caught
- SampleTime OLE date parsing: "12/30/1899 9:00:00 AM" → extract time only → assign shift
- Equipment table has ONE row per job+date; Sample has MULTIPLE rows per job+date

---

### Task 1.5 — Chemical Categorizer Service

**File**: `backend/services/chemical_categorizer.py` (new)

**What**: Maps free-text `ItemName` values to functional categories using regex pattern matching. See design doc §6 for full category definitions and patterns.

**Input**: `item_name: str` → **Output**: `category: str`

**Implementation**:
```python
CATEGORY_PATTERNS = {
    "Weighting Agent":    r"barit|hematit|calcium\s*carb|barita|peso",
    "Viscosifier":        r"gel|bentonit|polymer|xanthan|PAC|viscosi",
    "Thinner":            r"thinn|lignit|ligno|deflocc|adelgaz",
    "Fluid Loss Control": r"starch|CMC|filtro|almid|fluid.loss",
    "pH Control":         r"lime|caustic|NaOH|soda|cal\b|sosa",
    "LCM":                r"mica|fiber|cellophan|walnut|LCM|perdida",
    "Base Fluid":         r"^agua$|^water$|^diesel$|^oil$|aceite|base.oil",
    "Emulsifier":         r"emul|MUL\s|primary|secondary",
    "SC Removal":         r"solids.equip|centrifuge.dis|dewater",
    "Downhole Loss":      r"formation|lost.circ",
    "Recovered Mud":      r"recup|recover|lodo.+recup",
}
DEFAULT_CATEGORY = "Generic/Unknown"
```

**Must also provide**:
- `categorize(item_name: str) -> str` — single item
- `categorize_batch(items: list[str]) -> dict[str, str]` — bulk with caching
- Cache for repeated lookups (many rows share the same ItemName)

**Acceptance Criteria**:
- [ ] `categorize("Agua")` → "Base Fluid"
- [ ] `categorize("Barita")` → "Weighting Agent"
- [ ] `categorize("Quimicos")` → "Generic/Unknown"
- [ ] `categorize("Formation")` → "Downhole Loss"
- [ ] `categorize("Solids Equipment")` → "SC Removal"
- [ ] All 21 unique TK021 items receive a category (no crashes on unexpected input)

**Gotchas**:
- Pattern order matters — first match wins. "LCM perdida" should match LCM, not Downhole Loss
- Case-insensitive matching required
- Some item names are in Spanish — patterns must cover both languages
- Must handle empty strings, None, and whitespace-only inputs

---

### Task 1.6 — Insights Router + Registration

**Files**: `backend/routers/insights.py` (new), `backend/routers/__init__.py` (modify)

**What**: Create the insights router with the first 3 endpoints and register it in the main app.

**Endpoints**:

#### `GET /api/insights/jobs`
Returns a list of all jobs with basic stats for job selection.

```json
{
    "jobs": [
        {
            "job_id": "TK021",
            "first_date": "2018-01-01",
            "last_date": "2018-02-03",
            "total_days": 74,
            "report_count": 74,
            "sample_count": 247,
            "chemical_txn_count": 17206
        },
        ...
    ]
}
```

**Performance note**: This queries counts across all ~19K jobs — needs to be efficient. Consider caching or paginating. For MVP, limit to jobs with >10 reports.

#### `GET /api/insights/jobs/{job_id}/summary`
Returns detailed job summary.

```json
{
    "job_id": "TK021",
    "first_date": "2018-01-01",
    "last_date": "2018-02-03",
    "total_days": 74,
    "max_depth_md": 5200.0,
    "max_depth_tvd": 4900.0,
    "mud_type": "WBM",
    "unique_chemicals": 21,
    "total_samples": 247,
    "engineers": ["J. Rodriguez", "M. Garcia"]
}
```

#### `GET /api/insights/jobs/{job_id}/timeline?start=&end=`
Returns daily timeline data from the Timeline Aggregator. Optional `start`/`end` query params for date filtering.

Returns array of daily summary objects (per Task 1.4 output schema).

**Acceptance Criteria**:
- [ ] `GET /api/insights/jobs` returns at least 100 jobs (filtered to >10 reports)
- [ ] `GET /api/insights/jobs/TK021/summary` returns correct stats
- [ ] `GET /api/insights/jobs/TK021/timeline` returns ~74 daily rows with complete data
- [ ] `GET /api/insights/jobs/TK021/timeline?start=2018-01-10&end=2018-01-20` returns only ~11 rows
- [ ] All endpoints return proper JSON with correct content types

---

### Task 1.7 — Phase 1 Verification

**Test with**:
```bash
# Start backend
cd backend && uvicorn main:app --reload --port 8080

# Test jobs list
curl http://localhost:8080/api/insights/jobs | python -m json.tool | head -30

# Test job summary
curl http://localhost:8080/api/insights/jobs/TK021/summary | python -m json.tool

# Test timeline (full)
curl http://localhost:8080/api/insights/jobs/TK021/timeline | python -m json.tool | head -80

# Test timeline (date filtered)
curl "http://localhost:8080/api/insights/jobs/TK021/timeline?start=2018-01-10&end=2018-01-20" | python -m json.tool
```

**Phase 1 is DONE when**:
- All 3 endpoints return valid JSON
- TK021 timeline has equipment hours, mud props (with sane values), categorized chemicals
- Sand_Content shows decimal floats (not comma strings)
- Shift grouping is present in `mud_properties_by_shift`
- No import errors or crashes

---

## Phase 2 — Event Detection (Backend)

**Goal**: Automatically detect equipment, mud property, and inventory events by comparing consecutive days. Apply causal rules to link related events.

**Endpoints delivered**: `GET /jobs/{id}/events`, `GET /jobs/{id}/chemicals/new`

**Depends on**: Phase 1 (Timeline Aggregator outputs)

| Task | Description | Depends On | Complexity |
|------|-------------|------------|------------|
| 2.1 | Pydantic schemas for insights | — | Medium |
| 2.2 | Equipment event detectors | 2.1, Phase 1 | High |
| 2.3 | Mud property event detectors | 2.1, Phase 1 | High |
| 2.4 | Inventory event detectors | 2.1, Phase 1 | Medium |
| 2.5 | Causal linker | 2.2, 2.3, 2.4 | High |
| 2.6 | Events + chemicals router | 2.5 | Medium |
| 2.7 | Phase 2 verification | 2.6 | Low |

---

### Task 2.1 — Pydantic Schemas

**File**: `backend/schemas_insights.py` (new)

**What**: Define response models for all insight-related endpoints.

**Core models**:

```python
class EventSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EventType(str, Enum):
    # Equipment
    SHAKER_DOWN = "shaker_down"
    SCREEN_CHANGE = "screen_change"
    CENTRIFUGE_DOWN = "centrifuge_down"
    CENTRIFUGE_FEED_CHANGE = "centrifuge_feed_change"
    HYDROCYCLONE_DOWN = "hydrocyclone_down"
    EQUIPMENT_STARTUP = "equipment_startup"
    # Mud properties
    SOLIDS_SPIKE = "solids_spike"
    SAND_INCREASE = "sand_increase"
    LGS_CREEP = "lgs_creep"
    DRILL_SOLIDS_RISE = "drill_solids_rise"
    RHEOLOGY_SHIFT = "rheology_shift"
    WEIGHT_UP = "weight_up"
    DILUTION = "dilution"
    PH_SHIFT = "ph_shift"
    # Inventory
    NEW_CHEMICAL = "new_chemical"
    CHEMICAL_SPIKE = "chemical_spike"
    LARGE_FORMATION_LOSS = "large_formation_loss"
    HIGH_SC_REMOVAL = "high_sc_removal"

class Event(BaseModel):
    event_type: EventType
    severity: EventSeverity
    date: str                          # ISO date
    title: str                         # Short label
    description: str                   # What happened (data-driven)
    values: dict                       # Numeric evidence (before/after, threshold, etc.)
    related_events: list[str] = []     # IDs of causally linked events

class CausalLink(BaseModel):
    cause_event_id: str
    effect_event_id: str
    rule_name: str
    explanation: str
    confidence: str                    # HIGH / MEDIUM

class TimelineDay(BaseModel):
    date: str
    depth_md: float | None
    activity: str | None
    equipment: dict
    mud_properties: dict
    mud_properties_by_shift: dict
    chemicals: list[dict]
    volumes: dict | None
    remarks: str | None
    engineer: str | None

class JobSummary(BaseModel):
    job_id: str
    first_date: str
    last_date: str
    total_days: int
    max_depth_md: float | None
    mud_type: str | None
    unique_chemicals: int
    total_samples: int
    engineers: list[str]

class ChemicalFirstAppearance(BaseModel):
    item_name: str
    category: str
    first_date: str
    first_quantity: float
    first_units: str
```

**Acceptance Criteria**:
- [ ] All models validate sample data without errors
- [ ] Enum values cover all 18 event types from design doc §5
- [ ] Models are importable from `backend.schemas_insights`

---

### Task 2.2 — Equipment Event Detectors

**File**: `backend/services/event_detector.py` (new — equipment section)

**What**: Compare consecutive daily timeline rows to detect equipment anomalies.

**Detectors** (from design doc §5.1):

| Detector | Logic | Produces |
|----------|-------|----------|
| `detect_shaker_down` | ShakerHoursX drops >50% from 7-day rolling avg | `SHAKER_DOWN` (HIGH) |
| `detect_screen_change` | ShakerSizeX_Y value differs from previous day | `SCREEN_CHANGE` (MED) |
| `detect_centrifuge_down` | CentrifugeX_Hours = 0 or drops >50% | `CENTRIFUGE_DOWN` (HIGH) |
| `detect_centrifuge_feed_change` | CentrifugeX_FeedRate changes >25% | `CENTRIFUGE_FEED_CHANGE` (MED) |
| `detect_hydrocyclone_down` | Desander/Desilter hours drops >50% | `HYDROCYCLONE_DOWN` (MED) |
| `detect_equipment_startup` | Hours goes 0 → >0 | `EQUIPMENT_STARTUP` (LOW) |

**Input**: List of `TimelineDay` dicts (sorted by date) from Timeline Aggregator
**Output**: List of `Event` objects

**Implementation approach**:
- Process timeline as sliding window (current day + 7-day lookback)
- Each detector function returns `list[Event]`
- Main `detect_equipment_events(timeline: list[dict]) -> list[Event]` calls all detectors

**Acceptance Criteria**:
- [ ] Feed TK021 timeline → produces at least some events (equipment changes exist in 74-day job)
- [ ] Events have correct severity per rules
- [ ] Events reference specific equipment (e.g., "Shaker 3" not just "a shaker")
- [ ] No false positives on day 1 (no previous day to compare)

**Gotchas**:
- First day of job has no baseline — skip or mark as "initial state"
- Equipment with 0 hours that stays at 0 is "not running" — NOT a down event
- ShakerSize fields may be null when shaker is not running — don't fire screen_change for null→null

---

### Task 2.3 — Mud Property Event Detectors

**File**: `backend/services/event_detector.py` (mud section)

**What**: Detect meaningful changes in mud properties.

**Detectors** (from design doc §5.2):

| Detector | Logic | Produces |
|----------|-------|----------|
| `detect_solids_spike` | Solids_Content increases >15% in 1 day | `SOLIDS_SPIKE` (HIGH) |
| `detect_sand_increase` | Sand_Content >0.5% or doubles | `SAND_INCREASE` (HIGH) |
| `detect_lgs_creep` | LGS increases >0.5% over 3 days | `LGS_CREEP` (MED) |
| `detect_drill_solids_rise` | DrillSolids increases >0.3% in 1 day | `DRILL_SOLIDS_RISE` (MED) |
| `detect_rheology_shift` | PV or YP changes >20% from 3-day avg | `RHEOLOGY_SHIFT` (MED) |
| `detect_weight_up` | MudWeight increases >0.3 ppg | `WEIGHT_UP` (MED) |
| `detect_dilution` | MudWeight drops + water additions detected | `DILUTION` (LOW) |
| `detect_ph_shift` | pH changes >0.5 units | `PH_SHIFT` (MED) |

**Key considerations**:
- Use daily-averaged mud properties for comparison (not individual samples)
- LGS creep uses 3-day window, not just day-over-day
- Dilution detection requires cross-referencing chemicals (water addition) with mud weight drop
- Rheology shift should note direction (UP or DOWN), include both PV and YP

**Acceptance Criteria**:
- [ ] Detects rheology changes when PV/YP shift significantly
- [ ] Dilution detection correctly cross-references chemical additions
- [ ] LGS creep using 3-day rolling window fires at correct threshold
- [ ] No false positives from null/missing data

**Gotchas**:
- Null mud properties (no samples on a day) — skip that day, don't compare null to previous
- Sand_Content comma-decimal must already be fixed by Timeline Aggregator (Task 1.4)
- Percentage changes: avoid division by zero when previous value is 0

---

### Task 2.4 — Inventory Event Detectors

**File**: `backend/services/event_detector.py` (inventory section)

**What**: Detect notable chemical inventory changes.

**Detectors** (from design doc §5.3):

| Detector | Logic | Produces |
|----------|-------|----------|
| `detect_new_chemical` | ItemName first appearance in this job | `NEW_CHEMICAL` (HIGH) |
| `detect_chemical_spike` | Quantity >3× the 7-day avg for that item | `CHEMICAL_SPIKE` (MED) |
| `detect_large_formation_loss` | Loss type "Formation" with quantity >100 bbl | `LARGE_FORMATION_LOSS` (HIGH) |
| `detect_high_sc_removal` | "Solids Equipment" loss exceeds 7-day baseline | `HIGH_SC_REMOVAL` (LOW) |

**Key considerations**:
- New chemical detection needs the full job's chemical history to determine "first appearance"
- Chemical spike needs per-item 7-day rolling average
- Formation loss detection uses the categorized item name (from Task 1.5)

**Acceptance Criteria**:
- [ ] New chemicals detected on their actual first appearance date only
- [ ] Chemical spike correctly computes per-item rolling average
- [ ] Formation losses >100 bbl flagged as HIGH severity
- [ ] SC removal events marked as LOW (positive signal)

---

### Task 2.5 — Causal Linker

**File**: `backend/services/causal_linker.py` (new)

**What**: Takes the flat list of events from all detectors and applies the 7 causal rules from design doc §5.4 to link cause-effect pairs.

**Rules**:

| Rule | IF (cause) | AND (effect) | Window | Confidence |
|------|-----------|-------------|--------|------------|
| `screen_failure_from_solids` | SolidsSpike OR SandIncrease (day N-1..N) | ShakerDown (day N) | 1 day | HIGH |
| `lgs_from_centrifuge_down` | CentrifugeDown (day N-3..N-1) | LGSCreep (day N-2..N) | 3 days | HIGH |
| `rheology_from_new_chemical` | NewChemical (day N-1..N) | RheologyShift (day N) | 1 day | HIGH |
| `rheology_from_lgs` | LGSCreep (day N-3..N) | RheologyShift (day N, UP) | 3 days | MEDIUM |
| `weight_up_operation` | BariteAddition (day N) | WeightUp (day N) | Same day | HIGH |
| `screen_change_preventive` | SandIncrease (day N-3..N-1) | ScreenChange (day N) | 3 days | MEDIUM |
| `dilution_effective` | Dilution (day N) | RheologyShift (day N..N+1, DOWN) | 1 day | MEDIUM |

**Implementation approach**:
- Sort events by date
- For each rule, scan for matching event pairs within the specified time window
- Produce `CausalLink` objects
- Attach causal links back to the events' `related_events` field

**Output**: `list[CausalLink]` + mutated events with `related_events` populated

**Acceptance Criteria**:
- [ ] Causal links produced when matching event pairs exist within windows
- [ ] Confidence levels match the rule definitions
- [ ] No duplicate links (same cause-effect pair linked twice)
- [ ] Events without causal matches remain unlinked (not an error)

**Gotchas**:
- A single event can be both a cause and an effect in different rules
- Time windows must be carefully applied — "day N-3..N-1" means 1-3 days before
- Barite addition check for `weight_up_operation` needs the chemical category from Task 1.5

---

### Task 2.6 — Events + Chemicals Router

**File**: `backend/routers/insights.py` (add endpoints)

**Endpoints**:

#### `GET /api/insights/jobs/{job_id}/events?start=&end=&severity=`
Returns all detected events for a job, optionally filtered by date range and severity.

```json
{
    "events": [
        {
            "id": "evt_TK021_20180115_shaker_down_3",
            "event_type": "shaker_down",
            "severity": "high",
            "date": "2018-01-15",
            "title": "Shaker 3 Down",
            "description": "Shaker 3 hours dropped from 18h to 6h (-67%), below 7-day average of 16.5h.",
            "values": {"shaker": 3, "hours": 6.0, "prev_avg": 16.5, "drop_pct": 67},
            "related_events": ["evt_TK021_20180114_solids_spike"]
        },
        ...
    ],
    "causal_links": [
        {
            "cause": "evt_TK021_20180114_solids_spike",
            "effect": "evt_TK021_20180115_shaker_down_3",
            "rule": "screen_failure_from_solids",
            "explanation": "Shaker 3 underperformance likely caused by elevated solids on Jan 14",
            "confidence": "HIGH"
        }
    ],
    "total": 42,
    "filters": {"start": null, "end": null, "severity": null}
}
```

#### `GET /api/insights/jobs/{job_id}/chemicals/new`
Returns date of first appearance for each unique chemical in the job.

```json
{
    "new_chemicals": [
        {"item_name": "Agua", "category": "Base Fluid", "first_date": "2018-01-01", "first_quantity": 80.0, "units": "bbl"},
        {"item_name": "Barita", "category": "Weighting Agent", "first_date": "2018-01-05", "first_quantity": 200.0, "units": "sx"},
        ...
    ]
}
```

**Acceptance Criteria**:
- [ ] Events endpoint returns events sorted by date, then severity (HIGH first)
- [ ] Severity filter works: `?severity=high` returns only HIGH events
- [ ] Date filter works: `?start=2018-01-10&end=2018-01-20` scopes events
- [ ] Causal links reference valid event IDs
- [ ] Chemicals/new returns all 21 unique TK021 chemicals with correct first dates

---

### Task 2.7 — Phase 2 Verification

**Test with**:
```bash
# All events
curl http://localhost:8080/api/insights/jobs/TK021/events | python -m json.tool | head -50

# High severity only
curl "http://localhost:8080/api/insights/jobs/TK021/events?severity=high" | python -m json.tool

# Date range
curl "http://localhost:8080/api/insights/jobs/TK021/events?start=2018-01-10&end=2018-01-20" | python -m json.tool

# New chemicals
curl http://localhost:8080/api/insights/jobs/TK021/chemicals/new | python -m json.tool
```

**Phase 2 is DONE when**:
- Events are generated from TK021 data (not zero)
- Causal links connect related events with correct explanations
- New chemicals list includes all 21 unique items with first appearance dates
- No crashes on edge cases (missing data, single-day jobs, etc.)

---

## Phase 3 — Narrative Engine + PDF (Backend)

**Goal**: Transform raw events + causal links into plain-English narratives and generate shift handover PDF reports.

**Endpoints delivered**: `GET /jobs/{id}/insights/{date}`, `GET /jobs/{id}/report/{date}?format=pdf&shift=...`

**Depends on**: Phase 2 (Events + Causal Links)

| Task | Description | Depends On | Complexity |
|------|-------------|------------|------------|
| 3.1 | Shift grouping utility | Phase 1 | Low |
| 3.2 | Narrative generator service | 3.1, Phase 2 | High |
| 3.3 | PDF generator service | 3.1, 3.2 | High |
| 3.4 | Insights + report router | 3.2, 3.3 | Medium |
| 3.5 | Phase 3 verification | 3.4 | Low |

---

### Task 3.1 — Shift Grouping Utility

**File**: `backend/services/timeline.py` (extend) or `backend/services/shift_utils.py` (new)

**What**: A utility to classify `SampleTime` values into the 3 shifts and group data accordingly.

```python
SHIFTS = {
    "day":     (time(6, 0), time(14, 0)),     # 06:00 - 14:00
    "evening": (time(14, 0), time(22, 0)),    # 14:00 - 22:00
    "night":   (time(22, 0), time(6, 0)),     # 22:00 - 06:00 (wraps midnight)
}

def classify_shift(sample_time: str) -> str:
    """Parse OLE SampleTime and return 'day', 'evening', or 'night'."""
    # Parse "12/30/1899 9:00:00 AM" → extract time → classify
```

**Gotchas**:
- Night shift wraps midnight: 22:00 → 06:00 next day. Times like 02:00 AM belong to "night"
- If SampleTime is null or unparseable, default to "day" or "unknown"

---

### Task 3.2 — Narrative Generator Service

**File**: `backend/services/narrative_generator.py` (new)

**What**: Takes a day's events + causal links and produces structured English narratives with recommendations.

**Input**: `date: str, events: list[Event], causal_links: list[CausalLink], timeline_day: TimelineDay`

**Output**:
```python
{
    "date": "2018-01-15",
    "summary": "2 notable events detected. Shaker underperformance linked to solids increase.",
    "insights": [
        {
            "severity": "high",
            "title": "Equipment Performance Change",
            "narrative": "Shaker 3 hours dropped from 18h to 6h (-67%). This coincides with...",
            "cause": "Elevated drill solids (0.5% → 0.8%) from increased ROP.",
            "recommendation": "Consider: Inspect Shaker 3 screens for blinding. Evaluate mesh size.",
            "related_data": {...}
        },
        ...
    ],
    "shift_notes": {
        "day": "PV rose to 14 cP during day shift. LGS at 2.8%.",
        "evening": "No samples recorded.",
        "night": "Mud weight stable at 8.7 ppg."
    },
    "recommendations": [
        "Monitor Shaker 3 — if hours continue to drop, inspect screens for blinding/damage.",
        "Watch LGS trend — currently 2.8%, up from 2.6%. If exceeds 3.5%, increase centrifuge capacity.",
        "PV trending up (+4 cP in 2 days). If continues, prepare for dilution treatment."
    ]
}
```

**Template strategy**: Use Python f-strings with data fill, not Jinja2 or LLM. Each event type has a narrative template:

```python
TEMPLATES = {
    "shaker_down": {
        "title": "Shaker {shaker_num} Underperforming",
        "narrative": "{name} hours dropped from {prev}h to {current}h (-{pct}%). {cause_text}",
        "recommendation": "Consider: Inspect {name} screens for blinding/damage. {mesh_suggestion}"
    },
    # ... one per EventType
}
```

**Must handle**:
- Events with causal links → include "Likely caused by..." sentence
- Events without causal links → state observation only
- Multiple events on same day → rank by severity, summarize
- No events on a day → "Normal operations. All equipment within parameters."
- Prescriptiveness level → directional guidance, no specific quantities

**Acceptance Criteria**:
- [ ] Generates readable English narratives for each event type
- [ ] Causal text matches the linked cause event
- [ ] Recommendations are directional (not prescriptive quantities)
- [ ] Days with no events produce "Normal operations" narrative
- [ ] Summary correctly counts events and highlights the most severe

---

### Task 3.3 — PDF Generator Service

**File**: `backend/services/pdf_generator.py` (new)

**What**: Uses `reportlab` to generate a PDF shift handover report matching wireframe 4.2 from the design doc.

**Input**: `job_id: str, date: str, shift: str ("day"|"evening"|"night")`

**Output**: `bytes` (PDF content) or file path

**PDF layout** (per wireframe):
- **Page 1**: Header → Equipment Summary table → Mud Properties table (shift avg + delta + target range) → Key Insights section
- **Page 2**: Chemical Inventory (Additions + Losses tables) → Volume Accounting → Recommendations for Incoming Shift → Operational Remarks → Footer

**reportlab specifics**:
- Use `SimpleDocTemplate` with `Table`, `Paragraph`, `Spacer`
- Styles: title, section headers, body text, table cells
- Status indicators: use text symbols (✅ ⚠️ 🔴 ⬜) or colored cells
- Page size: Letter or A4
- Margins: 1 inch

**Must pull data from**:
- Timeline Aggregator (equipment, mud props for specific shift, chemicals, volumes, remarks)
- Event Detector (events for that date)
- Narrative Generator (insights and recommendations)

**Acceptance Criteria**:
- [ ] Generates a valid 2-page PDF
- [ ] Equipment table shows all equipment with hours, mesh, and status indicators
- [ ] Mud properties table includes previous day comparison and delta arrows
- [ ] Key insights section shows severity-colored narratives
- [ ] Chemicals split into Additions and Losses tables
- [ ] Recommendations are actionable and match the narrative
- [ ] Remarks section includes raw operational text
- [ ] Footer shows generation timestamp and system version

**Gotchas**:
- reportlab doesn't support emoji natively — may need to use colored text/symbols instead of ✅⚠️🔴
- Tables with many rows need cell wrapping/truncation
- Test with a date that has many chemicals (TK021 has up to 232 txns/day)

---

### Task 3.4 — Insights + Report Router

**File**: `backend/routers/insights.py` (add endpoints)

**Endpoints**:

#### `GET /api/insights/jobs/{job_id}/insights/{date}`
Returns narratives for a specific date.

#### `GET /api/insights/jobs/{job_id}/report/{date}?format=json|pdf&shift=day|evening|night`
- `format=json` → returns the same data as insights endpoint plus shift-specific mud props
- `format=pdf` → returns PDF bytes with `Content-Type: application/pdf`
- `shift` parameter selects which shift's data to focus on (defaults to "day")

**Acceptance Criteria**:
- [ ] Insights endpoint returns narratives with recommendations
- [ ] `format=pdf` returns downloadable PDF
- [ ] `shift=evening` groups samples from 14:00-22:00
- [ ] Default shift is "day" if not specified

---

### Task 3.5 — Phase 3 Verification

**Test with**:
```bash
# Insights for a date
curl http://localhost:8080/api/insights/jobs/TK021/insights/2018-01-15 | python -m json.tool

# PDF download
curl -o report.pdf "http://localhost:8080/api/insights/jobs/TK021/report/2018-01-15?format=pdf&shift=day"
# Open report.pdf and visually inspect

# JSON report
curl "http://localhost:8080/api/insights/jobs/TK021/report/2018-01-15?format=json&shift=evening" | python -m json.tool
```

**Phase 3 is DONE when**:
- Insights return readable English narratives for TK021 dates
- PDF generates without errors and matches the wireframe layout
- Shift parameter correctly filters sample data
- Recommendations are directional, not prescriptive

---

## Phase 4 — Dashboard UI (Frontend)

**Goal**: Build the React dashboard per wireframe 4.1 — responsive, data-driven, fully connected to the backend API.

**Depends on**: Phase 3 (all backend endpoints available)

| Task | Description | Depends On | Complexity |
|------|-------------|------------|------------|
| 4.1 | Install frontend dependencies | — | Low |
| 4.2 | API client for insights | — | Low |
| 4.3 | App routing setup | — | Low |
| 4.4 | Job selector component | 4.2 | Medium |
| 4.5 | Date slider component | 4.2 | Medium |
| 4.6 | Equipment status panel | 4.2 | Medium |
| 4.7 | Mud properties snapshot | 4.2 | Medium |
| 4.8 | Trend charts (Recharts) | 4.2 | High |
| 4.9 | Event insight cards | 4.2 | Medium |
| 4.10 | Inventory table | 4.2 | Low |
| 4.11 | Report remarks | 4.2 | Low |
| 4.12 | Agent placeholder | — | Low |
| 4.13 | Dashboard page assembly | 4.4–4.12 | Medium |
| 4.14 | Responsive styling | 4.13 | Medium |
| 4.15 | Phase 4 verification | 4.14 | Low |

---

### Task 4.1 — Install Frontend Dependencies

**File**: `frontend/package.json`

```bash
cd frontend
npm install recharts react-to-print date-fns
```

New dependencies:
- `recharts` — Charting (line, bar, area charts)
- `react-to-print` — Print/save dashboard sections
- `date-fns` — Date parsing, formatting, arithmetic

---

### Task 4.2 — Insights API Client

**File**: `frontend/src/services/insightsApi.ts` (new)

**What**: Typed Axios client wrapping all insight endpoints.

```typescript
interface Job { job_id: string; first_date: string; last_date: string; total_days: number; ... }
interface JobSummary { ... }
interface TimelineDay { date: string; equipment: {...}; mud_properties: {...}; chemicals: [...]; ... }
interface Event { id: string; event_type: string; severity: string; ... }
interface Insight { severity: string; title: string; narrative: string; recommendation: string; ... }
interface ChemicalFirstAppearance { item_name: string; category: string; first_date: string; ... }

// API functions
getJobs(): Promise<Job[]>
getJobSummary(jobId: string): Promise<JobSummary>
getTimeline(jobId: string, start?: string, end?: string): Promise<TimelineDay[]>
getTimelineDay(jobId: string, date: string): Promise<TimelineDay>
getEvents(jobId: string, start?: string, end?: string, severity?: string): Promise<{events: Event[], causal_links: CausalLink[]}>
getInsights(jobId: string, date: string): Promise<InsightsResponse>
getReport(jobId: string, date: string, format: 'json'|'pdf', shift: string): Promise<...>
getNewChemicals(jobId: string): Promise<ChemicalFirstAppearance[]>
```

---

### Task 4.3 — App Routing Setup

**File**: `frontend/src/App.tsx` (modify)

Replace boilerplate counter with React Router:
```
/ → redirect to /dashboard
/dashboard → Dashboard page (main)
/dashboard/:jobId → Dashboard with selected job
/dashboard/:jobId/:date → Dashboard with selected job and date
```

---

### Task 4.4–4.12 — Components

Each component maps to a section of the wireframe (design doc §4.1):

| Component | Wireframe Section | Data Source | Key Features |
|-----------|-------------------|-------------|--------------|
| `JobSelector` | Top bar | `getJobs()` | Searchable dropdown, shows job ID + well name + date range |
| `DateSlider` | Below header | Timeline dates | Range slider, day counter, keyboard arrows |
| `EquipmentStatus` | Left panel | `timeline.equipment` | Horizontal bars (hours/24h), mesh labels, status colors |
| `MudPropsSnapshot` | Right panel | `timeline.mud_properties` | Value + delta arrows (▲▼—) + color coding |
| `TrendCharts` | Center section | `getTimeline()` (7-day) | 4 charts: Solids vs Equip, PV/YP, Chemicals stacked bar, MW |
| `EventCards` | Below charts | `getEvents()` | Severity badge, expandable narrative, recommendation |
| `InventoryTable` | Below events | `timeline.chemicals` | Sortable table with Add/Loss, Qty, Units, Category |
| `ReportRemarks` | Bottom | `timeline.remarks` | Raw text display, HTML sanitized |
| `AgentPlaceholder` | Below inventory | — | Static "Coming Soon" panel with example questions |

**Shared state management**:
- Dashboard page holds: `selectedJobId`, `selectedDate`, `timelineData`, `events`
- Components receive data via props
- Data fetches triggered on job/date change via `useEffect`

---

### Task 4.13 — Dashboard Page Assembly

**File**: `frontend/src/pages/Dashboard.tsx` (new)

**What**: Composes all components into the dashboard layout per wireframe.

**Layout grid** (responsive):
```
Desktop (>1024px):                    Tablet/Mobile (<1024px):
┌──────────────────────────────┐     ┌────────────────────┐
│ [JobSelector] [Date] [📄PDF] │     │ [Job▾] [Date] [PDF]│
├──────────┬───────────────────┤     ├────────────────────┤
│ Equip    │ MudProps           │     │ Equipment Status   │
│ Status   │ Snapshot           │     │ MudProps Snapshot   │
├──────────┴───────────────────┤     │ Trend Charts        │
│ Trend Charts (2×2 grid)      │     │ Event Cards         │
├──────────────────────────────┤     │ Inventory Table     │
│ Event Cards (scrollable)     │     │ Remarks             │
├──────────────────────────────┤     │ Agent Placeholder   │
│ Inventory Table              │     └────────────────────┘
├──────────────────────────────┤
│ Agent Placeholder            │
├──────────────────────────────┤
│ Report Remarks               │
└──────────────────────────────┘
```

**Data flow**:
1. On mount → `getJobs()` → populate JobSelector
2. On job select → `getJobSummary(jobId)` + `getTimeline(jobId)` → populate DateSlider + all panels
3. On date change → `getTimelineDay(jobId, date)` + `getEvents(jobId, date, date)` + `getInsights(jobId, date)` → update panels
4. PDF button → `window.open(/api/insights/jobs/{jobId}/report/{date}?format=pdf&shift=day)`

---

### Task 4.14 — Responsive Styling

**File**: `frontend/src/App.css` (modify) or new CSS modules

- Ensure all components work at:
  - Desktop: 1440px+ (2-column layout)
  - Tablet: 768px-1024px (single column, wider)
  - Mobile: 320px-768px (single column, compact)
- Charts resize with container
- Tables scroll horizontally on small screens
- Font sizes adjust: 14px base desktop, 13px tablet, 12px mobile

---

### Task 4.15 — Phase 4 Verification

**Test with**:
```bash
cd frontend && npm run dev
# Open http://localhost:5173

# Verify:
# 1. Job selector loads and shows jobs
# 2. Select TK021 → dashboard populates
# 3. Date slider shows Jan 1 - Feb 3 range
# 4. Equipment bars show shaker/centrifuge hours
# 5. Mud props show values with delta arrows
# 6. Trend charts show 7-day rolling data
# 7. Event cards show with severity colors
# 8. Inventory table shows chemicals with categories
# 9. PDF button downloads a valid PDF
# 10. Responsive: resize browser to tablet/mobile widths
```

**Phase 4 is DONE when**:
- Dashboard loads and displays TK021 data end-to-end
- All wireframe sections are present and populated
- Date navigation updates all panels
- PDF download works from the UI
- Responsive layout works on all 3 breakpoints

---

## Phase 5 — Agent Placeholder + Polish (Full Stack)

**Goal**: Wire up LangChain agent placeholder with pre-defined tool schemas, add the chat UI, then polish the overall system for demo readiness.

**Depends on**: Phase 4 (Dashboard operational)

| Task | Description | Depends On | Complexity |
|------|-------------|------------|------------|
| 5.1 | Agent stub service | — | Medium |
| 5.2 | Agent router | 5.1 | Low |
| 5.3 | Agent chat component | 5.2 | Medium |
| 5.4 | Router registration | 5.2 | Low |
| 5.5 | Edge case hardening | Phase 1-4 | Medium |
| 5.6 | Performance optimization | Phase 1-4 | Medium |
| 5.7 | Final QA + demo prep | All | Low |

---

### Task 5.1 — Agent Stub Service

**File**: `backend/services/agent_stub.py` (new)

**What**: Pre-define LangChain tool schemas and prompt templates. Placeholder response logic that acknowledges the question and explains the feature is coming.

**Contains**:
- `AGENT_TOOLS` — 6 tool definitions (query_timeline, query_events, query_mud_properties, query_chemicals, compare_periods, explain_event) — schemas only
- `SYSTEM_PROMPT` — Domain-specific prompt template for future LLM integration
- `get_placeholder_response(job_id, question)` — Returns a structured "coming soon" response that acknowledges the question topic

---

### Task 5.2 — Agent Router

**File**: `backend/routers/agent.py` (new)

**Endpoints**:
- `POST /api/agent/chat` — Accepts `{job_id, question}`, returns placeholder
- `GET /api/agent/tools` — Returns tool schema list
- `GET /api/agent/status` — Returns `{"status": "placeholder", "version": "0.0.1"}`

---

### Task 5.3 — Agent Chat Component

**File**: `frontend/src/components/AgentChat.tsx` (new)

**What**: Chat UI with input box, submit button, and response display area. Posts to `/api/agent/chat`. Shows "Coming Soon" badge and example questions.

---

### Task 5.4 — Router Registration

**File**: `backend/routers/__init__.py` (modify)

Add agent router to the main API router.

---

### Task 5.5 — Edge Case Hardening

Address known edge cases across all phases:

| Edge Case | Where | Solution |
|-----------|-------|----------|
| Job with no equipment data | Timeline | Return empty equipment section, don't crash |
| Day with no samples | Mud properties | Return nulls, skip event detection for that day |
| Chemical with unknown name | Categorizer | Return "Generic/Unknown", log for review |
| SampleTime is null | Shift grouping | Default to "unknown" shift |
| ReportDate parse failure | Timeline | Log warning, skip row |
| Very large job (500+ days) | Timeline endpoint | Add pagination or limit response size |
| Job with only 1 day | Event detection | No events (no baseline), return empty list |
| HTML in remarks | PDF + UI | Strip HTML tags for PDF, sanitize for UI |
| Unicode in item names | Categorizer + PDF | Ensure UTF-8 handling throughout |

---

### Task 5.6 — Performance Optimization

| Area | Issue | Solution |
|------|-------|----------|
| Jobs list | Querying all ~19K jobs is slow | Filter to jobs with >10 reports (~2K jobs), cache result |
| Timeline query | 5-table join for full job | Use raw SQL with CTEs, not ORM joins. Cache per job_id |
| Event detection | Re-runs on every request | Compute on first request, cache per job_id+date_range |
| PDF generation | Can be slow for data-heavy days | Stream response, show loading indicator in UI |
| Frontend | Initial data load (all timeline) | Fetch timeline in background, show loading skeleton |

---

### Task 5.7 — Final QA + Demo Prep

**Full end-to-end test**:

1. Start backend: `uvicorn main:app --port 8080`
2. Start frontend: `npm run dev` → `http://localhost:5173`
3. Walk through the dashboard:
   - Select Job TK021
   - Browse dates from Jan 1 to Feb 3
   - Verify equipment hours make sense
   - Verify mud properties have realistic values
   - Check that event cards appear on days with changes
   - Verify causal links show "Likely caused by..." text
   - Download PDF for a data-rich day
   - Open PDF, verify all sections present and readable
   - Try the agent chat, confirm placeholder response
   - Resize browser for responsive check
4. Test with a second job (pick one from the jobs list) to confirm generalization

**Phase 5 is DONE when**:
- Agent chat returns placeholder responses
- No crashes on any job/date combination
- PDF generates cleanly for any date
- Performance is acceptable (<3s for timeline load)
- Dashboard tells a coherent story about equipment behavior

---

## Summary Table

| Phase | Focus | New Files | Endpoints | Key Deliverable |
|-------|-------|-----------|-----------|-----------------|
| **1** | Data Foundation | 4 new, 2 modified | 3 | Read Wellstar.db, aggregate timeline, categorize chemicals |
| **2** | Event Detection | 3 new, 1 modified | 2 | 18 event types + 7 causal rules |
| **3** | Narrative + PDF | 3 new, 1 modified | 2 | English narratives + shift PDF report |
| **4** | Dashboard UI | 13 new, 2 modified | 0 (FE) | Full React dashboard per wireframe |
| **5** | Agent + Polish | 3 new, 1 modified | 3 | LangChain placeholder + edge case hardening |
| **Total** | | **26 new, 7 modified** | **10** | Complete MVP |

### Estimated Build Order Time (sequential)

| Phase | Estimated Duration |
|-------|--------------------|
| Phase 1 | 1–2 sessions |
| Phase 2 | 1–2 sessions |
| Phase 3 | 1–2 sessions |
| Phase 4 | 2–3 sessions |
| Phase 5 | 1 session |
| **Total** | **6–10 sessions** |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wellstar.db column names don't match our models | Phase 1 blocked | Query `PRAGMA table_info()` for every table before writing models |
| Sand_Content comma decimals appear in other fields too | Data corruption | Audit all numeric fields in TK021 for comma vs dot decimals |
| ReportDate format varies across jobs | Parse failures | Build robust date parser with multiple format fallback |
| Event detection produces too many false positives | User distrust | Add configurable thresholds, test extensively with TK021 |
| reportlab emoji/Unicode issues in PDF | Broken PDF | Use plain text indicators (OK/WARN/CRIT) instead of emoji |
| Large jobs exceed API response size limits | Timeout/crash | Paginate timeline endpoint, lazy-load events |
| Chemical categorizer misclassifies items | Wrong insights | Log all "Generic/Unknown" items, refine patterns iteratively |
