name: "J2534 PassThru"
```
```
## What is J2534?

**SAE J2534** is a standard API for vehicle programming. PassThru devices are hardware interfaces that connect to your PC via USB and to the vehicle via OBD-II.

### Capabilities

| Feature | OBD-II Adapter | J2534 PassThru |
|---------|---------------|----------------|
| Read DTCs | ✅ Yes | ✅ Yes |
| Clear DTCs | ✅ Yes | ✅ Yes |
| Data Logging | ⚠️ Slow (~10 PIDs/sec) | ✅ Fast (~100+ PIDs/sec) |
| Read ECU Flash | ❌ No | ✅ Yes |
| Write ECU Flash | ❌ No | ✅ Yes |
| Direct Memory Access | ❌ No | ✅ Yes |
| Programming Voltage | ❌ No | ✅ Yes (pin 13) |

## Supported Devices

- **TOPDON RLink X3** (Affordable, popular - see device_configs/TOPDON_GUIDE.md)
- **Tactrix OpenPort 2.0** (Most popular, affordable)
- ** DrewTech Mongoose** (Professional grade)
- **Ford VCI / VCM II** (Bosch - see device_configs/FORD_VCI_GUIDE.md)
- **Bosch/VCI** (OEM grade)
- **Any J2534-1 or J2534-2 compliant device**

### TOPDON RLink X3 Users
Your device is auto-detected! Run the analyzer for detailed info:
```bash
# Using the batch file
double-click: analyze_topdon.bat

# Or Python directly
python skills/j2534_passthru/device_configs/topdon_analyzer.py
```

### Ford VCI Users
If you have a Ford VCI (VCM II), run the analyzer:
```bash
analyze_vci.bat
```
See `device_configs/FORD_VCI_GUIDE.md` for detailed setup instructions.

## Quick Start

```python
from skills.j2534_passthru import J2534PassThru, Protocol

# Connect to device
pt = J2534PassThru()
pt.open()

# Connect to vehicle (CAN bus)
channel = pt.connect(Protocol.CAN, baud_rate=500000)

# Read VIN
vin = pt.read_vin()
print(f"VIN: {vin}")

# Flash ECU (using your generated binary)
with open("stage1.bin", "rb") as f:
    binary_data = f.read()
    
pt.flash_ecu(binary_data, start_address=0x00000)

# Cleanup
pt.disconnect(channel)
pt.close()
```

## Protocols Supported

| Protocol | ID | Description |
|----------|-----|-------------|
| ISO9141 | 1 | K-line, older vehicles |
| ISO14230 (KWP2000) | 2 | Keyword Protocol 2000 |
| J1850PWM | 3 | Ford proprietary |
| J1850VPW | 4 | GM/Chrysler proprietary |
| CAN | 5 | Modern vehicles (most common) |
| ISO15765 | 6 | CAN-based diagnostic |

## Core Operations

### Read ECU Flash

```python
from skills.j2534_passthru import J2534PassThru

pt = J2534PassThru()
pt.open()
channel = pt.connect_can(baud_rate=500000)

# Read 1MB flash memory
flash_data = pt.read_flash(
    start_address=0x000000,
    size=1024*1024,  # 1MB for E37
    block_size=1024   # Read in 1KB chunks
)

# Save to file
with open("ecu_flash.bin", "wb") as f:
    f.write(flash_data)

pt.disconnect(channel)
pt.close()
```

### Write ECU Flash

```python
from skills.j2534_passthru import J2534PassThru
from skills.hpt_converter import ChecksumValidator

# Validate checksums before flashing
validator = ChecksumValidator("GM_E37")
report = validator.validate_binary("stage1.bin")
if not report.overall_valid:
    raise ValueError("Checksums invalid! Fix before flashing.")

# Flash to ECU
pt = J2534PassThru()
pt.open()
channel = pt.connect_can()

# Unlock ECU for programming
pt.unlock_ecu(seed_key_algorithm="GM_E37")

# Write flash
pt.write_flash(
    data=tune_data,
    start_address=0x000000,
    verify=True
)

pt.disconnect(channel)
pt.close()
```

## CLI Usage

```bash
# Read ECU flash
python -m skills.j2534_passthru read_flash --output stock.bin --size 1MB

# Flash binary
python -m skills.j2534_passthru flash --input stage1.bin --platform GM_E37

# Get ECU info
python -m skills.j2534_passthru info
```

## Platform-Specific Notes

### GM E37 (LFX 3.6L V6)

- **Protocol**: CAN 500kbps
- **Flash Size**: 1MB
- **Unlock**: Seed/Key required
- **Programming Voltage**: Required on pin 13

### GM E38 (LS3/L99)

- **Protocol**: CAN 500kbps
- **Flash Size**: 1MB
- **Unlock**: Different seed/key algorithm

## Safety

⚠️ **WARNING**: Direct ECU flashing can brick your vehicle!

- Always have a known-good backup
- Maintain stable battery voltage during flash
- Don't interrupt flashing process
- Use at your own risk
