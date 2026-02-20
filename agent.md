# Mud Reports — Solids Control Insight System

## Overview

Full-stack drilling mud analysis application. Reads a 2.2 GB legacy SQLite database (Wellstar.db, 17,732 jobs) and surfaces daily solids-control insights via an event-detection engine, causal linker, narrative generator, and PDF report builder. The React dashboard visualizes equipment status, mud property trends, chemical usage, and AI-detected events.

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Axios, React Router, Recharts, date-fns, react-to-print
- **Backend**: FastAPI 0.104.1, SQLAlchemy 2.0.23, Pydantic 2.5.0, reportlab 4.x, pandas
- **Database**: SQLite — `app.db` (read-write, app state) + `Wellstar.db` (read-only, legacy drilling data)
- **Design System**: Dark industrial control-room theme (JetBrains Mono + DM Sans, cyan accent #00d4ff, atmospheric backgrounds)

## Project Structure

```
Mud-Reports/
├── docs/
│   ├── build-overview.md              # 5-phase build plan (1269 lines)
│   ├── database-overview.md
│   ├── solids-control-insight-system-design.md
│   └── top-complete-jobs.md
├── frontend/
│   ├── src/
│   │   ├── styles/
│   │   │   ├── variables.css          # 100+ CSS design tokens
│   │   │   └── globals.css            # Reset, atmospheric bg, animations
│   │   ├── services/
│   │   │   ├── api.ts                 # Legacy items API
│   │   │   └── insightsApi.ts         # Typed client for all 7 insight endpoints
│   │   ├── components/
│   │   │   ├── JobSelector.tsx/.css    # Searchable dropdown, keyboard nav
│   │   │   ├── DateSlider.tsx/.css     # Range slider with arrow keys
│   │   │   ├── EquipmentStatus.tsx/.css # Horizontal bars (hours/24h)
│   │   │   ├── MudPropsSnapshot.tsx/.css # 3×3 grid with delta arrows
│   │   │   ├── TrendCharts.tsx/.css    # 4 Recharts (solids, rheology, chems, MW)
│   │   │   ├── EventCards.tsx/.css     # Expandable insight cards + severity badges
│   │   │   ├── InventoryTable.tsx/.css # Sortable chemical table + category badges
│   │   │   ├── ReportRemarks.tsx/.css  # Monospace remarks display
│   │   │   └── AgentPlaceholder.tsx/.css # "Coming Soon" with shimmer
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx           # Main page — state mgmt, data fetching, URL sync
│   │   │   └── Dashboard.css           # Responsive layout (3 breakpoints)
│   │   ├── App.tsx                     # React Router (/dashboard/:jobId?/:date?)
│   │   └── main.tsx                    # Entry point with BrowserRouter
│   └── public/
├── backend/
│   ├── database.py                     # Dual engines: app.db (rw) + Wellstar.db (ro)
│   ├── models.py                       # App models
│   ├── models_wellstar.py              # 5 ORM models (Equipment, Sample, ConcentAddLoss, Report, CircData)
│   ├── schemas.py                      # App schemas
│   ├── schemas_insights.py             # Event, CausalLink, InsightItem, InsightsResponse + enums
│   ├── services/
│   │   ├── timeline.py                 # Timeline aggregator (~390 lines) — daily join across 5 tables
│   │   ├── chemical_categorizer.py     # 16 regex categories with LRU cache
│   │   ├── event_detector.py           # 18 event detectors (743 lines)
│   │   ├── causal_linker.py            # 7 causal rules (237 lines)
│   │   ├── narrative_generator.py      # 18 narrative templates → plain-English insights
│   │   └── pdf_generator.py            # 2-page reportlab shift handover PDF
│   ├── routers/
│   │   ├── items.py                    # Legacy CRUD
│   │   └── insights.py                 # 7 insight endpoints (402 lines)
│   ├── main.py
│   ├── init_db.py
│   ├── requirements.txt
│   └── db/                             # Wellstar.db lives here (not tracked in git)
├── README.md
└── agent.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/insights/jobs` | GET | List all jobs (13,250 with ≥10 reports) |
| `/api/insights/jobs/{id}/summary` | GET | Job stats (dates, depths, mud type, engineers) |
| `/api/insights/jobs/{id}/timeline` | GET | Daily timeline — equipment, mud props, chemicals, volumes |
| `/api/insights/jobs/{id}/events` | GET | Auto-detected events + causal links (filterable) |
| `/api/insights/jobs/{id}/chemicals/new` | GET | First-appearance date per chemical |
| `/api/insights/jobs/{id}/insights/{date}` | GET | Plain-English insights + recommendations for a date |
| `/api/insights/jobs/{id}/report/{date}` | GET | Shift handover report (JSON or PDF, ?format=pdf&shift=day) |

## Build Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** — Data Foundation | ✅ Complete | DB connection, 5 ORM models, timeline aggregator, chemical categorizer, 3 endpoints |
| **Phase 2** — Event Detection | ✅ Complete | 18 detectors, 7 causal rules, Pydantic schemas, 2 endpoints |
| **Phase 3** — Narrative + PDF | ✅ Complete | 18 narrative templates, reportlab PDF generator, shift grouping, 2 endpoints |
| **Phase 4** — Dashboard UI | ✅ Complete | 9 React components, Recharts trends, responsive CSS, dark theme, full API integration |
| **Phase 5** — Agent + Polish | ⬜ Not started | LangChain agent stub, chat UI, final QA |

## Pilot Job

**TK021** — used for all verification:
- 74 equipment days, 247 samples, 17,206 inventory transactions, 21 unique chemicals
- Date range: 2017-11-22 → 2018-02-03
- 200 detected events, 54 causal links
- 8 insights for 2018-01-08, valid PDF (9,981 bytes)

## Running

```bash
# Backend (port 8080)
cd backend && python -m uvicorn backend.main:app --port 8080

# Frontend (port 5173, proxies /api → 8080)
cd frontend && npm run dev
```

## Change Log

- **2025-02-19**: Initial project setup with React + TypeScript frontend and FastAPI + SQLite backend.
- **2026-02-20**: Phase 1 — Data Foundation: dual DB engines, 5 Wellstar ORM models, timeline aggregator, chemical categorizer, 3 API endpoints.
- **2026-02-20**: Phase 2 — Event Detection: 18 event detectors, 7 causal linker rules, Pydantic schemas, 2 API endpoints. Verified: 200 events, 54 causal links for TK021.
- **2026-02-20**: Phase 3 — Narrative + PDF: 18 narrative templates, reportlab PDF generator, shift grouping, 2 API endpoints. Verified: correct narratives, valid PDFs.
- **2026-02-20**: Phase 4 — Dashboard UI: 9 components (JobSelector, DateSlider, EquipmentStatus, MudPropsSnapshot, TrendCharts, EventCards, InventoryTable, ReportRemarks, AgentPlaceholder), dark industrial theme with Cuttings-load aesthetic, responsive 3-breakpoint layout, full API integration. Verified: TK021 end-to-end, 0 TypeScript errors.
