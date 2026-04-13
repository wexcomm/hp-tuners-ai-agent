# Complete Tuning Workflow with Live Bridge 🏁

Step-by-step guide from stock tune to Stage 1, using the Live Tuning Bridge.

---

## Phase 1: Preparation (5 minutes)

### 1.1 Start the Live Bridge

Open a terminal/PowerShell and run:

```bash
cd c:\git\hp-tuners-ai-agent
python src/live_tuning_bridge.py
```

You'll see the bridge instructions and folder structure. Press Enter to start watching.

**Leave this window open** - the bridge is now running!

---

### 1.2 Open VCM Suite

1. Launch **VCM Editor** (for reading/flashing)
2. Launch **VCM Scanner** (for logging)
3. Connect your MPVI2 to the car's OBD-II port
4. Ignition ON, engine OFF

---

## Phase 2: Stock Backup (10 minutes)

### 2.1 Read Stock Tune

**In VCM Editor:**
1. Vehicle → Read → Read Entire
2. Wait for completion (5-10 minutes)
3. File → Save As:
   ```
   Stock_YOURVIN_YYYY-MM-DD.hpt
   Example: Stock_2G1WB5E37D1157819_2026-04-12.hpt
   ```
4. **Export CSV** (for AI analysis):
   - File → Export → Export as CSV
   - Save to: `bridge/stock/`

---

### 2.2 Baseline Log

**In VCM Scanner:**
1. Connect to vehicle
2. Select these PIDs (minimum):
   - Engine → RPM
   - Engine → Spark Advance
   - Engine → Knock Retard
   - Fuel → STFT Bank 1, STFT Bank 2
   - Fuel → LTFT Bank 1, LTFT Bank 2
   - Fuel → MAF
   - Transmission → Gear
   - Transmission → TCC Slip
   - Transmission → TFT (Fluid Temp)

3. Start Logging (F5 or red circle button)
4. **Drive the following cycle:**
   - Idle 3-5 minutes (warm up)
   - Normal city driving 5 minutes
   - Highway cruise 5 minutes
   - **3x WOT pulls**: From 2500 RPM to redline (safely!)
   - More city driving 5 minutes
   - Idle 2 minutes

5. Stop Logging (F5 or square button)
6. File → Save As:
   ```
   Baseline_Stock_YYYY-MM-DD.csv
   ```

---

## Phase 3: AI Tune Generation (2 minutes)

### 3.1 Drop Log for Analysis

1. Copy your `Baseline_Stock_*.csv` to:
   ```
   bridge/incoming/
   ```

2. **The bridge auto-analyzes!** Watch the console for:
   - RPM range detected
   - WOT events count
   - Knock analysis
   - Fuel trim recommendations

3. Find the analysis report in:
   ```
   bridge/incoming/analysis_Baseline_Stock_*.json
   ```

---

### 3.2 Generate Stage 1 Tune

**Option A: Quick Command**
```bash
# In a NEW terminal window (keep bridge running)
cd c:\git\hp-tuners-ai-agent
python src/live_tuning_bridge.py --quick YOURVIN --octane 93
```

**Option B: Request File**
Create `bridge/outgoing/my_tune.json`:
```json
{
  "vin": "2G1WB5E37D1157819",
  "octane": 93,
  "mods": ["intake", "exhaust"],
  "type": "stage1",
  "notes": "First Stage 1 attempt"
}
```

The bridge auto-detects and generates!

---

### 3.3 Review Generated Tune

Find your tune in:
```
bridge/outgoing/stage1_YOURVIN_93oct_TIMESTAMP/
```

