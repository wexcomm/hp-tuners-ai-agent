# HP Tuners AI Agent v2.0 🤖🔧

A comprehensive Python-based AI agent for ECU tuning, transmission tuning, data logging, and vehicle diagnostics using HP Tuners and OBD-II protocols.

## ✨ What's New in v2.0

### 📝 Native HP Tuners Integration
- **HPT File Export**: Generate native `.hpt.json` files compatible with VCM Editor
- **VCM Scanner Import**: Parse and analyze CSV logs exported from VCM Scanner
- **Table Templates**: Pre-built tuning tables for Stage 1, bolt-ons, and more
- **Tune Comparison**: Diff tool to compare two calibrations

### 🔄 HPT Converter Skill (NEW!)
- **Extract Binary**: Convert .hpt → .bin for use with other tools
- **Create HPT**: Convert .bin → .hpt to import external calibrations
- **Binary Analysis**: Compare tunes at byte level
- **Batch Processing**: Convert entire folders at once
- **Cross-Platform**: Works with TunerCat and other tuning software

### 🔌 J2534 PassThru Skill (NEW!)
- **Direct Flashing**: Flash .bin files directly to ECU (no HP Tuners needed!)
- **Read ECU Memory**: Backup stock tune directly from ECU
- **Real-Time Logging**: High-speed data logging (100+ PIDs/sec)
- **Device Support**: TOPDON RLink X3 ✅, Tactrix OpenPort, DrewTech, Ford VCI, and more
- **See**: `J2534_DEVICE_SETUP.md` for your specific device configuration

### 📊 Comprehensive PID Database
- **200+ PIDs**: Standard OBD-II + GM Mode 22 extended parameters
- **LFX V6 Specific**: Individual cylinder knock, HPFP, VVT monitoring
- **Logging Presets**: Pre-configured PID sets for different scenarios
- **Smart Recommendations**: AI-powered tuning suggestions from log analysis

### 🔧 Enhanced Tuning Workflows
- **One-Click Stage 1**: Generate complete tunes for common modifications
- **Safety Validation**: Automatic checks before exporting
- **MAF/VE Generators**: Auto-scale for different intake configurations
- **Transmission Tables**: Shift points and line pressure optimization

---

## 🎯 Features

- **ECU Operations**: Read/Write ECU parameters, backup/restore stock tunes
- **Transmission Tuning**: TCM control, shift points, line pressure, torque converter management
- **Data Logging**: Real-time OBD-II data capture with analysis
- **Vehicle-Specific Support**: LFX 3.6L V6 (2013 Chevrolet Impala) with Direct Injection monitoring
- **Safety Validation**: Pre-flash safety checks and post-tune verification
- **Wideband O2 Integration**: Support for external wideband sensors
- **HP Tuners Export**: Native .HPT file generation for VCM Editor
- **HPT Converter**: Convert between .hpt/.bin/.hex/.json formats (see skills/hpt_converter/)
- **Checksum Validator**: Verify and fix ECM calibration checksums
- **J2534 PassThru**: Direct ECU flashing with PassThru devices (see skills/j2534_passthru/)

---

## 🚗 Supported Vehicles

### GM Platforms
- **LFX 3.6L V6**: Chevrolet Impala (2013-2016), Camaro, Equinox, etc.
  - Direct Injection fuel system monitoring
  - High compression (12:1) knock analysis
  - Dual VVT tracking
  - 6T70 FWD transmission tuning
- **LS3/L99 6.2L V8**: Camaro SS, Corvette, G8 GXP
- **L83/L86 5.3L/6.2L**: Silverado, Sierra, Tahoe

### Transmissions
- 6T70/6T75 (FWD 6-speed)
- 6L80/6L90 (RWD 6-speed)
- 8L90 (8-speed)
- 10L80 (10-speed)

---

## 📦 Installation

### Requirements
- Python 3.8+
- OBD-II Bluetooth or USB adapter (ELM327 compatible)
- HP Tuners VCM Suite (for ECU flashing)

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Quick Start

