# Quick Start: Using AI Agent with HP Tuners

Get started with AI-assisted tuning in 10 minutes.

---

## 🎯 The Basic Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  1. READ STOCK    →    2. LOG DATA     →    3. AI ANALYSIS  │
│     (VCM Editor)       (VCM Scanner)        (AI Agent)      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. AI GENERATES  →    5. IMPORT      →    6. FLASH        │
│     TUNE FILES         (VCM Editor)      (VCM Editor)       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  7. VERIFY        →    DONE!                                │
│     (AI Agent)                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Setup (One Time)

### 1. Install Python Dependencies
```bash
cd c:\git\hp-tuners-ai-agent
pip install -r requirements.txt
```

### 2. Verify HP Tuners
- Open VCM Editor → Help → About (should show 5.x)
- Connect MPVI2 to PC
- Verify vehicle license available

---

## 🚀 Option 1: Complete Workflow (With Vehicle)

### Step 1: Run the Example Script
```bash
# Navigate to examples
cd c:\git\hp-tuners-ai-agent\examples

# Run complete workflow
python stage1_workflow_example.py
```
cd c:\git\hp-tuners-ai-agent\examples

This will:
1. ✅ Connect to your vehicle
2. ✅ Check for DTCs
3. ✅ Log baseline data
4. ✅ Analyze with AI
5. ✅ Generate Stage 1 tune files
6. ✅ Guide you through flashing
7. ✅ Verify after flash

---

## 🚀 Option 2: Step-by-Step Manual Workflow

### STEP 1: Read Stock Tune (VCM Editor)
```
1. Connect MPVI2 to car OBD-II port
2. Ignition ON, engine OFF
3. VCM Editor → Vehicle → Read → Read Entire
4. Save: Stock_[YourVIN]_[Date].hpt
5. Export CSV: File → Export → Export as CSV
```

### STEP 2: Log Baseline Data (VCM Scanner)
```
1. Open VCM Scanner
2. Connect to vehicle
3. Select PIDs:
   - Engine > RPM, Spark Advance, Knock Retard
   - Fuel > STFT/LTFT Bank 1 & 2
   - Transmission > Gear, TCC Slip
4. Start logging (F5)
5. Drive: Idle 5min → Normal driving → 3x WOT pulls → Highway
6. Save: Baseline_[Date].csv
```

### STEP 3: Analyze with AI Agent
```python
from src.enhanced_agent import EnhancedHPTunersAgent

agent = EnhancedHPTunersAgent()
agent.initialize()

# Pre-tune check
result = agent.pre_tune_diagnostic()
print(f"Safe to tune: {result['safe_to_tune']}")

# Analyze your VCM Scanner log
results = agent.import_vcm_scanner_log(
    "C:/Users/WexCo/Documents/HP Tuners/Logs/Baseline_2026-04-11.csv"
)

print(f"WOT Events: {results['summary']['wot_events']}")
print(f"Max Knock: {results['summary']['knock_analysis']['max_retard']}°")

# See AI recommendations
for rec in results['recommendations']:
    print(f"[{rec['priority']}] {rec['action']}")
```

### STEP 4: Generate Stage 1 Tune
```python
# Create tune
hpt = agent.create_stage1_tune_package(
    octane=93,
    mods=["intake", "exhaust"]
)

# Export CSV tables for VCM Editor
agent.export_tune("./tunes/stage1", format="all")
```

**Output:** `tunes/stage1/csv_tables_*/`
- `spark_main.csv`
- `fuel_mass.csv`
- `maf.csv`
- `shift_normal.csv`
- `shift_sport.csv`

### STEP 5: Import to VCM Editor
```
For each CSV file:

1. VCM Editor: Open stock tune
2. Navigate to matching table:
   - spark_main.csv → Engine > Spark > Main Spark Advance
   - fuel_mass.csv → Engine > Fuel > Base Fuel Mass
   - maf.csv → Engine > Airflow > MAF Calibration
   - shift_*.csv → Transmission > Shift > [Normal/Performance]

3. Right-click table → Copy
4. Open CSV in Excel/Notepad
5. Select all, Copy
6. Back to VCM Editor: Right-click → Paste Special → Values
```

### STEP 6: Flash Tune
```
1. VCM Editor: File → Save As
   Name: Stage1_Intake_Exhaust_93oct_[Date].hpt

2. Vehicle → Write → Write Calibration
   (NOT Write Entire!)

3. Follow prompts:
   - Ignition ON, engine OFF
   - Wait for completion
   - Cycle ignition when instructed
```

