#!/usr/bin/env python3
"""
Tune Comparator - Compare two tunes at binary level
"""

import difflib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

try:
    from .converter import HPTConverter
except ImportError:
    from converter import HPTConverter

logger = logging.getLogger(__name__)


@dataclass
class Difference:
    """Single difference record"""
    offset: int
    old_value: bytes
    new_value: bytes
    context: str = ""  # Description of what this memory region is


@dataclass
class ComparisonResult:
    """Result of tune comparison"""
    file1: str
    file2: str
    identical: bool
    total_differences: int
    differences: List[Difference] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)


class TuneComparator:
    """
    Compare two HPT or BIN files and identify differences
    """
    
    def __init__(self):
        self.converter = HPTConverter()
        
    def compare_hpt(self, file1: str, file2: str,
                    output_format: str = "summary") -> ComparisonResult:
        """
        Compare two HPT files
        
        Args:
            file1: Path to first HPT file (baseline)
            file2: Path to second HPT file (modified)
            output_format: "summary", "detailed", or "diff"
            
        Returns:
            ComparisonResult with all differences
        """
        import tempfile
        
        # Extract binaries
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp1:
            bin1_path = tmp1.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp2:
            bin2_path = tmp2.name
            
        try:
            result1 = self.converter.hpt_to_bin(file1, bin1_path)
            result2 = self.converter.hpt_to_bin(file2, bin2_path)
            
            if not result1.success:
                raise ValueError(f"Failed to extract {file1}: {result1.errors}")
            if not result2.success:
                raise ValueError(f"Failed to extract {file2}: {result2.errors}")
                
            # Compare binaries
            return self.compare_bin(bin1_path, bin2_path, 
                                    file1, file2, output_format)
                                    
        finally:
            # Cleanup
            Path(bin1_path).unlink(missing_ok=True)
            Path(bin2_path).unlink(missing_ok=True)
            
    def compare_bin(self, file1: str, file2: str,
                    original_names: Tuple[str, str] = None,
                    output_format: str = "summary") -> ComparisonResult:
        """
        Compare two binary files
        
        Args:
            file1: Path to first binary file
            file2: Path to second binary file
            original_names: Original HPT filenames (if different from bin paths)
            output_format: Output detail level
            
        Returns:
            ComparisonResult with all differences
        """
        # Read binaries
        with open(file1, 'rb') as f:
            data1 = f.read()
        with open(file2, 'rb') as f:
            data2 = f.read()
            
        names = original_names or (file1, file2)
        
        result = ComparisonResult(
            file1=names[0],
            file2=names[1],
            identical=data1 == data2,
            total_differences=0
        )
        
        if result.identical:
            return result
            
        # Find differences
        differences = self._find_differences(data1, data2)
        result.differences = differences
        result.total_differences = len(differences)
        
        # Generate summary
        result.summary = self._generate_summary(differences, len(data1))
        
        logger.info(f"Found {len(differences)} differences between files")
        
        return result
        
    def _find_differences(self, data1: bytes, data2: bytes) -> List[Difference]:
        """Find all byte-level differences"""
        differences = []
        
        # Ensure same length for comparison
        min_len = min(len(data1), len(data2))
        
        i = 0
        while i < min_len:
            if data1[i] != data2[i]:
                # Found difference, find run length
                start = i
                while i < min_len and data1[i] != data2[i]:
                    i += 1
                end = i
                
                diff = Difference(
                    offset=start,
                    old_value=data1[start:end],
                    new_value=data2[start:end],
                    context=self._identify_memory_region(start)
                )
                differences.append(diff)
            else:
                i += 1
                
        # Handle size difference
        if len(data1) != len(data2):
            if len(data1) > len(data2):
                differences.append(Difference(
                    offset=min_len,
                    old_value=data1[min_len:],
                    new_value=b'',
                    context="Extra data in file 1"
                ))
            else:
                differences.append(Difference(
                    offset=min_len,
                    old_value=b'',
                    new_value=data2[min_len:],
                    context="Extra data in file 2"
                ))
                
        return differences
        
    def _identify_memory_region(self, offset: int) -> str:
        """Try to identify what memory region an offset belongs to"""
        # GM E37 memory map (simplified)
        regions = [
            (0x00000, 0x10000, "Boot/Reserved"),
            (0x10000, 0x20000, "Calibration Header"),
            (0x20000, 0x50000, "Engine Tables"),
            (0x50000, 0x60000, "Transmission Tables"),
            (0x60000, 0x70000, "Fuel Tables"),
            (0x70000, 0x80000, "Spark Tables"),
            (0x80000, 0x90000, "Torque Model"),
            (0x90000, 0xA0000, "VE/MAF Tables"),
            (0xA0000, 0xF0000, "System/Diagnostics"),
        ]
        
        for start, end, name in regions:
            if start <= offset < end:
                return name
                
        return "Unknown"
        
    def _generate_summary(self, differences: List[Difference], 
                          total_size: int) -> Dict:
        """Generate summary statistics"""
        total_changed_bytes = sum(len(d.old_value) + len(d.new_value) 
                                   for d in differences)
        
        # Group by context
        by_context = {}
        for diff in differences:
            ctx = diff.context
            if ctx not in by_context:
                by_context[ctx] = {"count": 0, "bytes": 0}
            by_context[ctx]["count"] += 1
            by_context[ctx]["bytes"] += len(diff.old_value) + len(diff.new_value)
            
        return {
            "total_differences": len(differences),
            "total_changed_bytes": total_changed_bytes,
            "change_percentage": (total_changed_bytes / total_size) * 100,
            "by_region": by_context
        }
        
    def print_comparison(self, result: ComparisonResult, 
                         verbose: bool = False):
        """
        Print comparison results to console
        
        Args:
            result: ComparisonResult to print
            verbose: Show all differences if True
        """
        print("\n" + "="*70)
        print("TUNE COMPARISON REPORT")
        print("="*70)
        print(f"File 1: {result.file1}")
        print(f"File 2: {result.file2}")
        print()
        
        if result.identical:
            print("Files are IDENTICAL")
            return
            
        print(f"Total Differences: {result.total_differences}")
        print(f"Changed Bytes: {result.summary['total_changed_bytes']}")
        print(f"Change: {result.summary['change_percentage']:.4f}%")
        print()
        
        print("Changes by Region:")
        for region, stats in result.summary['by_region'].items():
            print(f"  {region}: {stats['count']} changes ({stats['bytes']} bytes)")
            
        if verbose and result.differences:
            print("\nDetailed Differences:")
            for i, diff in enumerate(result.differences[:20], 1):  # Limit to 20
                print(f"\n{i}. Offset 0x{diff.offset:06X} ({diff.context})")
                print(f"   Old: {diff.old_value.hex()}")
                print(f"   New: {diff.new_value.hex()}")
                
            if len(result.differences) > 20:
                print(f"\n... and {len(result.differences) - 20} more differences")
                
    def export_diff_report(self, result: ComparisonResult, 
                           output_path: str) -> str:
        """
        Export comparison report to file
        
        Args:
            result: ComparisonResult to export
            output_path: Path for output file
            
        Returns:
            Path to saved report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build report
        report = {
            "comparison": {
                "file1": result.file1,
                "file2": result.file2,
                "timestamp": str(datetime.now()),
                "identical": result.identical,
                "total_differences": result.total_differences,
                "summary": result.summary
            },
            "differences": [
                {
                    "offset": f"0x{d.offset:06X}",
                    "old_value": d.old_value.hex(),
                    "new_value": d.new_value.hex(),
                    "context": d.context
                }
                for d in result.differences
            ]
        }
        
        # Save as JSON
        if output_path.suffix == '.json':
            import json
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        else:
            # Text format
            with open(output_path, 'w') as f:
                f.write(f"Tune Comparison Report\n")
                f.write(f"=====================\n\n")
                f.write(f"File 1: {result.file1}\n")
                f.write(f"File 2: {result.file2}\n\n")
                f.write(f"Total Differences: {result.total_differences}\n")
                f.write(f"Changed Bytes: {result.summary['total_changed_bytes']}\n\n")
                
                f.write("Differences:\n")
                for d in result.differences:
                    f.write(f"\nOffset 0x{d.offset:06X} ({d.context})\n")
                    f.write(f"  Old: {d.old_value.hex()}\n")
                    f.write(f"  New: {d.new_value.hex()}\n")
                    
        logger.info(f"Exported diff report: {output_path}")
        return str(output_path)
        
    def create_binary_patch(self, result: ComparisonResult,
                           output_path: str) -> str:
        """
        Create a binary patch file (similar to .ips or .bps)
        
        Args:
            result: ComparisonResult with differences
            output_path: Path for patch file
            
        Returns:
            Path to patch file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create simple patch format
        import struct
        
        with open(output_path, 'wb') as f:
            # Header
            f.write(b'HPTP')  # HPT Patch magic
            f.write(struct.pack('<I', len(result.differences)))
            
            # Write each difference
            for diff in result.differences:
                f.write(struct.pack('<I', diff.offset))  # Offset
                f.write(struct.pack('<H', len(diff.new_value)))  # Length
                f.write(diff.new_value)  # New data
                
        logger.info(f"Created patch file: {output_path}")
        return str(output_path)


from datetime import datetime
