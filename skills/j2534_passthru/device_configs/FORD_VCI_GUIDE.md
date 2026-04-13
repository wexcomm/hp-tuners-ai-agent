# Ford VCI (VCM II) Setup Guide

## About Your Device

The **Ford VCI** (Vehicle Communication Interface), also known as **VCM II**, is a J2534-1/J2534-2 compliant device manufactured by Bosch for Ford Motor Company. While designed for Ford vehicles, it can work with GM vehicles in pass-through (J2534) mode.

## Device Capabilities

| Feature | Support |
|---------|---------|
| J2534-1 | ✅ Yes |
| J2534-2 | ✅ Yes |
| CAN 2.0 | ✅ Yes (125k, 250k, 500k, 1M) |
| CAN FD | ❌ No |
| ISO15765 | ✅ Yes |
| Programming Voltage | ✅ Yes (Pin 13, up to 20V) |
| USB Connection | ✅ USB 2.0 |

## Installation Paths

Your VCI Manager is installed at:
```
C:\Users\Public\Desktop\VCI Manager [Ford].lnk
```

The actual installation is typically at:
```
C:\Program Files\Ford\Ford VCI\
C:\Program Files (x86)\Ford\Ford VCI\
C:\Program Files\Ford Motor Company\VCM II\
```

## J2534 DLL Location

The J2534 interface DLL should be at one of these locations:
```
C:\Program Files\Ford\Ford VCI\j2534\fordvci.dll
C:\Program Files (x86)\Ford\Ford VCI\j2534\fordvci.dll
C:\Program Files\Ford Motor Company\VCM II\j2534\vcm2.dll
```

## Using with GM Vehicles

### Important Notes

1. **Pass-Through Mode**: The Ford VCI works with GM vehicles in J2534 pass-through mode, but some features may be limited compared to a GM-specific interface.

2. **Programming Voltage**: GM ECUs often require programming voltage (18V) on OBD-II pin 13. The Ford VCI supports this.

3. **Protocol**: GM vehicles use CAN 500kbps for diagnostics and flashing.

### Configuration

```python
from skills.j2534_passthru import J2534PassThru
from skills.j2534_passthru.device_configs.ford_vci import FordVCIDevice

# Auto-detect Ford VCI
ford_vci = FordVCIDevice()
if ford_vci.find_dll():
    print(f"Ford VCI found: {ford_vci.find_dll()}")
    
    # Use with J2534PassThru
    pt = J2534PassThru()  # Will auto-detect Ford VCI DLL
    pt.open()
    
    # Connect to GM vehicle (CAN 500kbps)
    channel = pt.connect_can(baud_rate=500000)
    
    # Enable programming voltage if needed
    pt.set_programming_voltage(pin_number=13, voltage=18000)  # 18V
    
    # Now you can flash...
```

## Extracting Configuration Data

Run the analyzer to extract data from your VCI Manager:

```bash
# Using batch file
analyze_vci.bat

# Or directly
python skills/j2534_passthru/device_configs/vci_analyzer.py
```

This will:
1. Find your VCI Manager installation
2. Locate J2534 DLL files
3. Detect USB device connection
4. Generate a configuration file

## Troubleshooting

### "DLL not found"
- Check if VCI Manager is installed
- Look for `fordvci.dll` or `vcm2.dll` in the installation directory
- Try reinstalling VCI Manager

### "Device not connected"
- Ensure VCI is plugged into USB
- Check Windows Device Manager for "Ford VCI" or "VCM II"
- Try a different USB port

### "Cannot communicate with vehicle"
- Verify ignition is ON
- Check OBD-II connection
- Ensure battery voltage > 12V
- Some GM vehicles may require specific initialization

## Data Collection for Development

To help improve GM support with Ford VCI, you can collect:

### 1. Protocol Logs
If your VCI Manager has logging:
- Enable debug logging
- Perform a simple operation (read VIN)
- Share the log file

### 2. Registry Settings
```powershell
# Export VCI registry settings
reg export "HKLM\SOFTWARE\Ford\Ford VCI" ford_vci.reg
```

### 3. USB Device Info
```powershell
# Get USB device details
Get-PnpDevice | Where-Object {$_.Name -like "*VCI*" -or $_.Name -like "*VCM*"} | 
    Select-Object Name, DeviceID, Status
```

### 4. Successful Operations
If you successfully use Ford VCI with a GM vehicle:
- Vehicle year/make/model
- ECU type (E37, E38, etc.)
- What operation worked (read, flash, etc.)
- Any special settings required

## Safety Notes

⚠️ **Programming Voltage**: Ford VCI can output up to 20V on pin 13. This is required for some GM ECUs but can damage others if used incorrectly.

⚠️ **ECM Damage**: Incorrect flashing can brick your ECU. Always have a known-good backup.

## References

- [J2534 Standard](https://www.sae.org/standards/content/j2534_1_202002/)
- Ford VCI User Manual (in your VCI Manager installation)
- Bosch VCI Documentation
