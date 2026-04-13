# Live Tuning Bridge 🌉

Real-time file synchronization between the HP Tuners AI Agent and VCM Suite.

## What It Does

The Live Tuning Bridge watches folders and automatically:
- **Exports tunes** in VCM Editor compatible formats (CSV/JSON)
- **Imports VCM Scanner logs** and provides instant analysis
- **Alerts on critical issues** (knock, lean conditions, etc.)
- **Archives processed files** for record keeping

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Bridge

```bash
# Interactive mode with instructions
python src/live_tuning_bridge.py

# Or use the Windows batch file
start_bridge.bat
```

### 3. Generate a Tune

**Option A: Quick Generate**
```bash
python src/live_tuning_bridge.py --quick YOURVIN --octane 93
```

**Option B: Request File**
Create `bridge/outgoing/request.json`:
```json
{
  "vin": "2G1WB5E37D1157819",
  "octane": 93,
  "mods": ["intake", "exhaust"],
  "type": "stage1"
}
```

The bridge will auto-detect and generate the tune.

### 4. Import to VCM Editor

Find your tune in `bridge/outgoing/`:
- `spark_main.csv` → Copy to VCM Editor → Engine > Spark > Main Spark Advance
- `fuel_mass.csv` → Engine > Fuel > Base Fuel Mass  
- `maf.csv` → Engine > Airflow > MAF Calibration
- `shift_normal.csv` → Transmission > Shift > Normal Mode
- `shift_sport.csv` → Transmission > Shift > Performance Mode

### 5. Analyze Logs

Simply drop your VCM Scanner CSV export into:
```
bridge/incoming/
```

The bridge will:
- Analyze knock events
- Check fuel trims
- Detect WOT pulls
- Generate recommendations
- Alert on critical issues

## Folder Structure

```
bridge/
├── outgoing/          # AI-generated tunes (copy to VCM Editor)
├── incoming/          # Drop VCM Scanner CSVs here
├── stock/             # Place stock .hpt exports here (future feature)
└── archive/           # Processed files moved here
```

## Configuration

### Custom Directories

```python
from live_tuning_bridge import LiveTuningBridge, BridgeConfig

config = BridgeConfig(
    bridge_dir="C:/Tuning/Bridge",
    outgoing_dir="C:/Tuning/ToVCM",
    incoming_dir="C:/Tuning/FromVCM",
    knock_threshold=3.0,      # More sensitive
    fuel_trim_threshold=3.0   # More sensitive
)

bridge = LiveTuningBridge(config)
bridge.start()
```

### Alert Thresholds

| Setting | Default | Description |
|---------|---------|-------------|
| `knock_threshold` | 4.0° | Alert if knock retard exceeds this |
| `fuel_trim_threshold` | 5.0% | Alert if fuel trim exceeds this |

## Python API

### Quick Generate
```python
from live_tuning_bridge import LiveTuningBridge

bridge = LiveTuningBridge()
output_dir = bridge.quick_generate(
    vin="2G1WB5E37D1157819",
    octane=93,
    mods=["intake", "exhaust"]
)
```

### Create Request File
```python
bridge.create_tune_request(
    vin="YOURVIN",
    octane=91,
    mods=["intake", "headers"],
    tune_type="stage1"
)
```

### Run Bridge
```python
bridge = LiveTuningBridge()
bridge.start()  # Press Ctrl+C to stop
```

## Workflow Examples

### Complete Stage 1 Workflow

```bash
# 1. Start the bridge
python src/live_tuning_bridge.py

# 2. In another terminal, generate tune
python src/live_tuning_bridge.py --quick YOURVIN --octane 93

# 3. Copy CSV files from bridge/outgoing/ to VCM Editor

# 4. Flash with VCM Editor

# 5. Log with VCM Scanner

# 6. Drop CSV into bridge/incoming/

# 7. Review analysis and recommendations
```

### Iterative Tuning

```bash
# Make changes, export from VCM Scanner
cp wot_pull_v2.csv bridge/incoming/

# Bridge analyzes instantly
# Check recommendations
# Adjust tune
# Repeat until perfect
```

## Troubleshooting

### Bridge not detecting files?
- Check that file extensions are `.csv` (logs) or `.json` (requests)
- Ensure files are fully written before moving to watched folder
- Check folder permissions

### Analysis shows no data?
- Verify CSV format matches VCM Scanner export
- Check that required PIDs were logged (RPM, Throttle Position, etc.)

### Import to VCM Editor fails?
- Ensure you're using "Paste Special → Values" in VCM Editor
- Verify axis values match (RPM ranges, load percentages)
- Check that table dimensions match

## Tips

1. **Use the batch files** on Windows for one-click operation
2. **Pin the bridge folder** to File Explorer for quick access
3. **Set up a hotkey** to copy latest CSV to incoming folder
4. **Archive important logs** before they get auto-moved

## Command Line Reference

```bash
# Show instructions
python src/live_tuning_bridge.py --instructions

# Quick generate tune
python src/live_tuning_bridge.py --quick VIN --octane 93 --mods intake exhaust

# Run bridge with custom config (via Python)
python -c "from live_tuning_bridge import *; LiveTuningBridge(BridgeConfig(knock_threshold=2.0)).start()"
```
