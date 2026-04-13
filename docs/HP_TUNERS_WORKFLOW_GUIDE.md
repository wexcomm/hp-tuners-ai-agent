# HP Tuners AI Agent + VCM Suite Workflow Guide

Complete guide for using the AI Agent with HP Tuners VCM Suite 5.x

---

## 🔄 Workflow Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   HP Tuners     │────▶│   AI Agent       │────▶│   HP Tuners     │
│   VCM Editor    │     │   (Analysis)     │     │   VCM Editor    │
│   (Read ECU)    │     │                  │     │   (Flash ECU)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                       ▲
         │                       ▼                       │
         │              ┌──────────────────┐            │
         │              │  VCM Scanner     │            │
         └─────────────▶│  (Data Logging)  │────────────┘
                        └──────────────────┘
```

**The Cycle:**
1. **Read** stock tune from ECU using VCM Editor
2. **Log** baseline data using VCM Scanner
3. **Analyze** logs with AI Agent
4. **Generate** tune with AI Agent
5. **Import** tune tables into VCM Editor
6. **Flash** modified tune to ECU
7. **Verify** with new logs

---

## 📋 Prerequisites

### Hardware Required
- HP Tuners MPVI2 interface (or MPVI2+)
- Windows PC with VCM Suite installed
- OBD-II cable (included with MPVI2)
- Optional: Wideband O2 sensor (recommended for tuning)

### Software Required
- HP Tuners VCM Suite 5.x (VCM Editor + VCM Scanner)
- Python 3.8+ with AI Agent installed
- Vehicle license credits on your MPVI2

### File Paths (Default)
```
HP Tuners:
  C:\Users\[Username]\Documents\HP Tuners\Tunes\
  C:\Users\[Username]\Documents\HP Tuners\Logs\

AI Agent:
  c:\git\hp-tuners-ai-agent\
```

---

## 🎯 Step-by-Step Workflow

### Phase 1: Stock Baseline

#### Step 1: Read Stock Tune (VCM Editor)
```
1. Open VCM Editor
2. Connect MPVI2 to vehicle OBD-II port
3. Vehicle → Read → Read Entire
4. Save as: Stock_[VIN]_[Date].hpt
5. File → Export → Export as CSV (for AI analysis)
   Location: Documents\HP Tuners\Tunes\
```

#### Step 2: Baseline Data Logging (VCM Scanner)
```
1. Open VCM Scanner
2. Connect to vehicle
3. Select PIDs:
   - Engine > RPM, Spark Advance
   - Engine > Knock Retard
   - Fuel > Fuel Trim Bank 1/2
   - Fuel > Injector Duty Cycle (GM Extended)
   - Transmission > Gear, TCC Slip
   
4. Logging → Start Recording
5. Drive cycle:
   - 5 min idle
   - Normal driving 0-50 mph
   - 3x WOT pulls from 2500-6500 RPM
   - Highway cruise
6. Save log: Baseline_[Date].csv
```

#### Step 3: Run AI Pre-Tune Diagnostic
```python
from src.enhanced_agent import EnhancedHPTunersAgent

agent = EnhancedHPTunersAgent(port="COM3")  # MPVI2 port
agent.initialize()

# Run pre-tune diagnostic
result = agent.pre_tune_diagnostic()

print(f"Safe to tune: {result['safe_to_tune']}")
for warning in result['warnings']:
    print(f"⚠️ {warning}")

# If DTCs present, check details
codes = agent.read_dtcs()
for code in codes:
    print(f"{code['code']}: {code['description']}")
```

---

### Phase 2: AI Analysis & Tune Generation

#### Step 4: Import VCM Scanner Log to AI
```python
# Analyze the baseline log
results = agent.import_vcm_scanner_log(
    "C:/Users/WexCo/Documents/HP Tuners/Logs/Baseline_2026-04-11.csv"
)

# View analysis
print(f"WOT Events: {results['summary']['wot_events']}")
print(f"Max Knock: {results['summary']['knock_analysis']['max_retard']}°")
print(f"Fuel Trim: {results['summary']['fuel_analysis']['stft_avg']:.1f}%")

# View AI recommendations
for rec in results['recommendations']:
    print(f"[{rec['priority']}] {rec['action']}")
```

#### Step 5: Generate Stage 1 Tune
```python
# Create Stage 1 tune based on logs
hpt = agent.create_stage1_tune_package(
    octane=93,
    mods=["intake", "exhaust"]
)

# Export for HP Tuners
exported = agent.export_tune(
    output_dir="./tunes/stage1",
    format="all"  # JSON + CSV tables
)

print(f"Files exported:")
for key, path in exported.items():
    print(f"  {key}: {path}")
```

**Output Files:**
```
tunes/stage1/
├── tune_20260411_143022.hpt.json     # AI format
├── tuning_report_20260411_143022.json # Analysis
└── csv_tables_20260411_143022/
    ├── spark_main.csv                 # Import to VCM Editor
    ├── fuel_mass.csv
    ├── maf.csv
    ├── shift_normal.csv
    └── shift_sport.csv
