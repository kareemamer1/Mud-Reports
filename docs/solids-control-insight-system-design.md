# Solids Control Insight System — Design & Build Plan

> **Version**: 2.1 — Updated Feb 20, 2026
> **Decisions Locked**: Daily dashboard + PDF shift report, all equipment issues, LangChain agent placeholder
> **Pilot Job**: TK021 (74 days, highest inventory density)
> **Deployment**: Cloud Linux VPS
> **Auth**: None for MVP

---

## 1. System Overview

### 1.1 Objective
Build a system that **explains solids-control equipment behavior** in plain English by correlating:
- Equipment performance signals (shakers, centrifuges, hydrocyclones)
- Mud property changes (solids, rheology, chemistry)
- Chemical inventory changes (additions, losses, new introductions)

### 1.2 Users & Environment
- **Primary users**: Rig-site solids-control operators AND office mud engineers
- **UI requirement**: Responsive — works on field tablets and office desktops
- **Deployment**: Cloud Linux VPS
- **Auth**: None for MVP (add later)

### 1.3 Outputs
| Output | Audience | Delivery |
|--------|----------|----------|
| **Daily Insight Dashboard** | Mud engineer, solids-control operator | React web app (responsive) |
| **PDF Shift Handover Report** | Incoming shift crew (3 shifts/day) | Auto-generated PDF |
| **Smart Agent (future)** | All users | LangChain chat interface (placeholder) |

### 1.4 Shift Structure
- **3 shifts per day**: Day (06:00–14:00), Evening (14:00–22:00), Night (22:00–06:00)
- PDF reports generated per shift
- Samples grouped by shift based on `SampleTime`

### 1.5 Language
- **Bilingual**: English primary, Spanish terms preserved where relevant
- Keywords and item names kept in original language for traceability
- Explanations and recommendations written in English

### 1.6 Prescriptiveness Level
- **Explanations + directional guidance**
- System explains *what happened* and *why*, then suggests *direction* ("consider increasing centrifuge feed rate")
- Does NOT make specific quantitative prescriptions ("add 50 sacks") — that remains the engineer's call

### 1.7 Mud Types
- System handles both **WBM and OBM** jobs
- Detects mud type from `CircData.MudVol_MudType` or `Sample` fields (Oil_Ratio, ElectricalStability)
- Adapts explanations and chemical categories per mud type

### 1.8 Success Criteria
1. Reduce equipment NPT (non-productive time)
2. Improve mud properties stability
3. Reduce chemical waste / optimize chemical usage
4. Better operator training & knowledge transfer
5. Faster shift handover with actionable context

### 1.9 Equipment Issues Covered (All)
1. Screen blinding / tearing / premature failure
2. Centrifuge poor separation / underperformance
3. Desander / desilter overload
4. Low Gravity Solids (LGS) accumulation / creep
5. Sand content control failures
6. Mud cleaner inefficiency
7. Equipment downtime correlation with mud property degradation

---

## 2. Database Schema (Wellstar.db)

### 2.1 Core Tables

| Table | ~Records | Purpose | Join Key |
|-------|----------|---------|----------|
| `Equipment` | 242,852 | Daily solids-control equipment metrics | `Job + ReportDate` |
| `Sample` | 500K+ | Mud properties at shift level (3-6/day) | `Job + ReportDate` |
| `ConcentAddLoss` | 1M+ | Chemical inventory additions/losses | `Job + ReportDate` |
| `Report` | 346,548 | Daily reports with remarks | `Job + ReportDate` |
| `CircData` | 240K+ | Circulation / hydraulics data | `Job + ReportDate` |
| `Products` | ~1K | Product master (limited: Barite/Gel/Oil groups only) | `ProductCode` |
| `MudProp` | — | Mud property ranges / targets | `Job` |

### 2.2 Key Equipment Fields (`Equipment` Table)

```
Shakers (×5):  ShakerName1-5, ShakerSize1_1..5_4 (mesh), ShakerHours1-5
Centrifuges (×3): Centrifuge1-3Name, Centrifuge1-3_Type, _Hours, _FeedRate
Hydrocyclones:  Desander_Size, _Cones, DesanderHours
                Desilter_Size, _Cones, DesilterHours
                MudCleaner_Size, _Cones, MudCleanerHours
Other:          Other1_Name, Other1_Information (×2)
```

### 2.3 Key Mud Properties Fields (`Sample` Table)

```
Solids:      Solids_Content, Sand_Content, SolidsPct_GravHigh (HGS),
             SolidsPct_GravLow (LGS), SolidsPct_DrillSolids, SolidsPct_Bentonite
Rheology:    MudWeight_PPG, Plastic_Viscosity, Yield_Point,
             Gel_Strength10sec/10min/30min, 600/300/200/100/6/3_Reading
Chemistry:   PH, Alkalinity_Mud, Chloride, Ca, CaMg, Filtrate_API
Time:        SampleTime (shift-level: 6am/2pm/10pm typical)
```

### 2.4 Inventory Fields (`ConcentAddLoss` Table)