Files created:
- `spark_main.csv` - Spark advance table
- `fuel_mass.csv` - Fuel injector pulse width
- `maf.csv` - MAF calibration (scaled for intake)
- `shift_normal.csv` - Normal mode shift points
- `shift_sport.csv` - Sport mode shift points
- `ve.csv` - Volumetric efficiency
- `knock_limit.csv` - Knock sensor limits
- `line_pressure.csv` - Transmission line pressure
- `power_enrichment.csv` - WOT fuel enrichment
- `tune.hpt.json` - Complete tune in JSON
- `tuning_report.json` - Human-readable summary

Open `tuning_report.json` to verify:
- Tables generated: 8
- Spark range: ~17-33° (good for 93 octane)
- Fuel mass: appropriate scaling
- Shift points: raised appropriately

---

## Phase 4: Import to VCM Editor (10 minutes)

### 4.1 Open Stock Tune

1. In VCM Editor: File → Open
2. Select your `Stock_*.hpt` file

---

### 4.2 Import Spark Table

**From bridge output → VCM Editor:**

1. Open `spark_main.csv` in Excel or Notepad
2. Select all (Ctrl+A), Copy (Ctrl+C)
3. In VCM Editor:
   - Navigate to: Engine → Spark → Main Spark Advance
   - Right-click the table → Select All
   - Right-click → **Paste Special** → **Values**
   - Click OK

⚠️ **Important**: Use "Paste Special → Values", not regular paste!

---

### 4.3 Import Fuel Table

1. Open `fuel_mass.csv`
2. Copy all values
3. In VCM Editor:
   - Navigate to: Engine → Fuel → Base Fuel Mass
   - Paste Special → Values

---

### 4.4 Import MAF Calibration

1. Open `maf.csv`
2. Copy values
3. In VCM Editor:
   - Navigate to: Engine → Airflow → MAF Calibration
   - Paste Special → Values

---

### 4.5 Import Shift Tables

**Normal Mode:**
1. Open `shift_normal.csv`
2. Copy values
3. VCM Editor: Transmission → Shift → Normal Mode Shift Speeds
4. Paste Special → Values

**Sport Mode:**
1. Open `shift_sport.csv`
2. Copy values  
3. VCM Editor: Transmission → Shift → Performance Mode Shift Speeds
4. Paste Special → Values

---

### 4.6 Save Your Tune

File → Save As:
```
Stage1_Intake_Exhaust_93oct_v1.hpt
```

---

## Phase 5: Flash the Tune (5 minutes)

### 5.1 Pre-Flash Checklist

Before flashing, verify:
- [ ] Stock tune backed up
- [ ] Battery voltage > 12V (ideally on charger)
- [ ] No DTCs present (or non-critical ones)
- [ ] Safe location, won't need to drive immediately
- [ ] Time to let idle 5+ minutes after flash

---

### 5.2 Flash Calibration

**In VCM Editor:**
1. Ensure tune is loaded (your Stage1 v1)
2. Vehicle → Write → **Write Calibration**
   
   ⚠️ **Use "Write Calibration" NOT "Write Entire"!**

3. Follow prompts:
   - Ignition ON, engine OFF
   - Click OK to start
   - Wait for progress bar (2-5 minutes)
   - When prompted: Cycle ignition OFF → ON
   - Wait for "Write Complete"

4. Close VCM Editor (or disconnect)

---

### 5.3 First Start

1. Start engine
2. Let idle **5 minutes minimum** - don't touch throttle!
3. Monitor for:
   - Check engine light
   - Rough idle
   - Strange noises
   - Coolant temp (let it warm up)

4. If all good: Gentle test drive
   - Light throttle first
   - Gradually increase
   - NO WOT yet!

---

## Phase 6: Verification (20 minutes)

### 6.1 Log Verification Data

**In VCM Scanner:**
1. Use same PID selection as baseline
2. Start logging
3. Drive cycle:
   - Idle 5 minutes
   - Normal driving 5 minutes
   - **3x WOT pulls** (same as before)
   - Normal driving 5 minutes
   - Idle 2 minutes

4. Stop logging
5. Save as:
   ```
   Verification_Stage1_v1_YYYY-MM-DD.csv
   ```

