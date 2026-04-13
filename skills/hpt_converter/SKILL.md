# HPT File Converter Skill

## Overview

Convert HP Tuners .hpt files to/from various formats including .bin, .hex, .ori, and JSON. This skill enables cross-platform tune compatibility and deeper binary-level analysis.

## What is HPT Format?

HP Tuners .hpt files are proprietary compressed archives containing:
- **Raw binary calibration** (the actual ECU flash data)
- **Metadata** (VIN, comments, modification history)
- **Table definitions** (maps, axis labels, units)
- **Checksums** (file integrity)

The binary portion is compatible with the ECU's flash memory layout.

## Supported Conversions

| From | To | Use Case |
|------|-----|----------|
| .hpt | .bin | Use with other tuning tools (TunerCat, etc.) |
| .hpt | .hex | Human-readable hex dump for analysis |
| .hpt | .ori | Original/stock format for archives |
| .hpt | .json | Structured data for AI processing |
| .bin | .hpt | Import external binary to HP Tuners |
| .json | .hpt | Create tune from structured data |

## Checksum Validation

The converter includes comprehensive checksum validation:
- **Validate ECM checksums**: Verify calibration integrity
- **Fix invalid checksums**: Automatically correct after modifications
- **File hashes**: Calculate MD5, SHA256, CRC32
- **Platform-specific**: Supports GM E37, E38, E41 checksum schemes

## Installation

```bash
# No additional dependencies beyond base project
pip install -r requirements.txt
```

## Quick Start

```python
from skills.hpt_converter import HPTConverter, ConversionOptions

# Create converter instance
converter = HPTConverter()

# HPT to BIN (extract raw binary)
converter.hpt_to_bin(
    "input/Stock_Tune.hpt",
    "output/Stock_Tune.bin"
)

# HPT to JSON (full structure)
converter.hpt_to_json(
    "input/Stage1.hpt",
    "output/Stage1_analysis.json"
)

# BIN to HPT (create HP Tuners file)
converter.bin_to_hpt(
    "input/modified.bin",
    "output/modified.hpt",
    vin="2G1WB5E37D1157819",
    platform="GM_E37"
)
```

### Validate Checksums
```python
from skills.hpt_converter import ChecksumValidator

validator = ChecksumValidator(platform="GM_E37")

# Validate a binary
report = validator.validate_binary("tune.bin")
validator.print_report(report)

# Fix invalid checksums
validator.fix_checksums("tune.bin", "tune_fixed.bin")

# Calculate file hashes
checksums = validator.calculate_file_checksums("tune.bin")
print(f"MD5: {checksums['md5']}")
```

### CLI Checksum Commands
```bash
# Calculate file checksums (MD5, SHA256, CRC32)
python -m skills.hpt_converter checksum tune.bin

# Validate ECM checksums
python -m skills.hpt_converter validate tune.bin --platform GM_E37

# Fix invalid checksums
python -m skills.hpt_converter validate tune.bin --fix --output tune_fixed.bin
```

## File Format Reference

### HPT File Structure

```
HPT File (zlib compressed container)
├── Header (256 bytes)
│   ├── Magic: "HPTF" (4 bytes)
│   ├── Version: uint32
│   ├── Platform ID: 16 bytes
│   └── Metadata offset: uint32
├── Metadata (JSON)
│   ├── VIN
│   ├── Calibration ID
│   ├── Comments
│   ├── History
│   └── Checksums
└── Binary Payload (raw ECU flash)
    └── Size varies by platform (512KB - 4MB)
```

### Platform Binary Sizes

| Platform | ECM | Binary Size | Description |
|----------|-----|-------------|-------------|
| GM_E37 | E37 | 1MB | LFX 3.6L V6 |
| GM_E38 | E38 | 1MB | LS3/L99 V8 |
| GM_E41 | E41 | 2MB | Gen V V8 |
| GM_E39 | E39 | 2MB | Gen V Truck |
| GM_E78 | E78 | 1MB | 2.0T/2.5L |

## Usage Examples

### Extract and Analyze Binary

```python
from skills.hpt_converter import HPTConverter
from skills.hpt_converter.analyzer import BinaryAnalyzer

converter = HPTConverter()

# Extract binary
bin_path = converter.hpt_to_bin("tune.hpt", "tune.bin")

# Analyze binary structure
analyzer = BinaryAnalyzer(bin_path, platform="GM_E37")

# Find specific tables by signature
spark_table = analyzer.find_table_by_signature(
    signature=b'\x00\x10\x20\x30',  # Known spark table header
    size=1024
)

# Get checksums
checksums = analyzer.calculate_checksums()
print(f"BIN Checksum: {checksums['bin_checksum']}")
print(f"HPT Checksum: {checksums['hpt_checksum']}")
```

### Batch Conversion

```python
from skills.hpt_converter import BatchConverter

# Convert entire folder
batch = BatchConverter()

batch.convert_folder(
    input_dir="./tunes/hpt/",
    output_dir="./tunes/bin/",
    target_format="bin",
    preserve_structure=True
)

# Results report
for result in batch.results:
    print(f"{result.input_file} -> {result.output_file}: {result.status}")
```

### Compare Two Tunes at Binary Level

```python
from skills.hpt_converter import TuneComparator

comparator = TuneComparator()

# Compare two HPT files
differences = comparator.compare_hpt(
    "stock.hpt",
    "stage1.hpt",
    output_format="detailed"
)

# Show changed memory regions
for diff in differences['memory_diffs']:
    print(f"Offset 0x{diff['offset']:06X}: {diff['old_value']} -> {diff['new_value']}")
```

