#!/usr/bin/env python3
"""
HPT Converter Examples
Basic usage demonstrations
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from skills.hpt_converter import HPTConverter, HPTBuilder, TuneComparator, BatchConverter
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from converter import HPTConverter
    from builder import HPTBuilder
    from comparator import TuneComparator
    from batch import BatchConverter


def example_1_hpt_to_bin():
    """Extract binary from HPT file"""
    print("="*60)
    print("Example 1: HPT to BIN Conversion")
    print("="*60)
    
    converter = HPTConverter()
    
    # Convert HPT to binary
    result = converter.hpt_to_bin(
        "input/stock_tune.hpt",
        "output/stock_tune.bin"
    )
    
    if result.success:
        print(f"✓ Extracted binary: {result.binary_size} bytes")
        print(f"  Platform: {result.platform}")
        print(f"  Compression ratio: {result.metadata.get('compression_ratio', 0):.2f}")
    else:
        print(f"✗ Failed: {result.errors}")


def example_2_bin_to_hpt():
    """Create HPT from binary"""
    print("\n" + "="*60)
    print("Example 2: BIN to HPT Conversion")
    print("="*60)
    
    converter = HPTConverter()
    
    # Create HPT from binary
    result = converter.bin_to_hpt(
        "input/modified.bin",
        "output/modified.hpt",
        vin="2G1WB5E37D1157819",
        platform="GM_E37",
        calibration_id="12653917",
        metadata={
            "comments": "Stage 1 tune - intake and exhaust",
            "tuner": "AI Agent"
        }
    )
    
    if result.success:
        print(f"✓ Created HPT: {result.output_file}")
        print(f"  VIN: {result.metadata.get('VIN')}")
        print(f"  Platform: {result.metadata.get('Platform')}")
    else:
        print(f"✗ Failed: {result.errors}")


def example_3_compare_tunes():
    """Compare two tunes"""
    print("\n" + "="*60)
    print("Example 3: Compare Two Tunes")
    print("="*60)
    
    comparator = TuneComparator()
    
    # Compare stock vs modified
    result = comparator.compare_hpt(
        "input/stock.hpt",
        "input/stage1.hpt"
    )
    
    # Print results
    comparator.print_comparison(result, verbose=False)
    
    # Export detailed report
    comparator.export_diff_report(result, "output/diff_report.json")
    print("\nDetailed report saved: output/diff_report.json")


def example_4_build_tune():
    """Build a tune programmatically"""
    print("\n" + "="*60)
    print("Example 4: Build Tune Programmatically")
    print("="*60)
    
    builder = HPTBuilder(
        platform="GM_E37",
        vin="2G1WB5E37D1157819",
        calibration_id="12653917"
    )
    
    # Load base binary
    builder.load_base_binary("input/stock.bin")
    
    # Modify rev limiter
    builder.set_rev_limit(7000, offset=0x20000)
    
    # Modify speed limiter
    builder.set_speed_limit(160, offset=0x20010)
    
    # Custom modification
    builder.modify_bytes(
        offset=0x12345,
        data=b'\x20\x21\x22\x23',
        description="Increased timing at 4000 RPM"
    )
    
    # Add comments
    builder.add_comment("Stage 1 - Intake and Exhaust")
    builder.add_comment("Increased rev limit to 7000 RPM")
    
    # Save
    output = builder.save("output/custom_stage1.hpt")
    print(f"✓ Built tune: {output}")
    
    # Save modifications report
    builder.save_modifications_json("output/modifications.json")
    print("  Modifications: output/modifications.json")


def example_5_batch_convert():
    """Batch convert folder"""
    print("\n" + "="*60)
    print("Example 5: Batch Conversion")
    print("="*60)
    
    batch = BatchConverter(max_workers=4)
    
    # Set progress callback
    def progress(current, total, filename):
        print(f"  [{current}/{total}] {filename}")
        
    batch.set_progress_callback(progress)
    
    # Convert all HPT files
    result = batch.convert_folder(
        input_dir="./tunes/hpt/",
        output_dir="./tunes/bin/",
        target_format="bin",
        preserve_structure=True
    )
    
    # Print report
    batch.print_report(result)


def example_6_extract_metadata():
    """Extract and view metadata"""
    print("\n" + "="*60)
    print("Example 6: Extract Metadata")
    print("="*60)
    
    converter = HPTConverter()
    
    # Convert to JSON (metadata)
    result = converter.hpt_to_json(
        "input/stock.hpt",
        "output/metadata.json",
        extract_binary=False  # Just metadata
    )
    
    if result.success:
        import json
        metadata = result.metadata.get('metadata', {})
        
        print(f"VIN: {metadata.get('VIN', 'N/A')}")
        print(f"Calibration: {metadata.get('CalibrationID', 'N/A')}")
        print(f"Platform: {metadata.get('Platform', 'N/A')}")
        print(f"Created: {metadata.get('CreatedAt', 'N/A')}")
        
        if 'Comments' in metadata:
            print(f"Comments: {metadata['Comments']}")


def example_7_validate_checksums():
    """Validate checksums in tune file"""
    print("\n" + "="*60)
    print("Example 7: Validate Checksums")
    print("="*60)
    
    from skills.hpt_converter import ChecksumValidator
    
    validator = ChecksumValidator(platform="GM_E37")
    
    # Validate binary file
    report = validator.validate_binary("input/stock.bin")
    
    # Print report
    validator.print_report(report)
    
    if not report.overall_valid:
        print("\nSome checksums are invalid! Fixing...")
        
        # Fix checksums
        fixed_report = validator.fix_checksums(
            "input/stock.bin",
            "output/stock_fixed.bin"
        )
        
        if fixed_report.overall_valid:
            print("✓ Checksums fixed and saved to output/stock_fixed.bin")


def example_8_calculate_file_checksums():
    """Calculate MD5, SHA256, CRC32 of a file"""
    print("\n" + "="*60)
    print("Example 8: Calculate File Checksums")
    print("="*60)
    
    from skills.hpt_converter import ChecksumValidator
    
    validator = ChecksumValidator()
    
    # Calculate checksums
    checksums = validator.calculate_file_checksums("input/stock.bin")
    
    print(f"MD5:     {checksums['md5']}")
    print(f"SHA256:  {checksums['sha256']}")
    print(f"CRC32:   {checksums['crc32']}")
    print(f"Size:    {checksums['size_human']}")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("  HPT CONVERTER - USAGE EXAMPLES")
    print("="*60)
    
    examples = [
        ("HPT to BIN", example_1_hpt_to_bin),
        ("BIN to HPT", example_2_bin_to_hpt),
        ("Compare Tunes", example_3_compare_tunes),
        ("Build Tune", example_4_build_tune),
        ("Batch Convert", example_5_batch_convert),
        ("Extract Metadata", example_6_extract_metadata),
        ("Validate Checksums", example_7_validate_checksums),
        ("File Checksums", example_8_calculate_file_checksums),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nNote: These are code examples. Update file paths")
    print("      to match your actual tune files.")
    
    # Uncomment to run examples:
    # example_1_hpt_to_bin()
    # example_2_bin_to_hpt()
    # example_3_compare_tunes()
    # example_4_build_tune()
    # example_5_batch_convert()
    # example_6_extract_metadata()


if __name__ == "__main__":
    main()