```
AddLoss (Add|Loss), ItemName (free text), Quantity, RepUnits,
Location, MudWeight, ItemType, Notes
```

### 2.5 Data Quality Notes
- **No explicit failure flags** → infer from hours drops + remarks keywords + solids spikes
- **Item names are free text** → need custom categorization lookup
- **Sand_Content uses comma decimals** → "0,1" = 0.1%
- **SampleTime uses OLE epoch** → "12/30/1899 9:00:00 AM" = 9:00 AM
- **Reports in Spanish/English** → keyword matching must be bilingual
- **Time resolution**: Equipment/Report/Inventory = daily; Samples = shift-level (3-6/day)

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│   React + TypeScript + Recharts + react-to-print           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Dashboard    │  │  PDF Report  │  │  Agent Chat      │  │
│  │  (Daily View) │  │  (Shift PDF) │  │  (Placeholder)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────┘  │
│         │                 │                  │              │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                        │
│                                                             │
│  /api/insights/                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Timeline │  │  Events  │  │ Insights │  │ Agent Stub │  │
│  │  Router  │  │  Router  │  │  Router  │  │   Router   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │               │         │
│  ┌────▼──────────────▼─────────────▼───────────────▼──────┐  │
│  │              INSIGHT ENGINE (Python)                    │  │
│  │                                                        │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │   Timeline   │  │    Event     │  │  Narrative   │  │  │
│  │  │  Aggregator  │  │  Detector    │  │  Generator   │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │  │
│  │         │                 │                  │          │  │
│  │  ┌──────▼─────────────────▼──────────────────▼───────┐  │  │
│  │  │         Chemical Categorizer (Lookup)             │  │  │
│  │  └──────────────────────┬────────────────────────────┘  │  │
│  │                         │                               │  │
│  │  ┌──────────────────────▼────────────────────────────┐  │  │
│  │  │    LangChain Agent Placeholder (future)           │  │  │
│  │  │    - Tool definitions for DB queries              │  │  │
│  │  │    - Prompt templates for domain reasoning        │  │  │
│  │  │    - Memory / conversation state                  │  │  │
│  │  └───────────────────────────────────────────────────┘  │  │
│  └─────────────────────────┬──────────────────────────────┘  │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │   Wellstar.db      │
                   │   (SQLite)         │
                   └────────────────────┘