---

### 6.2 Analyze Results

**Drop the log into:**
```
bridge/incoming/
```

The bridge will auto-analyze and alert you to:
- Knock events (should be minimal)
- Fuel trims (should be closer to 0)
- WOT performance gains
- Any issues

**Compare to baseline:**
```python
# You can do this manually too
from enhanced_agent import analyze_log_file

baseline = analyze_log_file("bridge/archive/Baseline_Stock_*.csv")
stage1 = analyze_log_file("bridge/incoming/Verification_Stage1_v1_*.csv")

print(f"Baseline WOT events: {baseline['summary']['wot_events']}")
print(f"Stage 1 WOT events: {stage1['summary']['wot_events']}")
print(f"Baseline max knock: {baseline['summary']['knock_analysis']['max_retard']}")
print(f"Stage 1 max knock: {stage1['summary']['knock_analysis']['max_retard']}")
```

---

## Phase 7: Iterate (Optional)

### 7.1 If Knock Detected

1. Reduce timing in affected RPM range
2. Or generate new tune with `--octane 91` (more conservative)
3. Reflash and re-test

### 7.2 If Fuel Trims Off

1. Adjust MAF calibration manually
2. Or add more fuel to affected cells
3. Reflash and re-test

### 7.3 Version Your Tunes

Always increment version:
- `Stage1_v1.hpt` → `Stage1_v2.hpt`
- Keep notes on what changed
- Archive old versions

---

## Quick Reference

### Bridge Commands

```bash
# Start bridge (interactive)
python src/live_tuning_bridge.py

# Quick tune (no bridge needed)
python src/live_tuning_bridge.py --quick VIN --octane 93

# Show instructions
python src/live_tuning_bridge.py --instructions
```

### VCM Editor Import Checklist

| CSV File | VCM Editor Location |
|----------|---------------------|
| spark_main.csv | Engine → Spark → Main Spark Advance |
| fuel_mass.csv | Engine → Fuel → Base Fuel Mass |
| maf.csv | Engine → Airflow → MAF Calibration |
| shift_normal.csv | Transmission → Shift → Normal Mode |
| shift_sport.csv | Transmission → Shift → Performance Mode |
| ve.csv | Engine → Airflow → VE |
| knock_limit.csv | Engine → Spark → Knock Control |
| line_pressure.csv | Transmission → Pressure → Line Pressure |

### Safety Thresholds

| Parameter | Safe Range | Action if Exceeded |
|-----------|-----------|-------------------|
| Knock Retard | < 4° | Reduce timing 2-4° |
| STFT/LTFT | ±5% | Adjust MAF/fuel |
| TCC Slip | < 100 RPM | Increase line pressure |
| Trans Temp | < 220°F | Let cool down |

---

## Troubleshooting

### Bridge not detecting files?
- Ensure file extension is `.csv` (logs) or `.json` (requests)
- Check you're saving to correct folder
- Restart bridge if needed

### Import fails in VCM Editor?
- Use "Paste Special → Values" (NOT regular paste)
- Verify axis values match (RPM ranges, etc.)
- Check table dimensions are identical

### Flash fails?
- Battery voltage too low (charge it)
- Interruption during flash (DO NOT unplug MPVI2!)
- Try "Write Calibration" again

### Engine runs rough after flash?
- Let idle 5+ minutes (relearn)
- Check for DTCs
- Verify all tables imported correctly
- Revert to stock if concerned

---

## Success Checklist

After completing this workflow, you should have:

- [x] Stock tune backed up
- [x] Baseline log archived
- [x] Stage 1 tune generated by AI
- [x] Tune flashed successfully
- [x] Verification log showing improvements
- [x] No knock > 4°
- [x] Fuel trims within ±5%
- [x] Smooth idle and drivability
- [x] Noticeable performance gains!

---

**Happy Tuning!** 🏎️💨
