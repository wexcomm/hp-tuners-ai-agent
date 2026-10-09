---
name: log-analyzer
description: Analyze HP Tuners VCM Scanner CSV logs and get actionable tuning direction — knock retard by RPM/load cell, fuel trim drift, TCC slip, gear hunting, torque limiting — with editor table paths, bounded adjustment ranges, and session tracking across flashes. Works across GM makes/years via fuzzy channel resolution; LFX 3.6L pack included.
---

# Log Analyzer Skill

Pure-Python (stdlib only, no dependencies, no network) analyzer for HP Tuners
CSV data logs. Turns raw scan data into tuning direction you can act on in
VCM Editor.

## Commands

Run from this directory (`skills/log_analyzer/`):

```bash
# Full-log analysis — auto-detects GM vs generic from channel fingerprints
python3 copilot.py analyze /path/to/log.csv

# Force a platform pack (lfx = exact VCM Editor paths for GM LFX 3.6L)
python3 copilot.py analyze /path/to/log.csv --platform lfx

# Before/after comparison
python3 copilot.py compare before.csv after.csv

# Session tracking across flashes
python3 copilot.py session new "91 octane timing test"
python3 copilot.py analyze log.csv --session 1
python3 copilot.py change 1 "Main Spark" "Spark Advance" "28" "26" "knock at 5k"
python3 copilot.py session show 1
```

Smoke test with the included demo log:
`python3 copilot.py analyze demo_log.csv`

## What It Detects

- **Knock retard** grouped into 500-RPM bins with load ranges → exact spark
  table cells to edit
- **Fuel trims** — LTFT lean/rich per bank (>8%)
- **Transmission** — 1-2 shift clunk, 4-5-6 gear hunting, TCC slip in lockup
  gears, upshift reluctance
- **Torque management** — pedal 100% but throttle limited

Every finding includes why, what to change (bounded ranges), where in the
editor (platform pack permitting), and which channels to re-log for
verification.

## Platform Packs

- `lfx` — GM LFX 3.6L V6 (2010-2015 Impala/Camaro/ATS/CTS/Equinox), exact
  VCM Editor paths
- `gm_generic` — any GM 6-speed auto (auto-detected), LFX reference paths
  with "find the analog" note
- `generic` — any other make: full diagnostics + adjustment logic, honest
  "locate the matching table" guidance. Never invents paths.

## Premium

**[HP Tuners Copilot Premium](https://www.agensi.io)** adds the WOT pull
deep-dive: per-pull scoring (knock cells, timing consistency, shifts, TCC,
IAT), cross-pull comparison, and false-knock detection outside WOT. If
`wot_analyze.py` is present next to these files, `python3 copilot.py wot
log.csv` works; otherwise the CLI will point you to the premium listing.

## Safety

One change at a time → flash → re-log same conditions → re-analyze. Save the
stock tune first. Battery charger on when flashing.