```

### 3.1 Module Responsibilities

| Module | Role |
|--------|------|
| **Timeline Aggregator** | Joins Equipment + Sample + ConcentAddLoss + Report by `Job + ReportDate`. Produces daily summary rows with averaged mud props, total equip hours, chem additions. |
| **Event Detector** | Compares consecutive days. Fires typed events: `SolidsSpike`, `ScreenChange`, `EquipmentDown`, `NewChemical`, `WeightUp`, `Dilution`, `RheologyShift`, `SandIncrease`. |
| **Narrative Generator** | Given a list of events for a day, produces plain-English explanations using template + data fill. Includes causal linking (event A likely caused by event B). |
| **Chemical Categorizer** | Maps free-text `ItemName` → functional category (Weighting Agent, Viscosifier, Thinner, FLC, pH Control, LCM, Base Fluid, etc.) via pattern-match lookup table. |
| **Agent Placeholder** | Stub router `/api/agent/chat` that returns placeholder message. Pre-defined LangChain tool schemas and prompt templates ready for integration. |

---

## 4. UI Wireframes

### 4.1 Dashboard — Main Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ◉ Solids Control Insight System                          [Job ▾] [📄 PDF]  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Job: 220818 — Well: Pozo ABC-1 — Operator: XYZ Drilling                    │
│  ◀ Aug 24   [════════════════════●═══════════════════] Sep 15 ▶   Day 34     │
│     Date Slider                  ▲ Aug 25, 2018                              │
│                                                                              │
├────────────────────────────────┬─────────────────────────────────────────────┤
│                                │                                             │
│   ⚙️ EQUIPMENT STATUS          │   📊 MUD PROPERTIES SNAPSHOT               │
│                                │                                             │
│   Shaker 1  ████████░░  18h    │   MW      8.7 ppg   (▲ +0.1)              │
│   Shaker 2  ████████░░  18h    │   PV       14 cP    (▲ +4)               │
│   Shaker 3  ████████░░  15h    │   YP       38 lb    (— 0)                │
│   Shaker 4  ██████░░░░  12h    │   Gel10    21 lb    (▼ -9)               │
│   Centrifuge 1 ██████░░  22h   │   Solids   2.8%     (▲ +0.1)              │
│   Centrifuge 2 ████░░░░  13h   │   Sand     0.1%     (— 0)                │
│   Desander   ████████░░  18h   │   LGS      2.8%     (▲ +0.2)              │
│   Desilter   ░░░░░░░░░░   0h   │   HGS      0.0%     (— 0)                │
│   Mud Clnr   ░░░░░░░░░░   0h   │   pH       9.2      (— 0)                │
│                                │   Filtrate  8.0 ml   (— 0)                │
│   Screen Mesh:                 │                                             │
│   S1: 60  S2: 60  S3: 60      │   Depth: 51m MD  |  Activity: Perforando   │
│   S4: 60  S5: 100             │                                             │
│                                │                                             │
├────────────────────────────────┴─────────────────────────────────────────────┤
│                                                                              │
│   📈 TREND CHARTS (7-day rolling)                            [Day|Week|All]  │
│                                                                              │
│   Solids & Sand vs Equipment Hours                                           │
│   3.5│              ╱──solids          │24h│        ╱──shaker hrs            │
│   3.0│    ──────────╱                  │20 │───────╱                         │
│   2.5│───╱                             │16 │──╱                              │
│   2.0│                                 │12 │                                 │
│      └───────────────────────          └────────────────────────             │
│       Aug22  23  24  25  26             Aug22  23  24  25  26                │
│                                                                              │
│   PV / YP Trend                        Chemical Additions (stacked bar)      │
│   50 │╲                                │ ██ Gel  ░░ Barite  ▓▓ Other        │
│   40 │ ╲──YP──────────                 │ ██░░▓▓  ██░░  ██░░▓▓              │
│   30 │                                 │ ██░░▓▓  ██░░  ██░░▓▓              │
│   14 │    ──PV───╱────                 │ ██░░▓▓  ██░░  ██░░▓▓              │
│   10 │───╱                             └────────────────────────             │
│      └───────────────────────           Aug22  23  24  25  26                │
│       Aug22  23  24  25  26                                                  │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   🔔 EVENTS & INSIGHTS                                      [All ▾]         │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐     │
│   │ ⚠️  HIGH  Aug 24  Equipment Performance Change                     │     │
│   │                                                                    │     │
│   │ Shaker 4 hours dropped from 18h → 12h (-33%).                     │     │
│   │ Coincides with drill solids increase (0.5% → 0.8%).               │     │
│   │ ROP increased to 1.09 mph — higher cuttings volume likely         │     │
│   │ exceeded screen capacity.                                          │     │
│   │                                                                    │     │
│   │ 💡 Consider: Increase desander hours or evaluate screen mesh.     │     │
│   └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐     │
│   │ ℹ️  MED   Aug 24  Rheology Shift                                   │     │
│   │                                                                    │     │
│   │ PV rose from 10 → 14 cP (+40%) over 2 days.                      │     │
│   │ LGS trending up (2.6% → 2.8%). No new chemicals added.           │     │
│   │ Cause: Drill solids accumulating faster than removal rate.        │     │
│   │                                                                    │     │
│   │ 💡 Centrifuge feed rate may need increase. Current: 30 GPM.      │     │
│   └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐     │
│   │ ✅  LOW   Aug 23  Normal Operations                                │     │
│   │                                                                    │     │
│   │ All equipment running within normal parameters.                   │     │
│   │ Mud properties stable. No chemical changes.                       │     │
│   └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   💊 INVENTORY CHANGES TODAY                                                 │
│                                                                              │
│   ┌──────────────────┬──────────┬────────┬───────────┬──────────────────┐   │
│   │ Item             │ Add/Loss │ Qty    │ Units     │ Category         │   │
│   ├──────────────────┼──────────┼────────┼───────────┼──────────────────┤   │
│   │ Agua             │ Add      │ 120.0  │ bbl       │ Base Fluid       │   │
│   │ Quimicos         │ Add      │  45.0  │ sx        │ Mixed Chemicals  │   │
│   │ Formation        │ Loss     │ 261.0  │ bbl       │ Lost Circulation │   │
│   │ Solids Equipment │ Loss     │  35.0  │ bbl       │ SC Removal       │   │
│   │ Evaporation      │ Loss     │  12.0  │ bbl       │ Surface Loss     │   │
│   └──────────────────┴──────────┴────────┴───────────┴──────────────────┘   │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   🤖 SMART AGENT                                              [Coming Soon]  │
│   ┌────────────────────────────────────────────────────────────────────┐     │
│   │                                                                    │     │
│   │   Ask a question about this job...                                │     │
│   │   ┌────────────────────────────────────────────────────────┐      │     │
│   │   │ Why did the screens underperform this week?            │ [Ask] │     │
│   │   └────────────────────────────────────────────────────────┘      │     │
│   │                                                                    │     │
│   │   ┌──────────────────────────────────────────────────────┐        │     │
│   │   │ 🔒 Smart agent integration coming soon.              │        │     │
│   │   │    This will use LangChain to answer questions       │        │     │
│   │   │    about equipment, mud properties, and chemicals    │        │     │
│   │   │    using your job data.                              │        │     │
│   │   └──────────────────────────────────────────────────────┘        │     │
│   └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│   📋 DAILY REPORT REMARKS                                                    │
│   ┌────────────────────────────────────────────────────────────────────┐     │
│   │ Perfora fase 36" de 37m a 45m, con 15-23klb, 400-393gpm,         │     │
│   │ 45-55psi, 50rpm. ROP: 0.85 mph. Repasa con backreaming tramo     │     │
│   │ perforado de 51 a 34m 2 veces. Bombea 120 bbl de bache viscoso   │     │
│   │ de limpieza (8.8 ppg, VE: 250 seg)                               │     │
│   └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 PDF Shift Handover Report

```
┌──────────────────────────────────────────────────────────────────┐
│                                                     Page 1 of 2  │
│  ╔════════════════════════════════════════════════════════════╗   │
│  ║   SOLIDS CONTROL — SHIFT HANDOVER REPORT                 ║   │
│  ╚════════════════════════════════════════════════════════════╝   │
│                                                                   │
│  Job: 220818            Well: Pozo ABC-1         Report #: 34    │
│  Date: Aug 25, 2018     Shift: Day (06:00-14:00)                 │
│  Engineer: J. Rodriguez  Depth: 51m MD                           │
│  Activity: Perforando                                             │
│                                                                   │
│  ─── EQUIPMENT SUMMARY ──────────────────────────────────────    │
│                                                                   │
│  Equipment        Hours   Feed/Size   Mesh    Status             │
│  ─────────────── ─────── ─────────── ─────── ──────────         │
│  Shaker 1         18h     —           60      ✅ Normal          │
│  Shaker 2         18h     —           60      ✅ Normal          │
│  Shaker 3         15h     —           60      ⚠️ -3h vs avg     │
│  Shaker 4         12h     —           60      🔴 -6h vs avg     │
│  Shaker 5         —       —           100     ⬜ Not running     │
│  Centrifuge 1     22h     30 GPM      —       ✅ Normal          │
│  Centrifuge 2     13h     —           —       ⚠️ Low hours      │
│  Desander         18h     12"×—       —       ✅ Normal          │
│  Desilter          0h     4"×—        —       ⬜ Not running     │
│  Mud Cleaner       0h     —           —       ⬜ Not running     │
│                                                                   │
│  ─── MUD PROPERTIES (Shift Avg) ─────────────────────────────    │
│                                                                   │
│  Property          Value     Prev Day    Delta    Target Range   │
│  ──────────────── ───────── ─────────── ──────── ─────────────  │
│  Mud Weight        8.7 ppg   8.6 ppg    ▲ +0.1   8.5 - 9.0     │
│  PV                14 cP     10 cP      ▲ +4     8 - 15         │
│  YP                38 lb     40 lb      ▼ -2     30 - 50        │
│  Gel 10s           21 lb     30 lb      ▼ -9     15 - 35        │
│  Total Solids      2.8%      2.7%       ▲ +0.1   < 5%           │
│  Sand              0.1%      0.1%       — 0      < 0.5%         │
│  LGS               2.8%      2.6%       ▲ +0.2   < 4%           │
│  HGS               0.0%      0.1%       ▼ -0.1   —              │
│  Drill Solids      0.8%      0.5%       ▲ +0.3   < 3%           │
│  pH                9.2       9.2        — 0      9.0 - 10.5     │
│  Filtrate API      8.0 ml    8.0 ml     — 0      < 15           │
│                                                                   │
│  ─── KEY INSIGHTS ───────────────────────────────────────────    │
│                                                                   │
│  ⚠️  Shaker 4 underperforming — hours 33% below 7-day avg.      │
│      Drill solids rising (+0.3%), LGS trending up (+0.2%).       │
│      Likely cause: High ROP (1.09 mph) increasing cuttings       │
│      volume faster than current removal capacity.                 │
│                                                                   │
│  ℹ️  PV increased +4 cP (10→14). Consistent with LGS buildup.   │
│      Monitor trend — if PV exceeds 15, consider dilution or      │
│      increasing centrifuge feed rate.                             │
│                                                                   │
│  ✅  Sand content stable at 0.1%. Mud weight within range.       │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                     Page 2 of 2  │
│                                                                   │
│  ─── CHEMICAL INVENTORY CHANGES ─────────────────────────────    │
│                                                                   │
│  ADDITIONS                                                        │
│  Item               Qty      Units    Category                   │
│  ───────────────── ──────── ──────── ─────────────────           │
│  Agua (Water)       120.0    bbl      Base Fluid                 │
│  Quimicos            45.0    sx       Mixed Chemicals            │
│                                                                   │
│  LOSSES                                                           │
│  Item               Qty      Units    Category                   │
│  ───────────────── ──────── ──────── ─────────────────           │
│  Formation          261.0    bbl      Downhole Loss              │
│  Solids Equipment    35.0    bbl      SC Equipment Removal       │
│  Evaporation         12.0    bbl      Surface Loss               │
│  Tripping            8.0     bbl      Mechanical Loss            │
│                                                                   │
│  ⚡ NEW CHEMICALS: None this shift                                │
│                                                                   │
│  ─── VOLUME ACCOUNTING ──────────────────────────────────────    │
│                                                                   │
│  Total Circ:  450 bbl   │  In Storage:  200 bbl                  │
│  Hole Volume: 180 bbl   │  Reserve:     120 bbl                  │
│  Pits:        270 bbl   │  Premix:       0 bbl                   │
│                                                                   │
│  ─── RECOMMENDATIONS FOR INCOMING SHIFT ─────────────────────    │
│                                                                   │
│  1. Monitor Shaker 4 — if hours continue to drop, inspect        │
│     screens for blinding/damage. Consider screen change.         │
│                                                                   │
│  2. Watch LGS trend — currently 2.8%, up from 2.6%.             │
│     If exceeds 3.5%, increase centrifuge feed rate or add        │
│     second centrifuge to active duty.                            │
│                                                                   │
│  3. PV trending up (+4 cP in 2 days). If continues,             │
│     prepare for dilution treatment (est. 50-80 bbl water).      │
│                                                                   │
│  ─── OPERATIONAL REMARKS ────────────────────────────────────    │
│                                                                   │
│  Perfora fase 36" de 37m a 45m, con 15-23klb, 400-393gpm,       │
│  45-55psi, 50rpm. ROP: 0.85 mph. Repasa con backreaming         │
│  tramo perforado de 51 a 34m 2 veces. Bombea 120 bbl de         │
│  bache viscoso de limpieza (8.8 ppg, VE: 250 seg).              │
│                                                                   │
│  ═══════════════════════════════════════════════════════════════  │
│  Generated: Feb 20, 2026 06:00 UTC                               │
│  Solids Control Insight System v1.0                               │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Agent Chat Placeholder (Future)