### Basic Usage
```python
from src.enhanced_agent import EnhancedHPTunersAgent

# Connect to vehicle
agent = EnhancedHPTunersAgent(port="/dev/rfcomm0")  # Bluetooth
agent.initialize()

# Read ECU information
info = agent.ecu.read_ecu_info()
print(f"VIN: {info.vin}")
print(f"Calibration: {info.calibration_id}")

# Backup stock tune
agent.backup_stock_tune()
```

### Create Stage 1 Tune (Intake + Exhaust)
```python
from src.enhanced_agent import quick_stage1_tune

# Generate without vehicle connection
tune_path = quick_stage1_tune(
    vin="2G1WB5E37D1157819",
    octane=93,
    output_dir="./tunes"
)
print(f"Tune exported to: {tune_path}")
```

### Analyze VCM Scanner Log
```python
from src.enhanced_agent import analyze_log_file

# Analyze HP Tuners VCM Scanner CSV export
results = analyze_log_file("./logs/wot_pull.csv")

print("Summary:")
print(f"  WOT Events: {results['summary']['wot_events']}")
print(f"  Knock Events: {results['summary']['knock_analysis']['total_events']}")

print("\nRecommendations:")
for rec in results['recommendations']:
    print(f"  [{rec['priority']}] {rec['category']}: {rec['action']}")
```

---

## 📊 Data Logging

### Using PID Presets
```python
# Log with predefined PID sets
agent.log_with_preset("baseline", duration=600)      # Essential PIDs
agent.log_with_preset("performance", duration=300)   # Full performance
agent.log_with_preset("lfx_full", duration=600)      # Complete LFX monitoring
```

### PID Presets Available
| Preset | Description | PIDs | Rate |
|--------|-------------|------|------|
| `baseline` | Essential baseline | 14 | 0.5s |
| `performance` | Performance tuning | 17 | 0.1s |
| `lfx_full` | Complete LFX V6 | 33 | 0.1s |
| `transmission` | Trans diagnostics | 13 | 0.2s |

### Custom PID List
```python
from src.pid_database import PIDDatabase

db = PIDDatabase()

# Search for PIDs
knock_pids = db.search("knock")
for pid in knock_pids:
    print(f"{pid.short_name}: {pid.name} ({pid.unit})")

# Get LFX-specific list
lfx_pids = db.get_lfx_logging_pids()
print(f"Total LFX PIDs: {len(lfx_pids)}")
```

---

## 🔧 Tuning Workflows

### Complete Stage 1 Workflow
```python
from src.enhanced_agent import EnhancedHPTunersAgent

agent = EnhancedHPTunersAgent()
agent.initialize()

# 1. Backup stock tune
agent.backup_stock_tune()

# 2. Log baseline (WOT pulls, daily driving)
agent.log_with_preset("lfx_full", duration=600, 
                      output="./logs/baseline.csv")

# 3. Create Stage 1 tune
hpt = agent.create_stage1_tune_package(
    octane=93,
    mods=["intake", "exhaust"]
)

# 4. Export in multiple formats
exported = agent.export_tune("./tunes/stage1", format="all")
# Generates: .hpt.json, .csv tables, tuning report

# 5. Flash with HP Tuners Editor, then re-log
# 6. Validate results
results = agent.import_vcm_scanner_log("./logs/stage1_verification.csv")
```

### Table Template Generator
```python
from src.table_templates import (
    SparkTableGenerator, FuelTableGenerator,
    MAFCalibrationGenerator, TransmissionTableGenerator
)

# Generate spark table for 93 octane
spark = SparkTableGenerator.generate_main_spark_table(
    base_curve="gm_lfx_stock",
    octane_rating=93
)

# Generate MAF for cold air intake
maf = MAFCalibrationGenerator.generate_maf_calibration(
    tube_diameter_mm=90,
    calibration_type="intake_modified"
)

# Generate performance shift points
shifts = TransmissionTableGenerator.generate_shift_table(
    trans_type="6t70",
    style="sport",
    rpm_increase=400
)
```

---

## 🛡️ Safety Features

