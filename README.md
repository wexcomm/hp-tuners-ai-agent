# HP Tuners AI Agent 🤖🔧

A comprehensive Python-based AI agent for ECU tuning, transmission tuning, data logging, and vehicle diagnostics using HP Tuners and OBD-II protocols.

## 🎯 Features

- **ECU Operations**: Read/Write ECU parameters, backup/restore stock tunes
- **Transmission Tuning**: TCM control, shift points, line pressure, torque converter management
- **Data Logging**: Real-time OBD-II data capture with analysis
- **Vehicle-Specific Support**: LFX 3.6L V6 (2013 Chevrolet Impala) with Direct Injection monitoring
- **Safety Validation**: Pre-flash safety checks and post-tune verification
- **Wideband O2 Integration**: Support for external wideband sensors
- **HP Tuners Export**: Compatible tune file generation

## 🚗 Supported Vehicles

### GM Platforms
- **LFX 3.6L V6**: Chevrolet Impala (2013-2016), Camaro, Equinox, etc.
  - Direct Injection fuel system monitoring
  - High compression (12:1) knock analysis
  - Dual VVT tracking
  - 6T70 FWD transmission tuning

### Transmissions
- 6L80/6L90 (RWD 6-speed)
- 6T70 (FWD 6-speed)
- 8L90 (8-speed)
- 10L80 (10-speed)

## 📦 Installation

### Requirements
- Python 3.8+
- OBD-II Bluetooth or USB adapter (ELM327 compatible)
- HP Tuners VCM Suite (for ECU flashing)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### System Setup (Linux)
```bash
# For Bluetooth OBD-II adapters
sudo apt-get install bluetooth bluez

# USB serial permissions
sudo usermod -a -G dialout $USER
```

## 🚀 Quick Start

### Basic Usage
```python
from src.hp_tuners_agent import HPTunersAgent
from src.lfx_impala_controller import LFXImpalaController

# Connect to vehicle via Bluetooth OBD-II
agent = HPTunersAgent(port="/dev/rfcomm0")  # Bluetooth
agent.initialize()

# Read ECU information
info = agent.ecu.read_ecu_info()
print(f"VIN: {info.vin}")
print(f"Calibration: {info.calibration_id}")

# Backup stock tune
agent.backup_stock_tune()

# Log baseline data
print("Drive normally for 10 minutes including WOT...")
agent.log_baseline(duration=600)
```

### LFX Impala Specific
```python
# Add LFX-specific monitoring
lfx = LFXImpalaController(agent.ecu)

# Check maintenance items for your mileage
maintenance = lfx.check_maintenance_items(mileage=85000)
for item in maintenance:
    print(item)

# Get LFX-specific PIDs
pids = lfx.get_lfx_logging_pids()  # Includes HPFP, knock, VVT

# Log with LFX monitoring
log_data = agent.ecu.start_data_logging(pids, duration=600)

# Analyze LFX-specific parameters
fuel_analysis = lfx.analyze_lfx_fuel_system(log_data)
knock_analysis = lfx.analyze_lfx_knock(log_data)  # All 6 cylinders
vvt_analysis = lfx.analyze_vvt_operation(log_data)

# Generate Stage 1 tune (93 octane required for LFX)
tune = lfx.generate_stage1_lfx_tune(octane_rating=93)

# Export for HP Tuners Editor
agent.validate_and_export(tune, "lfx_stage1_93oct.json")
```

## 📊 Data Logging

### Essential PIDs
- **RPM**: Engine speed
- **SPEED**: Vehicle speed
- **MAF**: Mass airflow
- **O2_B1S1/B2S1**: Oxygen sensors
- **SHORT/LONG_FUEL_TRIM**: Fuel trim data
- **SPARK_ADV**: Spark advance
- **KNOCK**: Knock retard

### LFX-Specific PIDs
- **HPFP_PRESSURE**: High Pressure Fuel Pump (critical for direct injection)
- **INJECTOR_DUTY**: Fuel injector duty cycle
- **CYLINDER_HEAD_TEMP**: CHT monitoring
- **KNOCK_RETARD_CYL1-6**: Individual cylinder knock
- **VVT_INTAKE/EXHAUST**: Cam position tracking
- **FUEL_TRIM_CELL**: GM-specific fuel trim cells

## 🔧 Tuning Workflows

### Stage 1: Bolt-Ons (Intake/Exhaust)
```python
# Generate tune for intake + exhaust modifications
tune = lfx.generate_stage1_lfx_tune(octane_rating=93)

# Expected gains: +10-15 HP
# - MAF scaling +8-12%
# - Spark advance +3-4° (93 octane only)
# - Shift points +400 RPM
# - Line pressure 85→90 PSI
```

### Safety Validation
```python
from src.safety_validator import SafetyValidator

validator = SafetyValidator()
result = validator.validate_flash(tune, ecu_info, backups_dir)

if not result["safe_to_flash"]:
    print("Safety issues:")
    for warning in result["recommendations"]:
        print(f"  ⚠️ {warning}")
```

## 🛡️ Safety Features

### Pre-Flash Checklist
- ✅ Stock tune backup verification
- ✅ Fuel system capacity check (injector duty <85%)
- ✅ Spark advance limits verification
- ✅ HPFP pressure monitoring (DI engines)
- ✅ Knock sensor validation
- ✅ Rev limiter safety

### LFX-Specific Warnings
- ⚠️ **93 Octane Required**: 12:1 compression, no timing advance on 87
- ⚠️ **HPFP Monitoring**: $800+ part if overworked
- ⚠️ **Carbon Buildup**: Check at 60k+ miles (DI engines)
- ⚠️ **VVT Tracking**: Clogged solenoid screens common
- ⚠️ **6T70 Limit**: 350 lb-ft max input torque

## 📖 Documentation

- [LFX Tuning Guide](docs/references/lfx_tuning_guide.md) - Comprehensive LFX tuning manual
- [HP Tuners Tables](docs/references/hp_tuners_tables.md) - Table reference guide
- [Skill Documentation](docs/SKILL.md) - Full capability documentation

## 🔌 Hardware Requirements

### OBD-II Adapters
- **Bluetooth**: ELM327 Bluetooth adapter (Android/Linux compatible)
- **USB**: ELM327 USB with FTDI or CP2102 chipset
- **WiFi**: Compatible but not recommended for tuning

### HP Tuners Interface
- **MPVI2**: Required for ECU flashing
- **Pro Feature Set**: Needed for some advanced logging

## 🧪 Testing

Run tests:
```bash
pytest tests/
```

## 🤝 Contributing

Contributions welcome! Please ensure:
- Code follows PEP 8
- Include tests for new features
- Update documentation
- Test on actual vehicle before submitting

### Areas for Contribution
- Additional vehicle platforms (Ford, Mopar, etc.)
- More transmission support (10-speed, dual-clutch)
- Enhanced data analysis algorithms
- GUI/web interface
- Mobile app integration

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

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- HP Tuners for the VCM Suite software
- python-obd library contributors
- EFI University for tuning education resources
- GM LFX community for platform knowledge

## 📞 Support

- GitHub Issues: [Report bugs/request features](https://github.com/YOUR_USERNAME/hp-tuners-ai-agent/issues)
- HP Tuners Forums: [www.hptuners.com/forums](https://www.hptuners.com/forums)
- Impala Forums: [www.impalaforums.com](https://www.impalaforums.com)

---

**⚠️ WARNING**: This software is for educational and research purposes. Vehicle modifications may violate emissions laws or void warranties. Always comply with local regulations and manufacturer guidelines.