```
┌──────────────────────────────────────────────────────────────────┐
│  🤖 Solids Control Smart Agent                    Job: 220818    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ 🔒  Smart Agent — Coming Soon                            │    │
│  │                                                          │    │
│  │  This feature will allow you to ask natural language     │    │
│  │  questions about job data, equipment performance, and    │    │
│  │  mud properties.                                         │    │
│  │                                                          │    │
│  │  Example questions:                                      │    │
│  │  • "Why did the screens fail last Tuesday?"              │    │
│  │  • "What chemical was added before PV spiked?"           │    │
│  │  • "How to reduce LGS without affecting MW?"             │    │
│  │  • "Compare this week's centrifuge efficiency to last"   │    │
│  │                                                          │    │
│  │  Powered by LangChain + domain-specific tools            │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐  ┌───┐  │
│  │ Ask a question...                                   │  │ ➤ │  │
│  └─────────────────────────────────────────────────────┘  └───┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Event Detection Rules

Each detector compares day N to day N-1 (or rolling 7-day baseline).

### 5.1 Equipment Events

| Event | Trigger | Severity |
|-------|---------|----------|
| `ShakerDown` | `ShakerHoursX` drops >50% from 7-day avg | HIGH |
| `ScreenChange` | `ShakerSizeX_Y` value changes | MEDIUM |
| `CentrifugeDown` | `CentrifugeX_Hours` drops to 0 or >50% drop | HIGH |
| `CentrifugeFeedChange` | `CentrifugeX_FeedRate` changes >25% | MEDIUM |
| `HydrocycloneDown` | `DesanderHours/DesilterHours` drops >50% | MEDIUM |
| `EquipmentStartup` | Hours goes from 0 → >0 | LOW (informational) |

### 5.2 Mud Property Events

| Event | Trigger | Severity |
|-------|---------|----------|
| `SolidsSpike` | `Solids_Content` increases >15% in 1 day | HIGH |
| `SandIncrease` | `Sand_Content` exceeds 0.5% or doubles | HIGH |
| `LGSCreep` | `SolidsPct_GravLow` increases >0.5% over 3 days | MEDIUM |
| `DrillSolidsRise` | `SolidsPct_DrillSolids` increases >0.3% in 1 day | MEDIUM |
| `RheologyShift` | PV or YP changes >20% from 3-day avg | MEDIUM |
| `WeightUp` | `MudWeight_PPG` increases >0.3 ppg | MEDIUM |
| `Dilution` | `MudWeight_PPG` drops + water additions detected | LOW |
| `pHShift` | pH changes >0.5 units | MEDIUM |

### 5.3 Inventory Events

| Event | Trigger | Severity |
|-------|---------|----------|
| `NewChemical` | `ItemName` first appearance for this job | HIGH |
| `ChemicalSpike` | `Quantity` for an item >3× its 7-day avg | MEDIUM |
| `LargeFormationLoss` | Loss type "Formation" with quantity >100 bbl | HIGH |
| `HighSCRemoval` | Loss type "Solids Equipment" exceeds baseline | LOW (good) |

### 5.4 Causal Linking Rules

```
RULE: screen_failure_from_solids
  IF ShakerDown(day=N) AND (SolidsSpike(day=N-1..N) OR SandIncrease(day=N-1..N))
  THEN → "Screen underperformance likely caused by elevated solids/sand"
  CONFIDENCE: HIGH

