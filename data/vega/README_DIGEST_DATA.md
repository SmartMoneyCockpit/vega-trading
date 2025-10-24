# Owners Daily Digest — Data Files
This page reads/writes a few lightweight files. All paths are configurable via environment variables, but defaults are below.

```
data/vega/owners_tasks.json        # {"tasks":[{"text":"…","done":false}, ...]}
data/vega/owners_notes.md          # plain text notes
data/vega/pnl_today.json           # {"realized":0,"unrealized":0,"total":0,"currency":"USD","trades":0}
data/vega/health_today.json        # {"bp_sys":0,"bp_dia":0,"hr":0,"sleep_hours":0.0,"vagal_score":0}
data/vega/market_reports/morning.txt
data/vega/market_reports/evening.txt
```

## Environment overrides (optional)
- `VEGA_DATA_ROOT`
- `VEGA_TASKS_PATH`
- `VEGA_NOTES_PATH`
- `VEGA_PNL_TODAY_PATH`
- `VEGA_HEALTH_TODAY_PATH`
- `VEGA_MARKET_REPORTS_ROOT`

## Quick start
1. Drop the files in your project, keeping the same folder structure.
2. (Optional) Pre-seed `pnl_today.json` and `health_today.json` with today's values.
3. Open the **Owners Daily Digest** page — you should see KPI cards, Tasks, Notes, and report snapshots.
