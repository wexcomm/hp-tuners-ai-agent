#!/usr/bin/env python3
"""
Batch Converter - Convert multiple files at once
"""

from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

try:
    from .converter import HPTConverter, ConversionOptions, ConversionResult
except ImportError:
    from converter import HPTConverter, ConversionOptions, ConversionResult

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch conversion"""
    total_files: int
    successful: int
    failed: int
    results: List[ConversionResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BatchConverter:
    """
    Convert multiple files in batch
    """
    
    def __init__(self, options: Optional[ConversionOptions] = None,
                 max_workers: int = 4):
        self.options = options or ConversionOptions()
        self.max_workers = max_workers
        self.converter = HPTConverter(self.options)
        self.results: List[ConversionResult] = []
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        Set callback for progress updates
        
        Args:
            callback: Function(current, total, filename)
        """
        self.progress_callback = callback
        
    def convert_folder(self, input_dir: str, output_dir: str,
                       target_format: str = "bin",
                       preserve_structure: bool = True,
                       file_pattern: str = "*.hpt") -> BatchResult:
        """
        Convert all matching files in a folder
        
        Args:
            input_dir: Source folder
            output_dir: Destination folder
            target_format: Output format (bin, json, hex)
            preserve_structure: Maintain folder hierarchy
            file_pattern: Glob pattern for matching files
            
        Returns:
            BatchResult with all conversions
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Find all matching files
        files = list(input_path.rglob(file_pattern))
        
        logger.info(f"Found {len(files)} files to convert")
        
        batch_result = BatchResult(
            total_files=len(files),
            successful=0,
            failed=0
        )
        
        # Process files
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for file_path in files:
                # Determine output path
                if preserve_structure:
                    rel_path = file_path.relative_to(input_path)
                    out_file = output_path / rel_path.with_suffix(f'.{target_format}')
                else:
                    out_file = output_path / f"{file_path.stem}.{target_format}"
                    
                # Submit conversion
                future = executor.submit(
                    self._convert_single,
                    file_path,
                    out_file,
                    target_format
                )
                futures[future] = file_path
                
            # Collect results
            for i, future in enumerate(as_completed(futures), 1):
                file_path = futures[future]
                
                try:
                    result = future.result()
                    batch_result.results.append(result)
                    
                    if result.success:
                        batch_result.successful += 1
                    else:
                        batch_result.failed += 1
                        batch_result.errors.extend(result.errors)
                        
                except Exception as e:
                    batch_result.failed += 1
                    batch_result.errors.append(f"{file_path}: {str(e)}")
                    
                # Progress callback
                if self.progress_callback:
                    self.progress_callback(i, len(files), str(file_path))
                    
        self.results = batch_result.results
        
        logger.info(f"Batch complete: {batch_result.successful}/{batch_result.total_files} successful")
        
        return batch_result
        
    def _convert_single(self, input_path: Path, output_path: Path,
                       target_format: str) -> ConversionResult:
        """Convert a single file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if target_format == "bin":
            return self.converter.hpt_to_bin(
                str(input_path), 
                str(output_path)
            )
        elif target_format == "json":
            return self.converter.hpt_to_json(
                str(input_path),
                str(output_path),
                extract_binary=False
            )
        elif target_format == "hex":
            return self.converter.hpt_to_hex(
                str(input_path),
                str(output_path)
            )
        else:
            result = ConversionResult(
                success=False,
                input_file=str(input_path),
                output_file=str(output_path),
                format_from="hpt",
                format_to=target_format
            )
            result.errors.append(f"Unknown target format: {target_format}")
            return result
            
    def print_report(self, result: BatchResult):
        """Print batch conversion report"""
        print("\n" + "="*70)
        print("BATCH CONVERSION REPORT")
        print("="*70)
        print(f"Total Files: {result.total_files}")
        print(f"Successful:  {result.successful}")
        print(f"Failed:      {result.failed}")
        print(f"Success Rate: {(result.successful/result.total_files*100):.1f}%")
        print()
        
        if result.errors:
            print("Errors:")
            for error in result.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more errors")
                
        print("\nSuccessful Conversions:")
        for r in result.results:
            if r.success:
                print(f"  ✓ {Path(r.input_file).name} -> {Path(r.output_file).name}")
                
    def export_report(self, result: BatchResult, output_path: str):
        """Export batch report to JSON"""
        import json
        
        report = {
            "batch_summary": {
                "total": result.total_files,
                "successful": result.successful,
                "failed": result.failed,
                "success_rate": result.successful / result.total_files if result.total_files else 0
            },
            "conversions": [
                {
                    "input": r.input_file,
                    "output": r.output_file,
                    "success": r.success,
                    "platform": r.platform,
                    "errors": r.errors,
                    "warnings": r.warnings
                }
                for r in result.results
            ],
            "errors": result.errors
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Exported batch report: {output_path}")