RULE: lgs_from_centrifuge_down
  IF LGSCreep(day=N-2..N) AND CentrifugeDown(day=N-3..N-1)
  THEN → "LGS accumulation correlates with centrifuge downtime"
  CONFIDENCE: HIGH

RULE: rheology_from_new_chemical
  IF RheologyShift(day=N) AND NewChemical(day=N-1..N)
  THEN → "Rheology change follows introduction of [chemical]"
  CONFIDENCE: HIGH

RULE: rheology_from_lgs
  IF RheologyShift(day=N, direction=UP) AND LGSCreep(day=N-3..N)
  THEN → "Increasing PV/YP consistent with LGS buildup"
  CONFIDENCE: MEDIUM

RULE: weight_up_operation
  IF WeightUp(day=N) AND BariteAddition(day=N)
  THEN → "Planned weight-up operation with barite"
  CONFIDENCE: HIGH

RULE: screen_change_preventive
  IF ScreenChange(day=N) AND SandIncrease(day=N-3..N-1)
  THEN → "Screen mesh changed in response to sand trend"
  CONFIDENCE: MEDIUM

RULE: dilution_effective
  IF Dilution(day=N) AND RheologyShift(day=N..N+1, direction=DOWN)
  THEN → "Dilution treatment successfully reduced rheology"
  CONFIDENCE: MEDIUM