### Pre-Flash Validation
```python
from src.enhanced_agent import EnhancedHPTunersAgent

agent = EnhancedHPTunersAgent()
agent.initialize()

# Create tune
hpt = agent.create_stage1_tune_package(octane=93)

# Validate against logged data
validation = agent.validate_against_logs(
    hpt, 
    log_file="./logs/verification.csv"
)

if not validation["valid"]:
    print("Issues found:")
    for issue in validation["issues"]:
        print(f"  ⚠️ {issue}")
```

### Automatic Safety Checks
- ✅ Stock tune backup verification
- ✅ Fuel system capacity (injector duty <85%)
- ✅ Spark advance limits (max 45°)
- ✅ Rev limiter safety (< 7500 RPM)
- ✅ HPFP pressure monitoring (DI engines)
- ✅ Knock sensor validation

---

## 📁 File Formats

### HPT JSON Export
```json
{
  "Metadata": {
    "CreatedBy": "HP Tuners AI Agent",
    "Version": "1.0",
    "Date": "2026-04-11T12:00:00",
    "Platform": "GM_E37"
  },
  "Vehicle": {
    "VIN": "2G1WB5E37D1157819",
    "CalibrationID": "12653917"
  },
  "Tables": {
    "Spark Advance 93oct": {
      "TableName": "Spark Advance 93oct",
      "Category": "Engine - Spark",
      "RowAxis": {"Values": [800, 1000, ...], "Units": "RPM"},
      "ColAxis": {"Values": [20, 40, ...], "Units": "%"},
      "Data": [[18.0, 22.0, ...], ...],
      "Units": "Degrees"
    }
  }
}
```

### CSV Table Export
Each table exports as CSV for easy import to HP Tuners Editor:
```csv
Engine Load\Engine Speed,800,1000,1500,...
20,18.0,22.0,26.0,...
40,16.0,20.0,24.0,...
```

---

## 📖 Documentation

- [PID Database](docs/references/pid_database.md) - Complete PID reference
- [Table Templates](docs/references/table_templates.md) - Tuning table guide
- [LFX Tuning Guide](docs/references/lfx_tuning_guide.md) - LFX 3.6L specific
- [HP Tuners Tables](docs/references/hp_tuners_tables.md) - Table reference

---

## 🔌 Hardware Requirements

### OBD-II Adapters
- **Bluetooth**: ELM327 Bluetooth adapter (Android/Linux compatible)
- **USB**: ELM327 USB with FTDI or CP2102 chipset
- **WiFi**: Compatible but not recommended for tuning

### HP Tuners Interface
- **MPVI2**: Required for ECU flashing
- **Pro Feature Set**: Needed for advanced logging (Mode 22 PIDs)

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Test specific module
pytest tests/test_pid_database.py
pytest tests/test_table_templates.py
```

---

## 🤝 Contributing

Contributions welcome! Areas for contribution:
- Additional vehicle platforms (Ford, Mopar, etc.)
- More transmission support (10-speed, dual-clutch)
- Enhanced data analysis algorithms
- GUI/web interface
- Mobile app integration

---

## ⚠️ Disclaimer

**ECU tuning modifies critical vehicle safety systems. Improper tuning can cause:**
- Engine damage or failure
- Transmission damage
- Loss of vehicle control
- Voided warranty

**Always:**
- Start with conservative changes
- Monitor engine parameters continuously
- Use quality fuel (93 octane minimum for LFX timing advance)
- Have mechanical knowledge or professional assistance
- Follow manufacturer guidelines and local laws
- **LFX engines are interference design - valve-to-piston contact possible if timing wrong**

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 📞 Support

- GitHub Issues: [Report bugs/request features](https://github.com/wexcomm/hp-tuners-ai-agent/issues)
- HP Tuners Forums: [www.hptuners.com/forums](https://www.hptuners.com/forums)
- Impala Forums: [www.impalaforums.com](https://www.impalaforums.com)

---

**⚠️ WARNING**: This software is for educational and research purposes. Vehicle modifications may violate emissions laws or void warranties. Always comply with local regulations and manufacturer guidelines.
