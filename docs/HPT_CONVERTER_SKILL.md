# HPT Converter Skill

Convert HP Tuners .hpt files to/from .bin, .hex, .json, and more.

## Quick Start

```bash
# List supported platforms
python -m skills.hpt_converter platforms

# Or use the batch file
hpt-convert.bat platforms
```

## What It Does

This skill enables:
- **Extract binary** from HPT files → Use with other tuning tools
- **Create HPT** from binary → Import external calibrations
- **Compare tunes** at byte level → See exactly what changed
- **Batch convert** entire folders → Process multiple files
- **Build tunes programmatically** → Automated modifications
- **Validate checksums** → Ensure ECM calibration integrity
- **Fix checksums** → Auto-correct after modifications

## J2534 PassThru Integration

If you have a J2534 PassThru device (Tactrix OpenPort, etc.), you can flash directly:

```bash
# Flash your tune directly to the ECU
python -m skills.j2534_passthru flash stage1.bin --platform GM_E37

# Read stock flash for backup
python -m skills.j2534_passthru read_flash stock_backup.bin --platform GM_E37

# Test connection
python -m skills.j2534_passthru test
```

See `skills/j2534_passthru/SKILL.md` for complete J2534 documentation.

## Supported Platforms

| Platform | ECM | Binary Size | Vehicle |
|----------|-----|-------------|---------|
| GM_E37 | E37 | 1MB | LFX 3.6L V6 (Impala, Camaro) |
| GM_E38 | E38 | 1MB | LS3/L99 V8 |
| GM_E41 | E41 | 2MB | Gen V V8 |
| GM_E78 | E78 | 1MB | 2.0T/2.5L |

## Commands

### Calculate Checksums
```bash
# MD5, SHA256, CRC32
hpt-convert.bat checksum tune.bin

# Validate ECM checksums
hpt-convert.bat validate tune.bin --platform GM_E37

# Fix invalid checksums
hpt-convert.bat validate tune.bin --fix -o tune_fixed.bin
```

### Convert HPT to BIN
```bash
python -m skills.hpt_converter hpt_to_bin input.hpt output.bin
```

### Convert BIN to HPT
```bash
python -m skills.hpt_converter bin_to_hpt input.bin output.hpt \
    --vin YOURVIN \
    --platform GM_E37 \
    --cal-id 12653917
```

### Compare Two Tunes
```bash
python -m skills.hpt_converter compare stock.hpt modified.hpt --verbose
```

### Batch Convert Folder
```bash
python -m skills.hpt_converter batch ./hpt_files ./bin_files --format bin
```

### Extract Metadata
```bash
python -m skills.hpt_converter extract_metadata tune.hpt metadata.json
```

## Python API

```python
from skills.hpt_converter import HPTConverter, HPTBuilder

# Extract binary
converter = HPTConverter()
result = converter.hpt_to_bin("stock.hpt", "stock.bin")

# Create HPT
result = converter.bin_to_hpt(
    "modified.bin", "modified.hpt",
    vin="2G1WB5E37D1157819",
    platform="GM_E37"
)

# Build tune programmatically
builder = HPTBuilder(platform="GM_E37", vin="YOURVIN")
builder.load_base_binary("stock.bin")
builder.set_rev_limit(7000)
builder.save("stage1.hpt", fix_checksums=True)  # Auto-fix checksums

# Validate checksums
from skills.hpt_converter import ChecksumValidator
validator = ChecksumValidator(platform="GM_E37")
report = validator.validate_binary("stage1.bin")
validator.print_report(report)
```

## Integration with Live Bridge

Enable automatic HPT conversion in the bridge:

```python
from skills.hpt_converter.bridge_integration import HPTBridgeExtension

# In your bridge config
bridge_config = {
    'auto_convert_hpt': True,
    'auto_convert_format': ['bin', 'json'],
    'keep_originals': True
}

# Now dropping .hpt files auto-converts them!
```

## File Format

HPT files contain:
- **Header** (256 bytes): Magic, version, offsets
- **Metadata** (JSON): VIN, comments, history
- **Binary** (zlib compressed): Raw ECU flash data

## Safety & Legal

⚠️ **Important**:
- Only work on vehicles you own
- Always backup stock tunes
- Binary modifications can brick ECUs
- Respect HP Tuners' IP and terms

## More Info

See `skills/hpt_converter/SKILL.md` for complete documentation.
