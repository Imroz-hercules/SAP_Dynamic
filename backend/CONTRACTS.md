# Interface Contracts — static-to-dynamic migration

Written in commit 0, before branching. Two workstreams run in parallel with
exclusive file ownership. These are the only surfaces that cross the boundary.

**Change the implementation behind them freely. Do not change the contract
without agreeing it first** — each one has a caller in the other person's files.

---

## 1. `services/scale_service` — owned by Workstream B

Workstream A imports from this module in `routes/order_validation.py:5599`.

Frozen:

| Symbol | Contract |
|---|---|
| `get_scada_reading(field_name, apply_reset=True)` | returns `float \| None` |
| `get_multiple_scada_readings(field_names, force_fresh=False, apply_reset=True)` | returns `{tag: {"current": float, "delta": float}}` |
| `calculate_deltas(equipment, baselines, order=None, db=None)` | returns `{tag: {"baseline", "current", "delta", "rollover"}}` |
| `sum_dm_readings_for_order(dm_tag, order)` | returns `float` |
| `MILLING_FIELDS`, `INPUT_FIELDS` | stay importable as lists of tag strings |

B is replacing the hardcoded field lists with the `scada_tags` table. That is
fine — populate the module-level names from the registry at import time so the
existing imports keep resolving. If a name has to go away, say so before
deleting it.

---

## 2. `classify_order(order)` — owned by Workstream A

Called from `routes/scada_routes.py:489`, which Workstream B owns.

Frozen:

- Must stay importable as `from routes.order_validation import classify_order`.
  A is free to move the implementation into `services/classification_service.py`
  and re-export it from the old location — but the import path stays valid.
- Return value stays a `dict` with these keys:

```
order_type     "MILLING" | "PACKING" | None
equipment      list[str]        main scales driving confirmed weight
formula        str              "" for PACKING
byproduct      dict             {"scale1": str|None, "scale2": ..., "scale3": ...}
packing_info   dict             {} for MILLING
error          str | None       set means classification failed; callers check this
```

Four other modules read this shape (`error_log_routes`, `process_order_pull`,
`scale_lock_service`, `scada_routes`), so the keys are load-bearing.

---

## 3. `services/auto_validator.py` — being retired by Workstream B

Not a frozen interface, listed so nobody is surprised when it disappears.

The module holds a second, unreachable `classify_order` with its own hardcoded
maps. Its only live export is `_convert_to_tons`, imported by
`routes/sap_sync.py:317` — a B-owned file. The module object is also imported at
`app.py:365`, likewise B-owned.

Nothing in Workstream A imports it, so B can relocate `_convert_to_tons` to a
shared util and delete the module without coordinating.

`test_imports.py` also references it and belongs to B for this purpose.

---

## Shared files

| File | Rule |
|---|---|
| `backend/app.py` | Blueprint registration and model imports were done once, in commit 0. Owned by B afterwards. A does not open it. |
| `setup_sap_postgres.sql` | All three new tables were added in commit 0. Further changes to **your** table go in your own `backend/migrate_*.py`. This file is reconciled once, at the end, in a single cleanup PR. |
| `backend/public/assets/**` | The compiled frontend is committed and **not** gitignored. Nobody commits a build during the sprint — one build at the end, from one machine. |

---

## Table ownership

| Table | Owner |
|---|---|
| `classification_rules` | A |
| `milling_version_mappings` | A |
| `palletizer_mapping` | A |
| `scada_tags` | B |
| `kpi_config` | B |
| `system_settings` | shared key-value store — use distinct keys, never rewrite the other's |