```

---

### Phase 3: Import to VCM Editor

#### Step 6: Import CSV Tables to VCM Editor
```
For each table you want to modify:

1. VCM Editor: Open your stock tune file
2. Navigate to table (e.g., Engine > Spark > Main Spark Advance)
3. Right-click table → Copy
4. Open AI-generated CSV (e.g., spark_main.csv)
5. Select all data in CSV (Ctrl+A)
6. Copy (Ctrl+C)
7. Back to VCM Editor: Right-click → Paste Special → Values
8. Verify changes look reasonable
```

**Tables to Import:**

| CSV File | VCM Editor Location | Notes |
|----------|---------------------|-------|
| `spark_main.csv` | Engine > Spark > Main Spark Advance | Verify 93 octane values |
| `fuel_mass.csv` | Engine > Fuel > Base Fuel Mass | Check MAF scaling first |
| `maf.csv` | Engine > Airflow > MAF Calibration | For intake modifications |
| `shift_normal.csv` | Transmission > Shift > Normal | Daily driving |
| `shift_sport.csv` | Transmission > Shift > Performance | Sport mode |
| `line_pressure.csv` | Transmission > Pressure > Line Pressure | Firmer shifts |

#### Step 7: Manual Review & Adjustments
```
CRITICAL: Review these tables before flashing!

1. Spark Advance:
   - Max should not exceed 35-40° at high load
   - Check knock sensor is enabled
   
2. Fuel Mass:
   - Verify MAF calibration if intake modified
   - Check PE (Power Enrichment) is 12.0:1 - 12.5:1
   
3. Torque Limits:
   - Ensure within transmission rating
   - 6T70 max: ~350 lb-ft input
   
4. Rev Limiter:
   - Set 200-400 RPM below mechanical limit
   - LFX: 6800-7000 RPM soft limit
```

---

### Phase 4: Flash & Verify

#### Step 8: Save and Flash Tune
```
1. VCM Editor: File → Save As
   Name: Stage1_[ModList]_[Octane]_[Date].hpt
   
2. Vehicle → Write → Write Calibration
   (NOT Write Entire - only change calibration)
   
3. Follow prompts:
   - Ignition ON, engine OFF
   - Wait for write complete
   - Cycle ignition as instructed
```

#### Step 9: Verify with AI Agent
```python
# After flashing, verify with new logs

# Clear any old DTCs
agent.clear_dtcs()

# Log verification data
agent.log_with_preset(
    preset="lfx_full",
    duration=600,
    output="./logs/stage1_verification.csv"
)

# Import and analyze
results = agent.import_vcm_scanner_log("./logs/stage1_verification.csv")

# Check for issues
if results['summary']['knock_analysis']['max_retard'] > 4:
    print("⚠️ Knock detected - reduce timing 2-4°")
    
if results['summary']['fuel_analysis']['correction_needed']:
    print("⚠️ Fuel trims off - adjust MAF or fuel mass")

# Check for new DTCs
codes = agent.read_dtcs()
if codes:
    print(f"⚠️ New DTCs after flash: {[c['code'] for c in codes]}")
```

---

## 🔄 Advanced Workflows

### Workflow A: MAF Calibration Only
```python
# For intake modifications without other changes

# 1. Log stock baseline
agent.log_with_preset("baseline", duration=300)

# 2. Install new intake

# 3. Log with new intake
agent.log_with_preset("baseline", duration=300, output="./logs/with_intake.csv")

# 4. Generate MAF calibration only
from src.table_templates import MAFCalibrationGenerator

maf = MAFCalibrationGenerator.generate_maf_calibration(
    tube_diameter_mm=90,  # Your intake diameter
    calibration_type="intake_modified"
)

# 5. Export and import single table
# Import only maf.csv to VCM Editor

# 6. Verify fuel trims are within ±5%
```

### Workflow B: Knock Analysis & Timing Adjustment
```python
# If knock detected during logging

results = agent.import_vcm_scanner_log("./logs/wot_pull.csv")
knock = results['summary']['knock_analysis']

if knock['max_retard'] > 4:
    # Reduce timing based on knock amount
    reduction = knock['max_retard'] + 2  # Extra safety margin
    
    print(f"Reduce spark advance by {reduction}° in affected RPM range")
    
    # Generate revised spark table
    from src.table_templates import SparkTableGenerator
    
    # Create modifier function to reduce timing
    def reduce_timing(value, rpm, load):
        if load > 60:  # High load only
            return value - reduction
        return value
    
    spark = SparkTableGenerator.generate_main_spark_table(octane=93)
    revised = spark.modify(reduce_timing)
    
    # Export and flash revised tune
```

### Workflow C: Transmission Tuning
```python
# Focus on transmission only

# 1. Log with transmission preset
agent.log_with_preset("transmission", duration=300)

# 2. Check shift times and TCC slip
results = agent.import_vcm_scanner_log("./logs/trans.csv")
trans = results['summary']['trans_analysis']