```

---

## 6. Chemical Categorization Lookup

Since the Products table only has 3 groups (Barite, Gel, Oil), build a custom matcher:

### 6.1 Category Definitions

| Category | Function | Affects | Keywords (EN/ES) |
|----------|----------|---------|-------------------|
| **Weighting Agent** | Increase MW | MW, HGS, PV | barite, hematite, calcium carbonate, barita |
| **Viscosifier** | Increase viscosity | PV, YP, Gels | gel, bentonite, polymer, xanthan, PAC, viscosificante |
| **Thinner/Deflocculant** | Reduce viscosity | PV, YP, Gels | thinner, lignite, lignosulfonate, thinning, adelgazante |
| **Fluid Loss Control** | Reduce filtrate | Filtrate, Cake | starch, PAC, CMC, filtro, almidón |
| **pH Control** | Adjust pH/alkalinity | pH, Pf, Mf | lime, caustic, NaOH, soda, cal, sosa |
| **LCM** | Seal losses | Circulation losses | mica, fiber, cellophane, walnut, LCM, perdida |
| **Base Fluid** | Dilution / volume | MW (down), PV, Solids | water, diesel, oil, agua, aceite, OBM base |
| **Emulsifier** | OBM stability | ES, O/W ratio | emul, MUL, primary, secondary |
| **Biocide** | Bacterial control | pH stability | biocide, bactericide |
| **Defoamer** | Reduce foaming | Air entrainment | defoam, antifoam, antiespumante |
| **SC Removal** | Solids removed by equipment | Solids (down) | solids equipment, centrifuge discharge |
| **Downhole Loss** | Lost to formation | Volume deficit | formation, lost circulation, perdida formación |
| **Recovered Mud** | Returned from prior section | Variable | recup, recovered, lodo recup |
| **Generic/Unknown** | Unclassifiable | Unknown | quimicos, otras adiciones, chemicals |

### 6.2 Pattern Matching Strategy

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
```

---

## 7. API Endpoints

### 7.1 Insight Router (`/api/insights`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/jobs` | List all jobs with completeness scores |
| `GET` | `/jobs/{job_id}/summary` | Job summary: date range, depth, report count |
| `GET` | `/jobs/{job_id}/timeline?start=&end=` | Daily timeline data (equipment + mud props + inventory) |
| `GET` | `/jobs/{job_id}/timeline/{date}` | Single-day detail with all samples, events, chem changes |
| `GET` | `/jobs/{job_id}/events?start=&end=&severity=` | Detected events for date range |
| `GET` | `/jobs/{job_id}/insights/{date}` | Plain-English insights + recommendations for a day |
| `GET` | `/jobs/{job_id}/report/{date}?format=json\|pdf` | Shift handover report (JSON or PDF) |
| `GET` | `/jobs/{job_id}/chemicals/timeline` | Chemical additions over time with categories |
| `GET` | `/jobs/{job_id}/chemicals/new` | First-appearance dates for each chemical |