### Create Tune from Scratch

```python
from skills.hpt_converter import HPTBuilder

builder = HPTBuilder(
    platform="GM_E37",
    vin="2G1WB5E37D1157819",
    calibration_id="12653917"
)

# Load base binary (from stock read)
builder.load_base_binary("stock.bin")

# Modify specific addresses
builder.modify_bytes(
    offset=0x12345,
    data=b'\x20\x21\x22\x23',  # New spark values
    description="Increased timing at 4000 RPM"
)

# Build HPT file
builder.save("custom_tune.hpt")
```

## Memory Map Reference (GM E37 Example)

Common calibration addresses for GM E37 (LFX 3.6L):

| Component | Address Range | Size | Description |
|-----------|---------------|------|-------------|
| Spark Main | 0x12000-0x13000 | 4KB | Main spark advance table |
| Fuel Mass | 0x14000-0x15000 | 4KB | Base fuel mass table |
| MAF Cal | 0x16000-0x16500 | 1.25KB | MAF calibration curve |
| Rev Limit | 0x20000-0x20004 | 4B | RPM limiter |
| VE Table | 0x18000-0x19000 | 4KB | Volumetric efficiency |

⚠️ **Warning**: Addresses vary by OS version. Always verify with your specific calibration.

## Integration with Live Bridge

The converter integrates with the Live Tuning Bridge for automatic conversion:

```python
# In your bridge configuration
from skills.hpt_converter.bridge_integration import HPTBridgeExtension

bridge_config = BridgeConfig(
    auto_convert_hpt=True,
    auto_convert_format=["bin", "json"],  # Generate both
    keep_originals=True
)

# Now dropping an .hpt into bridge/incoming/ automatically:
# 1. Extracts binary -> bridge/incoming/extracted/
# 2. Creates JSON analysis -> bridge/incoming/analysis/
# 3. Archives original -> bridge/archive/
```

## CLI Usage

```bash
# Convert single file
python -m skills.hpt_converter hpt_to_bin input.hpt output.bin

# Convert with platform detection
python -m skills.hpt_converter hpt_to_bin input.hpt output.bin --platform GM_E37

# Batch convert folder
python -m skills.hpt_converter batch ./tunes/hpt ./tunes/bin --format bin

# Extract metadata only
python -m skills.hpt_converter extract_metadata input.hpt metadata.json

# Compare two files
python -m skills.hpt_converter compare stock.hpt modified.hpt diff_report.txt

# Create HPT from binary
python -m skills.hpt_converter bin_to_hpt input.bin output.hpt \
    --vin 2G1WB5E37D1157819 \
    --platform GM_E37 \
    --cal-id 12653917
```

## Advanced Features

### Checksum Verification

```python
from skills.hpt_converter.checksum import ChecksumValidator

validator = ChecksumValidator()

# Verify file integrity
result = validator.verify_hpt("tune.hpt")
if not result.valid:
    print(f"Checksum mismatch! Expected: {result.expected}, Got: {result.actual}")

# Recalculate checksums after modification
validator.fix_checksums("modified.hpt")
```

### Platform Auto-Detection

```python
from skills.hpt_converter.detector import PlatformDetector

detector = PlatformDetector()

# Detect from binary signature
platform = detector.detect_from_binary("tune.bin")
print(f"Detected platform: {platform}")

# Detect from HPT metadata
info = detector.analyze_hpt("tune.hpt")
print(f"ECM: {info.ecm_type}")
print(f"OS Version: {info.os_version}")
print(f"Calibration: {info.calibration_id}")
```

### Binary Patching

```python
from skills.hpt_converter.patcher import BinaryPatcher

patcher = BinaryPatcher("stock.bin")

# Apply known patches
patcher.apply_patch_set("stage1_patches.json")

# Manual patch
patcher.patch(
    name="Rev Limiter",
    offset=0x20000,
    old_value=b'\x1A\x20',  # 6500 RPM
    new_value=b'\x20\x20',  # 7000 RPM
)

patcher.save("patched.bin")
```

## Troubleshooting

### "Invalid HPT file" Error
- Verify file wasn't corrupted during transfer
- Check if file is password protected (some commercial tunes)
- Try extracting with HP Tuners first, then re-saving

### "Unknown platform" Error
- Specify platform manually with `--platform` flag
- Update platform database: `converter.update_platform_db()`

### Checksum Mismatch
- Binary was modified outside HP Tuners
- Use `validator.fix_checksums()` to recalculate
- Some ECMs use rolling checksums that require special handling

### Binary Size Mismatch
- Different OS versions have different sizes
- Verify you're using correct platform definition
- Check if file contains TCM data (larger size)

## Legal and Safety

⚠️ **Important Notes**:

1. **Only work on vehicles you own or have authorization to modify**
2. **Backup stock tune before any modifications**
3. **Understand that binary-level modifications can brick ECUs**
4. **Some regions prohibit ECU modifications for street use**

This tool is for educational and research purposes. Respect HP Tuners' intellectual property and terms of service.

## Contributing

To add support for new platforms:

1. Define platform in `platforms.json`:
```json
{
  "platform_id": "GM_NEW",
  "ecm": "E99",
  "binary_size": 2097152,
  "signature": "0x12345678"
}
```

2. Add memory map to `memory_maps/`
3. Submit pull request with test files

## References

- HP Tuners Forum: hptuners.com/forums
- GM ECM Documentation: gm-ecm-docs (community)
- OBD-II Standards: SAE J1979, J2534