print(f"Shift count: {trans['gear_changes']}")
print(f"Max TCC slip: {trans['max_slip']} RPM")
print(f"Trans temp: {trans['avg_temp']:.1f}°C")

# 3. Generate shift tables
from src.table_templates import TransmissionTableGenerator

# Sportier shifts
shifts = TransmissionTableGenerator.generate_shift_table(
    trans_type="6t70",
    style="sport",
    rpm_increase=400
)

# Firmer pressure
pressure = TransmissionTableGenerator.generate_line_pressure_table()

# 4. Export and flash only transmission tables
```

---

## 📊 File Format Reference

### HPT JSON Format (AI Export)
```json
{
  "Metadata": {
    "CreatedBy": "HP Tuners AI Agent",
    "Version": "1.0",
    "Platform": "GM_E37"
  },
  "Vehicle": {
    "VIN": "2G1WB5E37D1157819",
    "CalibrationID": "12653917"
  },
  "Tables": {
    "Spark Advance 93oct": {
      "TableName": "Spark Advance 93oct",
      "RowAxis": {"Values": [800, 1000, ...], "Units": "RPM"},
      "ColAxis": {"Values": [20, 40, ...], "Units": "%"},
      "Data": [[18.0, 22.0, ...], ...],
      "Units": "Degrees"
    }
  }
}
```

### CSV Format (VCM Editor Import)
```csv
Engine Load\Engine Speed,800,1000,1500,2000
20,18.0,22.0,26.0,28.0
40,16.0,20.0,24.0,26.0
60,14.0,18.0,22.0,24.0
```

### VCM Scanner Export Format
```csv
Time,Engine RPM,Knock Retard,Fuel Trim Cell
0.0,750.0,0.0,14.0
0.5,1520.0,0.0,14.5
1.0,2450.0,0.0,15.0
```

---

## ⚠️ Safety Checklist

### Before Flashing ANY Tune
```
□ Stock tune backed up and saved
□ DTCs checked and cleared if needed
□ All fluids at proper levels
□ Fuel quality verified (93 octane if required)
□ Coolant temp at operating temperature
□ Wideband O2 installed (recommended)
□ Helper present for first drive
□ Safe location for test drive
□ Emergency contact aware
```

### After Flashing
```
□ Idle stable for 5 minutes
□ No check engine light
□ No unusual noises
□ Test drive: gradual acceleration first
□ Log data during first drive
□ Verify no new DTCs
□ Check knock retard during WOT
□ Verify fuel trims within ±10%
□ Trans shifts properly
□ Return to stock if ANY concerns
```

---

## 🛠️ Troubleshooting

### VCM Editor Won't Connect
```
1. Check MPVI2 drivers installed
2. Verify ignition ON, engine OFF
3. Try different USB port
4. Check Windows Device Manager for errors
5. Restart VCM Editor
```

### AI Agent Can't Import CSV
```python
# If CSV import fails, check format

# Re-export from VCM Scanner:
# File → Export → CSV (All PIDs)

# Or use pandas to fix format
import pandas as pd
df = pd.read_csv("log.csv", skiprows=1)  # Skip header if needed
df.to_csv("log_fixed.csv", index=False)
```

### Tune Won't Flash
```
1. Verify battery voltage > 12V
2. Close all other programs
3. Disable antivirus temporarily
4. Use "Write Calibration" (not Write Entire)
5. Check VCM Editor has vehicle license
6. Try writing one table at a time
```

### Knock After Flashing
```python
# Immediate action
codes = agent.read_dtcs()
if any('knock' in c['description'].lower() for c in codes):
    print("STOP - Revert to stock tune!")
    
# Check logs for knock retard
results = agent.import_vcm_scanner_log("./logs/latest.csv")
if results['summary']['knock_analysis']['max_retard'] > 6:
    print("CRITICAL: Severe knock - revert to stock immediately!")
```

---

## 📞 Quick Reference

### Common Commands
```python
from src.enhanced_agent import EnhancedHPTunersAgent, quick_stage1_tune, analyze_log_file

# Quick workflow
agent = EnhancedHPTunersAgent()
agent.initialize()

# 1. Pre-tune check
diag = agent.pre_tune_diagnostic()

# 2. Log baseline
agent.log_with_preset("lfx_full", duration=600)

# 3. Generate tune
hpt = agent.create_stage1_tune_package(octane=93)
agent.export_tune("./tunes")

# 4. Verify
results = agent.import_vcm_scanner_log("./logs/verify.csv")
```

### VCM Suite Quick Keys
```
VCM Editor:
  Ctrl+R = Read Vehicle
  Ctrl+W = Write Vehicle
  Ctrl+S = Save Tune
  Ctrl+F = Find Table
  F2 = Compare Tunes

VCM Scanner:
  F5 = Start Logging
  F6 = Stop Logging
  Ctrl+E = Export CSV
```

---

**Remember:** The AI Agent assists your tuning decisions but YOU are responsible for safe operation. When in doubt, be conservative!
