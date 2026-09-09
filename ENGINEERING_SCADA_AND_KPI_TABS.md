# Engineering: SCADA Tags & KPI Limits

**Audience:** plant engineers / admins using Hercules SFMS  
**Where:** Sidebar → **Engineering** → tabs **SCADA Tags** and **KPI Limits**  
**Related code:** `scada_tags` / `kpi_config` tables, `scada_tag_registry.py`, `kpi_config_registry.py`

This document explains **what these tabs are for**, **how data flows**, and **what each field means** — so you know when to edit them and what breaks if you get them wrong.

---

## Why these tabs exist

Before Workstream B, scale names, counter wrap points, and KPI ceilings lived as **hardcoded lists in Python**. Changing a tag or a max value meant editing code and restarting the app.

Now that configuration lives in **Postgres** and is edited from Engineering:

| Tab | Database table | Job |
|-----|----------------|-----|
| **SCADA Tags** | `scada_tags` | Define *which* plant instruments exist and how the system reads them |
| **KPI Limits** | `kpi_config` | Define *how calculated KPIs are named, stored, and capped* |

Both registries are cached (~30 seconds). After you save in the UI, the backend invalidates cache so pollers, emulator, and KPI calc pick up changes without a full redeploy (you may still wait a few seconds for the next poll/calc cycle).

```
┌─────────────────┐     CRUD      ┌──────────────────┐
│ Engineering UI  │ ────────────► │ Postgres         │
│ Tags / KPI tabs │               │ scada_tags       │
└─────────────────┘               │ kpi_config       │
                                  └────────┬─────────┘
                                           │ registry read (cached)
           ┌───────────────────────────────┼───────────────────────────────┐
           ▼                               ▼                               ▼
   SCADA poll / live UI            Demo emulator                    KPI calculation
   (scale_service,                 (seeds, categories,              (ceilings / clamp,
    scheduler, Live Monitor)        totalizer toggles)               snapshot columns)
```

---

## Part 1 — SCADA Tags tab

### Purpose in one sentence

A **SCADA tag** is the system’s official name for one instrument (scale, meter, palletizer, counter). The registry tells every part of the app: *what it is called, which PLC/SQL column to read, how to interpret the number, and whether to use it*.

### What uses the tag registry

| Consumer | How it uses tags |
|----------|------------------|
| **SQL Server / ASM poll** | Only `is_pollable` + `is_active` tags are pulled into live readings |
| **Live Monitor / live tables** | Lists and categories come from the registry |
| **Demo Mode emulator** | Seeds (`emulator_seed`), categories, and which totalizers exist |
| **Order tracking / baselines** | Tag names must match process-order baseline columns and material mappings |
| **KPI formulas** | Formulas still refer to logical tags like `WG201`, `WG501` — those tags must exist and be active to get real numbers |

If a physical scale exists on the plant but is **missing or inactive** in this table, the app will not poll it reliably, demo won’t simulate it correctly, and KPIs that depend on it may stay at 0.

### Categories (plant areas)

| Category | Typical tags | Meaning |
|----------|--------------|---------|
| **INPUT** | WG101–WG302 | Wheat / screenings input scales |
| **MILLING** | WG501–WG503 | Flour and bran production scales |
| **WATER** | DM101–DM203 | Water dosing meters |
| **PACKING** | PL*_TOT, SL*_TOT, SL*_COUNTER | Palletizers and bag counters |
| **DAMAGED** | SL*_DAMAGED | Damaged-bag quality counters |

These categories also drive Demo Mode’s **Totalizer Configuration** groups (colors/names come from registry metadata).

### Reading types (how a raw value is interpreted)

This is the most important technical field on a tag.

| `reading_type` | What it means | Example |
|----------------|---------------|---------|
| **`hi_lo`** | Value is split across high and low words in the archive (`TAG_HI` + `TAG_LO`). The app combines them into one cumulative totalizer. | `WG501` → `WG501_HI` / `WG501_LO` |
| **`single`** | One cumulative column as-is. | `PL601_TOT`, `SL601_DAMAGED` |
| **`average`** | Source is a short-interval average (e.g. 30s); the system must **sum** samples over time for consumption, not treat one sample as a totalizer. | `DM101` water meters |

Wrong reading type → wrong totals, broken order progress, or nonsense water consumption.

### Field-by-field (SCADA Tags form)

