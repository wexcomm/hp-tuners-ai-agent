#!/usr/bin/env python3
"""
HPT Converter CLI - Command line interface
"""

import sys
import argparse
from pathlib import Path

try:
    from .converter import HPTConverter, ConversionOptions
    from .batch import BatchConverter
    from .comparator import TuneComparator
    from .checksum import ChecksumValidator
except ImportError:
    from converter import HPTConverter, ConversionOptions
    from batch import BatchConverter
    from comparator import TuneComparator
    from checksum import ChecksumValidator


def main():
    parser = argparse.ArgumentParser(
        description='HPT File Converter - Convert between .hpt, .bin, .hex, and .json formats'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # hpt_to_bin command
    p_bin = subparsers.add_parser('hpt_to_bin', help='Convert HPT to BIN')
    p_bin.add_argument('input', help='Input HPT file')
    p_bin.add_argument('output', help='Output BIN file')
    p_bin.add_argument('--platform', '-p', help='Platform override (e.g., GM_E37)')
    
    # hpt_to_json command
    p_json = subparsers.add_parser('hpt_to_json', help='Convert HPT to JSON')
    p_json.add_argument('input', help='Input HPT file')
    p_json.add_argument('output', help='Output JSON file')
    p_json.add_argument('--extract-binary', '-b', action='store_true',
                        help='Include binary data as base64')
    
    # hpt_to_hex command
    p_hex = subparsers.add_parser('hpt_to_hex', help='Convert HPT to Intel HEX')
    p_hex.add_argument('input', help='Input HPT file')
    p_hex.add_argument('output', help='Output HEX file')
    
    # bin_to_hpt command
    p_hpt = subparsers.add_parser('bin_to_hpt', help='Convert BIN to HPT')
    p_hpt.add_argument('input', help='Input BIN file')
    p_hpt.add_argument('output', help='Output HPT file')
    p_hpt.add_argument('--vin', '-v', default='UNKNOWN', help='Vehicle VIN')
    p_hpt.add_argument('--platform', '-p', default='GM_E37', help='Platform (e.g., GM_E37)')
    p_hpt.add_argument('--cal-id', '-c', default='AUTO', help='Calibration ID')
    
    # batch command
    p_batch = subparsers.add_parser('batch', help='Batch convert folder')
    p_batch.add_argument('input_dir', help='Input directory')
    p_batch.add_argument('output_dir', help='Output directory')
    p_batch.add_argument('--format', '-f', default='bin', 
                         choices=['bin', 'json', 'hex'],
                         help='Target format')
    p_batch.add_argument('--pattern', default='*.hpt', help='File pattern')
    
    # compare command
    p_cmp = subparsers.add_parser('compare', help='Compare two tunes')
    p_cmp.add_argument('file1', help='First file (baseline)')
    p_cmp.add_argument('file2', help='Second file (modified)')
    p_cmp.add_argument('--output', '-o', help='Output report file')
    p_cmp.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed differences')
    
    # extract_metadata command
    p_meta = subparsers.add_parser('extract_metadata', help='Extract metadata from HPT')
    p_meta.add_argument('input', help='Input HPT file')
    p_meta.add_argument('output', help='Output JSON file')
    
    # validate command
    p_val = subparsers.add_parser('validate', help='Validate checksums in BIN or HPT file')
    p_val.add_argument('input', help='Input file (BIN or HPT)')
    p_val.add_argument('--platform', '-p', default='GM_E37', help='Platform type')
    p_val.add_argument('--fix', '-f', action='store_true', help='Fix invalid checksums')
    p_val.add_argument('--output', '-o', help='Output file (when fixing)')
    
    # checksum command
    p_chk = subparsers.add_parser('checksum', help='Calculate file checksums (MD5, SHA256, CRC32)')
    p_chk.add_argument('input', help='Input file')
    
    # platforms command
    p_plat = subparsers.add_parser('platforms', help='List supported platforms')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    converter = HPTConverter()
    
    # Execute command
    if args.command == 'hpt_to_bin':
        result = converter.hpt_to_bin(args.input, args.output, args.platform)
        print_result(result)
        return 0 if result.success else 1
        
    elif args.command == 'hpt_to_json':
        result = converter.hpt_to_json(args.input, args.output, args.extract_binary)
        print_result(result)
        return 0 if result.success else 1
        
    elif args.command == 'hpt_to_hex':
        result = converter.hpt_to_hex(args.input, args.output)
        print_result(result)
        return 0 if result.success else 1
        
    elif args.command == 'bin_to_hpt':
        result = converter.bin_to_hpt(
            args.input, args.output,
            vin=args.vin,
            platform=args.platform,
            calibration_id=args.cal_id
        )
        print_result(result)
        return 0 if result.success else 1
        
    elif args.command == 'batch':
        batch = BatchConverter()
        
        def progress(current, total, filename):
            print(f"[{current}/{total}] {filename}")
            
        batch.set_progress_callback(progress)
        
        result = batch.convert_folder(
            args.input_dir,
            args.output_dir,
            target_format=args.format,
            file_pattern=args.pattern
        )
        
        batch.print_report(result)
        return 0 if result.failed == 0 else 1
        
    elif args.command == 'compare':
        comparator = TuneComparator()
        result = comparator.compare_hpt(args.file1, args.file2)
        
        comparator.print_comparison(result, verbose=args.verbose)
        
        if args.output:
            comparator.export_diff_report(result, args.output)
            print(f"\nReport saved: {args.output}")
            
        return 0
        
    elif args.command == 'extract_metadata':
        result = converter.hpt_to_json(args.input, args.output)
        if result.success:
            print(f"Metadata extracted: {args.output}")
        else:
            print(f"Error: {result.errors}")
        return 0 if result.success else 1
        
    elif args.command == 'validate':
        validator = ChecksumValidator(platform=args.platform)
        
        # Determine file type
        input_path = Path(args.input)
        
        if args.fix:
            # Fix mode
            if input_path.suffix.lower() == '.hpt':
                print("Error: Can only fix BIN files directly. Extract HPT first.")
                return 1
            
            report = validator.fix_checksums(
                args.input, 
                args.output or args.input
            )
            print(f"\nChecksums fixed and saved to: {args.output or args.input}")
        else:
            # Validation mode
            if input_path.suffix.lower() == '.hpt':
                report = validator.validate_hpt(args.input)
            else:
                report = validator.validate_binary(args.input)
            
            validator.print_report(report)
        
        return 0 if report.overall_valid else 1
        
    elif args.command == 'checksum':
        validator = ChecksumValidator()
        checksums = validator.calculate_file_checksums(args.input)
        
        print(f"\nFile Checksums: {args.input}")
        print("=" * 50)
        print(f"MD5:     {checksums['md5']}")
        print(f"SHA256:  {checksums['sha256']}")
        print(f"CRC32:   {checksums['crc32']}")
        print(f"Size:    {checksums['size']} bytes ({checksums['size_human']})")
        return 0
        
    elif args.command == 'platforms':
        print("Supported Platforms:")
        print("=" * 50)
        for platform, info in converter.PLATFORMS.items():
            print(f"{platform:12} | {info['ecm']:6} | {info['binary_size']//1024:4d}KB | {info['description']}")
        return 0
        
    return 0


def print_result(result):
    """Print conversion result"""
    if result.success:
        print(f"✓ Success: {result.input_file} -> {result.output_file}")
        if result.platform:
            print(f"  Platform: {result.platform}")
        if result.binary_size:
            print(f"  Binary size: {result.binary_size} bytes")
        if result.warnings:
            for w in result.warnings:
                print(f"  Warning: {w}")
    else:
        print(f"✗ Failed: {result.input_file}")
        for e in result.errors:
            print(f"  Error: {e}")


if __name__ == '__main__':
    sys.exit(main())