### 7.2 Agent Router (`/api/agent`) — Placeholder

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat` | Stub: accepts `{ job_id, question }`, returns placeholder response |
| `GET`  | `/tools` | Returns list of defined LangChain tool schemas (for future integration) |
| `GET`  | `/status` | Returns `{ "status": "placeholder", "version": "0.0.1" }` |

---

## 8. MVP Build Phases

### Phase 1 — Data Foundation (Backend)
**Goal**: Read Wellstar.db, aggregate daily timeline, categorize chemicals

**Files to Create/Modify**:
- `backend/database.py` — Add Wellstar.db engine (read-only)
- `backend/models_wellstar.py` — SQLAlchemy models reflecting Wellstar schema (Equipment, Sample, ConcentAddLoss, Report, CircData)
- `backend/services/timeline.py` — Timeline Aggregator: joins tables by Job+ReportDate, computes daily averages
- `backend/services/chemical_categorizer.py` — Pattern-matching lookup for ItemName → Category
- `backend/routers/insights.py` — `/jobs`, `/jobs/{id}/summary`, `/jobs/{id}/timeline`
- `backend/routers/__init__.py` — Register new router

**Verification**:
- `GET /api/insights/jobs` returns list of jobs with record counts
- `GET /api/insights/jobs/TK021/timeline` returns daily rows with equipment hours, avg mud props, categorized chemicals

---

### Phase 2 — Event Detection (Backend)
**Goal**: Detect equipment, mud property, and inventory events automatically

**Files to Create/Modify**:
- `backend/services/event_detector.py` — Implements all event rules from Section 5
- `backend/services/causal_linker.py` — Applies causal rules from Section 5.4, outputs linked event pairs with confidence
- `backend/schemas_insights.py` — Pydantic models: `TimelineDay`, `Event`, `Insight`, `ChemicalChange`
- `backend/routers/insights.py` — Add `/jobs/{id}/events`, `/jobs/{id}/chemicals/new`

**Verification**:
- `GET /api/insights/jobs/TK021/events` returns typed events with severity
- Known data patterns (e.g., shaker hours drop, new chemical introduction) produce expected events

---

### Phase 3 — Narrative Engine + PDF (Backend)
**Goal**: Generate plain-English insights and PDF shift reports

**Files to Create/Modify**:
- `backend/services/narrative_generator.py` — Template-based English narrative from events + causal links
- `backend/services/pdf_generator.py` — Uses `reportlab` to render shift handover PDF (per wireframe 4.2, 3 shifts/day)
- `backend/routers/insights.py` — Add `/jobs/{id}/insights/{date}`, `/jobs/{id}/report/{date}?format=pdf&shift=day|evening|night`
- `backend/requirements.txt` — Add `reportlab`, `pandas`

**Verification**:
- `GET /api/insights/jobs/TK021/insights/{date}` returns JSON with narratives
- `GET /api/insights/jobs/TK021/report/{date}?format=pdf&shift=day` downloads a PDF matching the wireframe layout

---

### Phase 4 — Dashboard UI (Frontend)
**Goal**: Build the daily insight dashboard per wireframe 4.1

**Files to Create/Modify**:
- `frontend/package.json` — Add `recharts`, `react-to-print`, `date-fns`
- `frontend/src/services/insightsApi.ts` — API client for insight endpoints
- `frontend/src/pages/Dashboard.tsx` — Main dashboard page
- `frontend/src/components/JobSelector.tsx` — Job dropdown with search
- `frontend/src/components/DateSlider.tsx` — Date range slider
- `frontend/src/components/EquipmentStatus.tsx` — Equipment hours bars with status indicators
- `frontend/src/components/MudPropsSnapshot.tsx` — Property values with delta arrows
- `frontend/src/components/TrendCharts.tsx` — Recharts line/bar charts (solids, PV/YP, chemicals)
- `frontend/src/components/EventCards.tsx` — Insight cards with severity coloring
- `frontend/src/components/InventoryTable.tsx` — Chemical additions/losses table
- `frontend/src/components/ReportRemarks.tsx` — Raw remarks display
- `frontend/src/components/AgentPlaceholder.tsx` — Locked agent chat UI
- `frontend/src/App.tsx` — Route setup with React Router

**Verification**:
- Dashboard loads for Job TK021
- Date slider navigates between days
- Equipment bars, mud props, trends, and insight cards populate correctly
- PDF download button generates and downloads report

---

### Phase 5 — Agent Placeholder + Polish (Full Stack)
**Goal**: Wire up LangChain placeholder, add finishing touches

**Files to Create/Modify**:
- `backend/services/agent_stub.py` — LangChain tool definitions (schemas only), prompt templates, placeholder response logic
- `backend/routers/agent.py` — `/api/agent/chat`, `/api/agent/tools`, `/api/agent/status`
- `backend/routers/__init__.py` — Register agent router
- `frontend/src/components/AgentChat.tsx` — Chat UI that posts to `/api/agent/chat`, displays placeholder response
- `backend/requirements.txt` — Add `langchain-core` (schemas only, no LLM dependency yet)

**Agent Tool Schemas (Pre-defined for Future)**:
```python
AGENT_TOOLS = [
    {
        "name": "query_timeline",
        "description": "Get daily timeline data for a job and date range",
        "parameters": {"job_id": "str", "start_date": "str", "end_date": "str"}
    },
    {
        "name": "query_events",
        "description": "Get detected events for a job and date range",
        "parameters": {"job_id": "str", "start_date": "str", "end_date": "str", "severity": "str?"}
    },
    {
        "name": "query_mud_properties",
        "description": "Get mud property samples for a job and date",
        "parameters": {"job_id": "str", "date": "str"}
    },
    {
        "name": "query_chemicals",
        "description": "Get chemical additions/losses for a job and date range",
        "parameters": {"job_id": "str", "start_date": "str", "end_date": "str", "category": "str?"}
    },
    {
        "name": "compare_periods",
        "description": "Compare mud properties between two date ranges",
        "parameters": {"job_id": "str", "period_a": "str", "period_b": "str"}
    },
    {
        "name": "explain_event",
        "description": "Get plain-English explanation for a specific event",
        "parameters": {"event_id": "str"}
    }
]
```

**Verification**:
- `POST /api/agent/chat` with `{"job_id": "TK021", "question": "Why did screens fail?"}` returns placeholder message
- `GET /api/agent/tools` returns tool schema list
- Chat UI displays input box and placeholder message on submit

---

## 9. File Structure (After Build)

```
backend/
├── __init__.py
├── main.py                          # FastAPI app (existing)
├── database.py                      # DB engines: app.db + Wellstar.db
├── models.py                        # Existing Item model
├── models_wellstar.py               # Wellstar table models (read-only)
├── schemas.py                       # Existing schemas
├── schemas_insights.py              # Insight-specific Pydantic models
├── db/
│   └── Wellstar.db                  # Source database (read-only)
├── routers/
│   ├── __init__.py                  # Router registry
│   ├── items.py                     # Existing items CRUD
│   ├── insights.py                  # Insight endpoints
│   └── agent.py                     # Agent placeholder
└── services/
    ├── __init__.py
    ├── timeline.py                  # Timeline Aggregator
    ├── event_detector.py            # Event detection rules
    ├── causal_linker.py             # Causal attribution
    ├── narrative_generator.py       # Plain-English explanations
    ├── chemical_categorizer.py      # ItemName → Category lookup
    ├── pdf_generator.py             # PDF shift report
    └── agent_stub.py               # LangChain placeholder + tool schemas