### STEP 7: Verify with AI
```python
# After flashing
agent.clear_dtcs()

# Log verification data
agent.log_with_preset("lfx_full", duration=600, 
                      output="./logs/verify.csv")

# Check for issues
results = agent.import_vcm_scanner_log("./logs/verify.csv")

if results['summary']['knock_analysis']['max_retard'] > 4:
    print("⚠️ Reduce timing 2-4°")
    
if results['summary']['fuel_analysis']['correction_needed']:
    print("⚠️ Adjust MAF calibration")

codes = agent.read_dtcs()
if codes:
    print(f"⚠️ New DTCs: {[c['code'] for c in codes]}")
```

---

## 🔧 Common Quick Tasks

### Quick: Generate Tune Without Vehicle
```python
from src.enhanced_agent import quick_stage1_tune

# Generate tune files (no car needed)
tune_path = quick_stage1_tune(
    vin="2G1WB5E37D1157819",
    octane=93,
    output_dir="./tunes"
)

print(f"Tune ready at: {tune_path}")
```

### Quick: Analyze Log File
```python
from src.enhanced_agent import analyze_log_file

results = analyze_log_file("path/to/your/log.csv")

print(f"Knock events: {results['summary']['knock_analysis']['total_events']}")
for rec in results['recommendations']:
    print(f"[{rec['priority']}] {rec['action']}")
```

### Quick: Look Up a DTC
```python
from src.enhanced_agent import EnhancedHPTunersAgent

agent = EnhancedHPTunersAgent()
dtc = agent.lookup_dtc("P0171")

print(f"{dtc['code']}: {dtc['description']}")
print(f"Causes: {dtc['possible_causes']}")
print(f"Fix before tuning: {dtc['tuning_related']}")
```

---

## 📊 What the AI Analyzes

### From Your Logs, AI Detects:
| Issue | AI Action |
|-------|-----------|
| Knock > 4° | Recommend timing reduction |
| Fuel trim > ±10% | Suggest MAF/fuel adjustments |
| WOT AFR lean | Alert to add fuel |
| High trans slip | Recommend pressure increase |
| New DTCs | Flag for investigation |

### AI Generates:
- ✅ Spark tables (optimized for your octane)
- ✅ MAF calibration (scaled for your intake)
- ✅ Fuel mass tables
- ✅ Shift points (normal + sport modes)
- ✅ Line pressure adjustments

---

## ⚠️ Safety First

### Before Flashing:
```
□ Stock tune backed up
□ No critical DTCs present
□ Battery voltage > 12V
□ Coolant at operating temp
□ Safe location for test drive
□ Wideband O2 recommended
```

### After Flashing:
```
□ Idle stable 5 minutes
□ No check engine light
□ No strange noises
□ Gradual test drive first
□ Monitor knock retard
□ Check for new DTCs
```

---

## 🆘 Troubleshooting

### "Can't connect to vehicle"
```
1. Check MPVI2 USB cable
2. Ignition must be ON
3. Try different USB port
4. Check Windows Device Manager
```

### "AI can't read CSV"
```python
# Re-export from VCM Scanner with all PIDs
# Or fix format:
import pandas as pd
df = pd.read_csv("log.csv")
df.to_csv("log_fixed.csv", index=False)
```

### "Won't flash"
```
1. Use "Write Calibration" not "Write Entire"
2. Ensure battery voltage good
3. Close antivirus temporarily
4. Check vehicle license in VCM Suite
```

---

## 📖 Next Steps

- **Detailed Guide**: `docs/HP_TUNERS_WORKFLOW_GUIDE.md`
- **Example Script**: `examples/stage1_workflow_example.py`
- **PID Reference**: `docs/references/pid_database.md`

---

## 💡 Pro Tips

1. **Always log before and after** - Compare with AI to verify gains
2. **Start conservative** - First tune should be mild, verify then push
3. **One change at a time** - Don't change spark, fuel, AND transmission at once
4. **Monitor knock** - Knock retard > 6° = immediately revert to stock
5. **Keep backups** - Save every iteration: Stage1_v1, Stage1_v2, etc.

---

**Ready to tune?** Start with the example script:
```bash
python examples/stage1_workflow_example.py
```
