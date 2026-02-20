# Wellstar Mud Reports Database Overview

## Database Summary

**Database File:** `backend/db/Wellstar.db`  
**Size:** 2.2 GB (2,214,129,664 bytes)  
**Data Span:** 1993 - 2026 (33+ years)  
**Total Jobs:** 17,732+ unique drilling operations

---

## Dataset Types Available

### 1. **Sample Data** (434,943 total records)
- **403,457 records with depth correlation**
- Comprehensive mud properties at specific measured depths
- **Fields include:**
  - MDDepth & TVDDepth
  - Mud weight (PPG)
  - Funnel viscosity
  - Plastic viscosity & Yield point
  - Gel strengths (10 sec, 10 min, 30 min)
  - Filtrate (API & HTHP)
  - pH, alkalinity
  - Solids content & sand content
  - Rheometer readings (600/300/200/100/6/3 RPM)
  - Chemical analysis (chlorides, calcium, etc.)

### 2. **Daily Reports** (346,548 total records)
- **340,503 records with depth data**
- Daily drilling progress summaries
- **Fields include:**
  - Report date & number
  - MDDepth & TVDDepth
  - Present activity
  - Engineer, operator, contractor details
  - Rig number
  - Remarks & comments

### 3. **Mud Properties** (317,989 total records)
- Daily mud property ranges
- **Fields include:**
  - Weight ranges (Low/High)
  - Viscosity ranges (Low/High)
  - Filtrate measurements
  - Comments

### 4. **Inventory Transactions** (376,774 total records)
- Material additions and losses tracking
- **Fields include:**
  - Item name & type
  - Quantity, start, received amounts
  - Location
  - Mud weight at time of transaction
  - Notes

### 5. **Circulation Data** (325,908 total records)
- Hydraulics calculations and system parameters
- **Fields include:**
  - Mud volumes (hole, pits, riser, storage, reserve)
  - Pump parameters (A, B, C pumps - liner/stroke sizes)
  - Annular velocities
  - Circulation times & bottoms-up time
  - Pressures
  - Temperature gradients

### 6. **Whole Mud Composition** (5,292 records)
- Product usage tracking
- **Fields include:**
  - Product codes & names (Barite, CLS, etc.)
  - Quantities (pounds & barrels)
  - Specific gravity
  - Location & volume changes

### 7. **Rheology Data (HBRheology)** (31,093 records)
- High temperature/high pressure rheology measurements
- **31,091 records with depth data**
- **Fields include:**
  - MD & TVD
  - Mud weight, temperature, pressure
  - Viscometer readings at multiple RPMs

### 8. **Mud Volume Accounting** (33,540 records)
- Material inventory by item
- **Fields include:**
  - Start inventory, received, used, on hand
  - Total delivered
  - Daily losses & total losses

### 9. **Concentrations Input** (98,022 records)
- Daily volume reconciliation
- **Fields include:**
  - Water added (drill/sea)
  - Mud lost or dumped
  - Volume built/received by location
  - Barite, gel, oil additions
  - System reset tracking

### 10. **Mud Type Reference** (79 records)
- Reference data for mud systems
- Types include: Amvert, Attapulgite, Calcium Chloride, Coring Fluid, Eco-Drill, etc.

---

## Data Completeness Analysis

### Completeness Criteria

**High-Quality Complete Dataset Defined As:**
- ✅ 100+ depth-correlated samples
- ✅ 50+ daily reports with depth
- ✅ 50+ mud property records
- ✅ 100+ inventory transactions

### Jobs Meeting Completeness Criteria

| Completeness Level | Job Count |
|-------------------|-----------|
| **All 4 categories** (samples + reports + mud props + inventory) | **56 jobs** |
| Sample + Report + MudProp only | 265 jobs |
| Sample + Report + Inventory only | 56 jobs |
| Sample data with depth (100+) | 311 jobs |

---

## Top 20 Most Complete Jobs

Jobs ranked by total records across all dataset types:

| Rank | Job ID | Depth Samples | Sample Days | Daily Reports | Mud Props | Inventory | Circulation | Products | Total Records |
|------|--------|---------------|-------------|---------------|-----------|-----------|-------------|----------|---------------|
| 1 | TK021 | 201 | 74 | 74 | 74 | 17,206 | 74 | - | 17,629 |
| 2 | 220818 | 1,551 | 618 | 618 | 618 | 11,237 | 618 | 0 | 14,642 |
| 3 | BOL0029 | 706 | 473 | 473 | 473 | 11,718 | 473 | 28 | 13,843 |
| 4 | 1006WD | 125 | 64 | 64 | 64 | 13,496 | 64 | - | 13,813 |
| 5 | 22082918 | 684 | 617 | 618 | 617 | 10,280 | 617 | 6 | 12,816 |
| 6 | 05042021 | 719 | 302 | 302 | 302 | 5,042 | 302 | 0 | 6,667 |
| 7 | BOL-LQCX1 | 605 | 363 | 363 | 363 | 3,820 | 363 | 0 | 5,514 |
| 8 | 22102016 | 532 | 260 | 260 | 260 | 3,995 | 260 | 3 | 5,307 |
| 9 | BOL0030 | 397 | 231 | 231 | 231 | 3,334 | 231 | 3 | 4,424 |
| 10 | BOL0033 | 512 | 245 | 246 | 246 | 3,114 | 246 | 1 | 4,364 |
| 11 | BOL-0100 | 435 | 237 | 242 | 237 | 2,637 | 242 | 3 | 3,793 |
| 12 | 0024 | 471 | 230 | 230 | 219 | 2,636 | 230 | 0 | 3,786 |
| 13 | 29112017 | 490 | 165 | 165 | 165 | 2,237 | 165 | 3 | 3,222 |
| 14 | 015 | 339 | 187 | 197 | 186 | 1,925 | 198 | 0 | 2,845 |
| 15 | 0027 | 339 | 191 | 191 | 190 | 1,890 | 190 | 0 | 2,800 |
| 16 | 0013 | 322 | 141 | 142 | 142 | 1,420 | 141 | 0 | 2,167 |
| 17 | BOL 1000 | 274 | 147 | 147 | 145 | 1,365 | 145 | - | 2,076 |
| 18 | PLUSP 01 | 288 | 121 | 121 | 120 | 1,391 | 120 | - | 2,040 |
| 19 | BOL0017 | 199 | 127 | 127 | 127 | 1,300 | 127 | - | 1,880 |
| 20 | COSTY 28 | 319 | 108 | 107 | 108 | 1,217 | 108 | 18 | 1,859 |

### Depth Coverage Examples

Jobs with most extensive depth sampling:

| Job ID | Sample Count | Days | Depth Range (ft) | Avg Samples/Day |
|--------|-------------|------|------------------|-----------------|
| 220818 | 1,551 | 618 | 0 - 5,998 | 2.5 |
| 05042021 | 719 | 302 | 120 - 5,272 | 2.4 |
| BOL0029 | 706 | 473 | 0 - 4,625 | 1.5 |
| 22082918 | 684 | 617 | 0 - 5,998 | 1.1 |
| SO 3343 | 680 | 349 | 0 - 20,225 | 1.9 |
| BOL-LQCX1 | 605 | 363 | 0 - 4,562 | 1.7 |
| 00122481 | 602 | 305 | 0 - 22,400 | 2.0 |
| DMSL01158 | 545 | 290 | 0 - 32,448 | 1.9 |
| BOL0030 | 397 | 231 | 0 - 37,060 | 1.7 |

---

## Dataset Types by Job Category

### Jobs with ALL Dataset Types Available
(Samples, Reports, Mud Properties, Inventory, Circulation, Product Usage)

**56 jobs** have comprehensive data across all categories, suitable for:
- Time series analysis
- Depth correlation studies
- Inventory optimization
- Mud program evaluation
- Cost analysis
- Performance benchmarking

### Jobs Best Suited for Specific Analysis Types

#### **Depth vs Mud Properties Analysis**
- **403,457 depth-correlated samples** across 311+ jobs
- Best jobs: 220818, 05042021, BOL0029, 22082918

#### **Time Series Analysis**
- Jobs with 150+ days of continuous data
- Best jobs: 220818 (618 days), 22082918 (617 days), BOL0029 (473 days)

#### **Inventory & Cost Analysis**
- Jobs with 5,000+ inventory transactions
- Best jobs: TK021 (17,206), 1006WD (13,496), BOL0029 (11,718), 220818 (11,237)

#### **Hydraulics & Circulation Studies**
- 325,908 circulation records across multiple jobs
- Best jobs: 220818 (618), 22082918 (617), BOL0029 (473)

#### **Rheology Studies**
- 31,091 depth-correlated rheology measurements
- Temperature range: 63°F - 161°F
- Pressure conditions: various HTHP scenarios

---

## Recommended Jobs for Analysis

### Best Overall Dataset Quality (Top 5)

1. **220818** - Most balanced dataset
   - 1,551 depth samples over 618 days
   - Complete time series from surface to 5,998 ft
   - 11,237 inventory transactions
   - All dataset types present

2. **BOL0029** - Excellent long-term tracking
   - 706 samples over 473 days
   - 11,718 inventory transactions
   - Product usage data (28 records)
   - Depth range: 0 - 4,625 ft

3. **22082918** - Comprehensive daily data
   - 684 samples over 617 days
   - Excellent time-series continuity
   - 10,280 inventory transactions

4. **TK021** - Best for inventory analysis
   - 17,206 inventory transactions
   - 201 depth samples over 74 days
   - Complete circulation data

5. **05042021** - High-frequency sampling
   - 719 samples over 302 days (2.4 samples/day)
   - 5,042 inventory transactions
   - Depth range: 120 - 5,272 ft

---

## Notes

- All depth measurements provided in both MD (Measured Depth) and TVD (True Vertical Depth)
- Data quality varies by job - some older jobs (1993-2000s) may have incomplete fields
- Inventory transactions include both additions and losses
- Circulation data includes pump efficiency and hydraulics calculations
- Sample data includes both specification ranges and actual measured values

---

**Last Updated:** February 20, 2026  
**Database Version:** Wellstar.db (2.2 GB)
