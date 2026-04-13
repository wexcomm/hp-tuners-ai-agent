# TOPDON RLink X3 Setup Guide

## Your Device

**TOPDON RLink X3** (Corded) - J2534-1/J2534-2 PassThru Device

### Specifications

| Feature | Specification |
|---------|--------------|
| Manufacturer | TOPDON |
| Model | RLink X3 |
| Connection | USB (Corded) |
| J2534 Version | 1.04 / 2.02 |
| CAN Bus | 125k, 250k, 500k, 1M baud |
| Protocols | CAN, ISO15765, J1850VPW, J1850PWM, ISO9141, ISO14230 |
| Programming Voltage | Yes (Pin 13, up to 20V) |

### Software Installation

Your software is installed at:
```
C:\Program Files\TOPDON
```

This contains the J2534 drivers and configuration tools.

## Quick Start

### 1. Verify Installation

Run the analyzer to check your setup:

```bash
# Double-click this file in the project folder:
analyze_topdon.bat

# Or from command line:
python skills/j2534_passthru/device_configs/topdon_analyzer.py
```

This will:
- Find your TOPDON installation
- Locate the J2534 DLL
- Check USB connection
- Generate a configuration file

### 2. Test Connection

```bash
python -m skills.j2534_passthru test
```

### 3. Get ECU Info

```bash
python -m skills.j2534_passthru info
```

## Using with Your LFX Impala (2013)

### Connection Steps

1. **Connect RLink X3 to PC** via USB
2. **Connect to vehicle OBD-II port**
3. **Ignition ON** (engine off for reading, on for some operations)
4. **Verify battery voltage** > 12V

### Read Stock Flash

```bash
python -m skills.j2534_passthru read_flash stock_backup.bin --platform GM_E37
```

This reads the complete 1MB flash from your E37 ECU.

### Flash Modified Tune

```bash
python -m skills.j2534_passthru flash stage1.bin --platform GM_E37
```

### Live Data Logging

```bash
python -m skills.j2534_passthru log --duration 60 --output log.json
```

## RLink X3 Specific Settings

### For GM E37 (Your LFX 3.6L)

```python
from skills.j2534_passthru import J2534PassThru
from skills.j2534_passthru.device_configs.topdon_rlink import TopdonRLinkX3Device

# Get RLink-specific config
rlink = TopdonRLinkX3Device()
config = rlink.get_flash_config("GM_E37")

# Use with PassThru
pt = J2534PassThru()
pt.open()

# Connect with RLink-optimized settings
channel = pt.connect_can(baud_rate=config['baud_rate'])

# Enable programming voltage for flashing
pt.set_programming_voltage(
    pin_number=config['voltage_pin'],
    voltage=config['programming_voltage']  # 18000 = 18V
)
```

### Configuration Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| CAN Baud Rate | 500000 | Standard GM CAN speed |
| Programming Voltage | 18V | Required for flash mode |
| Voltage Pin | 13 | OBD-II pin for programming |
| Block Size | 1024 bytes | Optimal for E37 |
| Connect Timeout | 10 seconds | Allow time for ECU to respond |

## Troubleshooting

### "DLL not found"

1. Check that TOPDON software is installed:
   ```
   C:\Program Files\TOPDON
   ```

2. Look for files named:
   - `rlinkj2534.dll`
   - `j2534.dll`
   - Any DLL in the TOPDON folder

3. If not found, reinstall TOPDON software from the manufacturer's website

### "Device not connected"

1. Check USB connection (try different port)
2. Check Windows Device Manager for "TOPDON" or "RLink"
3. Install/update drivers from TOPDON software
4. Try running as Administrator

### "Cannot communicate with vehicle"

1. Verify ignition is ON
2. Check OBD-II connection firmly seated
3. Verify battery voltage > 12V
4. Try disconnecting/reconnecting
5. Some vehicles need key cycled: OFF → ON → wait 3 sec → connect

### Programming Voltage Issues

The RLink X3 supports programming voltage on OBD-II pin 13, which GM ECUs need for flashing.

If flash fails:
- Verify voltage is being applied (should see 18V)
- Try longer delay after voltage on (1000ms instead of 500ms)
- Some ECUs are picky about voltage timing

## Python API Examples

### Complete Read-Modify-Flash Workflow

```python
from skills.j2534_passthru import J2534PassThru, FlashManager
from skills.j2534_passthru.device_configs.topdon_rlink import TopdonRLinkX3Device
from skills.hpt_converter import HPTBuilder, ChecksumValidator

# 1. Read stock flash
pt = J2534PassThru()
pt.open()
flash = FlashManager(pt)
flash.set_platform("GM_E37")
flash.backup_flash("stock_backup.bin")
pt.close()

# 2. Modify tune
builder = HPTBuilder(platform="GM_E37", vin="YOURVIN")
builder.load_base_binary("stock_backup.bin")
builder.set_rev_limit(7000)
builder.save("stage1.bin", fix_checksums=True)

# 3. Validate
validator = ChecksumValidator("GM_E37")
report = validator.validate_binary("stage1.bin")
assert report.overall_valid, "Checksums invalid!"

# 4. Flash to ECU
pt.open()
flash.flash_binary("stage1.bin", verify=True)
pt.close()

print("Success!")
```

### Using RLink-Specific Features

```python
from skills.j2534_passthru.device_configs.topdon_rlink import TopdonRLinkX3Device

# Get device info
rlink = TopdonRLinkX3Device()
info = rlink.get_device_info()
print(f"Device: {info['name']}")
print(f"DLL: {info['dll_path']}")
print(f"Connected: {info['connected']}")

# Get optimized settings for your platform
config = rlink.get_flash_config("GM_E37")
print(f"Baud Rate: {config['baud_rate']}")
print(f"Prog Voltage: {config['programming_voltage']}mV")
```

## Data Collection

To help improve RLink X3 support, please share:

1. **Run the analyzer** and share `topdon_rlink_config.json`
2. **DLL location** if different from expected paths
3. **Successful operations** - what worked with your vehicle
4. **Any issues** encountered

### Run Diagnostics

```bash
# Full device analysis
python skills/j2534_passthru/device_configs/topdon_analyzer.py

# Test connection
python -m skills.j2534_passthru test

# Get ECU info
python -m skills.j2534_passthru info
```

## References

- [TOPDON Official Website](https://www.topdon.com/)
- [J2534 Standard](https://www.sae.org/standards/content/j2534_1_202002/)
- GM E37 ECM Documentation (community)

## Safety Notes

⚠️ **Important**:
- Always backup stock flash before modifying
- Maintain battery voltage > 12V during flash
- Don't disconnect during flash operation
- Use at your own risk