frontend/src/
├── services/
│   ├── api.ts                       # Existing API client
│   └── insightsApi.ts               # Insight API client
├── pages/
│   └── Dashboard.tsx                # Main dashboard page
├── components/
│   ├── JobSelector.tsx
│   ├── DateSlider.tsx
│   ├── EquipmentStatus.tsx
│   ├── MudPropsSnapshot.tsx
│   ├── TrendCharts.tsx
│   ├── EventCards.tsx
│   ├── InventoryTable.tsx
│   ├── ReportRemarks.tsx
│   ├── AgentPlaceholder.tsx
│   └── AgentChat.tsx
├── App.tsx                          # Updated with routes
├── App.css
└── main.tsx
```

---

## 10. Dependencies to Add

### Backend (`requirements.txt`)
```
# Existing
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-dotenv==1.0.0

# New — Phase 1
pandas>=2.1.0

# New — Phase 3
reportlab>=4.0

# New — Phase 5
langchain-core>=0.1.0
```

### Frontend (`package.json`)
```json
{
  "recharts": "^2.10.0",
  "react-to-print": "^2.15.0",
  "date-fns": "^3.0.0"
}
```

---

## 11. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Output format | Daily dashboard + PDF shift report | Covers real-time monitoring and 3-shift handover |
| Equipment scope | All 7 issue types | Comprehensive — all interconnected |
| Agent integration | LangChain placeholder with pre-defined tool schemas | Clean integration path without blocking MVP |
| Pilot job | **Job TK021** (74 days, 17,206 inventory txns) | Highest inventory density — best for testing chemical correlation |
| Language | **Bilingual** — English primary, Spanish terms preserved | Traceability of original item names + English explanations |
| Prescriptiveness | Explanations + directional guidance | Engineers make final call; system provides context |
| Shifts | 3 shifts: Day/Evening/Night (8h each) | Matches typical rig operations |
| Mud types | Both WBM and OBM — auto-detect and adapt | Database contains both; system must handle either |
| Users | Both rig-site operators and office engineers | Responsive UI for tablets + desktops |
| Deployment | Cloud Linux VPS | Production-ready, no local-only constraints |
| Auth | None for MVP — add later | Speed to MVP; security layer added in future phase |
| Chemical categorization | Custom regex pattern matcher | Products table only has 3 groups — insufficient |
| PDF library | reportlab | Mature, no system dependencies (vs weasyprint needing GTK) |
| Chart library | Recharts | React-native, lightweight, good for time series |
| Date handling | Parse OLE dates at query time, normalize to ISO | Avoids modifying source DB |
| DB access | Read-only connection to Wellstar.db | Source data must never be modified |
| Success criteria | NPT reduction, mud stability, chemical optimization, training, shift handover | All 5 selected — drives feature prioritization |

---

## 12. Database Performance Notes

**Recommended Indexes** (apply during Phase 1):
```sql
CREATE INDEX IF NOT EXISTS idx_equipment_job_date ON Equipment(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_sample_job_date ON Sample(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_concentaddloss_job_date ON ConcentAddLoss(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_report_job_date ON Report(Job, ReportDate);
CREATE INDEX IF NOT EXISTS idx_sample_time ON Sample(Job, ReportDate, SampleTime);
```