| Field | Purpose |
|-------|---------|
| **Tag** | Stable logical ID used everywhere in code and mappings (`WG501`, `PL601_TOT`). Must be unique. Changing it is like renaming a foreign key — update mappings too. |
| **Display name** | Human label in UI (“Bakery flour stream”). Does not change calculations. |
| **Category** | Which plant area / Demo totalizer group. |
| **Reading type** | `hi_lo` / `single` / `average` (see above). |
| **Source column** | Exact column name in the SCADA archive table (`ASMArchive_DB5` or configured source). For `hi_lo`, this is usually the **base** name (`WG501`), not `_HI`/`_LO`. Spelling/case must match the PLC export. |
| **Unit** | Display/metadata (`TON`, `m3`, `BAG`, `PALLET`). |
| **Emulator seed** | Starting cumulative value when Demo Mode resets to “realistic”. Production MSSQL does not use this. |
| **Sort order** | Display order in lists and Demo grids. |
| **Active** | If off, treated as unused (not for live logic / KPIs that require active tags). Counters were historically seeded inactive until verified. |
| **Pollable** | If off, scheduler skips polling this tag even if active. Use when a row must exist for mapping but should not be read every cycle. |

Related (in DB; may not all be on the simple form): **`rollover_max`** — when a counter wraps (e.g. LO word at 1 000 000, palletizer at 100 000). Used so deltas stay correct after wrap. `NULL` = no wrap handling.

### Typical workflows

**Add a new scale the plant just commissioned**

1. Confirm the archive column name from the PLC/SCADA export.  
2. Engineering → **SCADA Tags** → fill Tag, category, reading type, source column, unit, rollover if needed.  
3. Set **Active** + **Pollable**.  
4. If orders use that scale, add/update **material / palletizer mapping** so process orders know which tag to baseline.  
5. In Demo Mode, set a sensible **emulator seed** and toggle the totalizer on.

**Temporarily ignore a broken instrument**

- Uncheck **Active** (or Pollable) rather than deleting — keeps history and mappings intact.

**Delete a tag**

- Only if nothing references it (mappings, baselines, formulas). Prefer deactivate.

### API (for reference)

- `GET /api/scada-config/tags` — list (optional `?category=`)  
- `POST /api/scada-config/tags` — create or upsert by tag key  
- `DELETE /api/scada-config/tags/{id}`

---

## Part 2 — KPI Limits tab

### Purpose in one sentence

A **KPI definition** describes one calculated performance metric: its stable key, screen name, department, which snapshot column stores it, and an optional **ceiling** so bad/noisy inputs cannot publish absurd percentages or rates to operators or SAP.

### What KPIs are (vs SCADA tags)

| | SCADA Tags | KPI Limits |
|---|------------|------------|
| Data kind | **Measured** instrument totals | **Calculated** performance numbers |
| Example | `WG202` = clean wheat tonnage | `flour_extraction_pct` = (WG501+WG502)/WG202 × 100 |
| Edited to… | Match the physical plant / PLC | Match business targets and reporting caps |

Tags feed the math; KPI config shapes the **outputs**.

### What uses `kpi_config`

| Consumer | How it uses definitions |
|----------|-------------------------|
| **KPI calculation** (`kpi_routes`) | After computing a value, applies `clamp(kpi_key, value)` → `min(value, max_value)` when `max_value` is set |
| **KPI snapshots / flat store** | `display_name` → `target_column` map so named results land in the right DB columns |
| **Screens / SAP send** | Keys and labels stay consistent with what Engineering defined |

### Departments

- **MILLING** — throughput, extraction, screening, water, hours, etc.  
- **PACKING** — line capacity, daily bags, machine utilization, hours, etc.

### Field-by-field (KPI Limits form)

| Field | Purpose |
|-------|---------|
| **KPI key** | Stable ID used in code (`flour_extraction_pct`). Must match what the calculator looks up for clamping. Do not rename casually. |
| **Display name** | Label shown in UI / reports (“Flour Extraction (%)”). Also used when mapping into snapshot columns. |
| **Department** | `MILLING` or `PACKING`. |
| **Target column** | Column in `milling_kpi_snapshots` / `packing_kpi_snapshots` (or related store). `NULL` for display-only / derived metrics that are not persisted that way. |
| **Max / target (`max_value`)** | **Ceiling** applied after calculation. Example: mill throughput clamped at **100**. `NULL` = uncapped (e.g. milling loss %, raw hours). |
| **Unit** | `%`, `m3`, `hrs`, `bags/hr`, etc. |
| **Sort order** | Order on screens/lists. |
| **Active** | Inactive definitions are ignored for ceilings and display maps. |

### How clamping works (exact behaviour)

```text
raw = (calculated KPI)
if max_value is set and definition is active:
    published = min(raw, max_value)
else:
    published = raw
```

Examples from seed data:

| KPI key | Typical max | Why |
|---------|-------------|-----|
| `mill_throughput_pct` | 100 | Throughput % should not exceed 100% of nameplate |
| `flour_extraction_pct` | 85 | Plant expects extraction under this ceiling |
| `milling_gain_pct` | 120 | Allows modest over-100% mass balance noise |
| `packing_line_capacity_bags_hr` | 2000 | Caps unrealistic bag/hr spikes |
| `milling_loss_pct` / net hours | *(null)* | Left uncapped |

**Important:** Changing `max_value` changes **published** KPIs, not the underlying SCADA math. If operators see “stuck at 100%”, check whether the real calc is above the ceiling and the clamp is doing its job.

Nameplate throughput (t/h) used inside some formulas comes from **system setting** `mill_nameplate_tph` (default 25), not from this tab — keep that in mind when interpreting Mill Throughput %.

### Typical workflows

**Tighten a KPI so SAP never receives wild values**

1. Engineering → **KPI Limits** → find the key.  
2. Set **Max / target** to the agreed business ceiling.  
3. Leave Active on.  
4. Recalculate / refresh KPI screen and confirm values no longer exceed the cap.

**Add a new KPI definition for a future formula**

1. Add key + display name + department + target column (if storing).  
2. Wire the calculator in backend to use that `kpi_key` with `kpi_clamp(...)`.  
3. Until the formula exists, the row only documents intent — it will not invent numbers by itself.

**Hide a KPI without deleting history**

- Uncheck **Active**.

### API (for reference)

- `GET /api/kpi-config/definitions` — list (optional `?department=`)  
- `POST /api/kpi-config/definitions` — create or upsert by `kpi_key`  
- `DELETE /api/kpi-config/definitions/{id}`

---

## How the two tabs work together (end-to-end)

Example: **Flour Extraction %**

1. **SCADA Tags** ensure `WG202`, `WG501`, `WG502` are active, pollable, `hi_lo`, correct source columns.  
2. Poller / emulator updates cumulative tonnages.  
3. KPI engine computes `(WG501 + WG502) / WG202 * 100`.  
4. **KPI Limits** row `flour_extraction_pct` with `max_value = 85` clamps the result.  
5. Value is labeled “Flour Extraction (%)”, stored in `flour_extraction_pct` if mapped, shown on KPI screens, and optionally sent to SAP.

If step 1 is wrong, step 3 is 0 or nonsense.  
If step 4 is wrong, step 5 shows uncapped or over-capped numbers.

```
WG202 / WG501 / WG502  (tags)
        │
        ▼
   KPI formula
        │
        ▼
 flour_extraction_pct  clamp(max 85)
        │
        ▼
  UI / snapshot / SAP
```

---

## Demo Mode vs Production

| Mode | SCADA Tags | KPI Limits |
|------|------------|------------|
| **Demo** (`MSSQL_ENABLED=false`) | Emulator advances tags using seeds and totalizer on/off | Same ceilings apply to calculated KPIs |
| **Production** | Tags drive real archive polling | Same ceilings apply to calculated KPIs |

Editing tags in demo still writes to Postgres. Production plants should treat Active/Pollable/source_column changes as **operational config**, not playground edits.

---

## Safe editing checklist

**SCADA Tags**

- [ ] Tag name matches mappings and (for new hardware) archive column  
- [ ] Reading type matches how the PLC exposes the value  
- [ ] Rollover max matches the device wrap (if any)  
- [ ] Prefer deactivate over delete  
- [ ] After add: verify Live Monitor and (if used) order baselines  

**KPI Limits**

- [ ] Do not rename `kpi_key` unless code is updated  
- [ ] Set `max_value` only when business wants a hard ceiling  
- [ ] Use `NULL` max for metrics that must never be clipped  
- [ ] Confirm department and target_column before expecting snapshot storage  

---

## Seed baseline (what you should already have)

After `setup_sap_postgres.sql` / demo seed migrations, expect on the order of:

- **~28 SCADA tags** (input/milling/water/packing/damaged + packing counters)  
- **~19 KPI definitions** (milling + packing)

Counters (`SL60x_COUNTER`) may be inactive until verified against real archive data — that is intentional.

---

## Where to click

1. Log in as **admin**  
2. Sidebar → **Engineering**  
3. Tab **SCADA Tags** or **KPI Limits**  
4. Filter by category/department → Edit / Save / Delete  

Deep links:

- `/engineering?tab=tags`  
- `/engineering?tab=kpi`

---

## Related docs

- `STATIC_TO_DYNAMIC_PLAN.md` §5 — Workstream B task definitions  
- `WORKSTREAM_B_STATUS.md` — implementation status  
- `ENDPOINT_TO_DB_MAPPING.md` — API ↔ table mapping  
- `backend/CONTRACTS.md` — registry contracts for developers  
