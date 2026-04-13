#!/usr/bin/env python3
"""
HPT Converter Bridge Integration
Integrate HPT conversion with Live Tuning Bridge
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    from .converter import HPTConverter
    from .analyzer import BinaryAnalyzer
except ImportError:
    from converter import HPTConverter
    from analyzer import BinaryAnalyzer

logger = logging.getLogger(__name__)


class HPTBridgeExtension:
    """
    Extension for Live Tuning Bridge to handle HPT files
    """
    
    def __init__(self, bridge_config: Dict):
        self.config = bridge_config
        self.converter = HPTConverter()
        self.enabled = bridge_config.get('auto_convert_hpt', True)
        self.output_formats = bridge_config.get('auto_convert_format', ['bin', 'json'])
        self.keep_originals = bridge_config.get('keep_originals', True)
        
    def process_incoming_hpt(self, hpt_path: str, 
                             output_base_dir: str) -> Dict:
        """
        Process an HPT file dropped into the bridge
        
        Args:
            hpt_path: Path to HPT file
            output_base_dir: Base output directory
            
        Returns:
            Processing results
        """
        if not self.enabled:
            return {'processed': False, 'reason': 'Auto-convert disabled'}
            
        hpt_path = Path(hpt_path)
        output_dir = Path(output_base_dir)
        results = {
            'input_file': str(hpt_path),
            'conversions': [],
            'analysis': {},
            'success': True
        }
        
        try:
            # Create output subdirectories
            bin_dir = output_dir / 'extracted'
            json_dir = output_dir / 'analysis'
            bin_dir.mkdir(parents=True, exist_ok=True)
            json_dir.mkdir(parents=True, exist_ok=True)
            
            base_name = hpt_path.stem
            
            # Convert to BIN
            if 'bin' in self.output_formats:
                bin_path = bin_dir / f"{base_name}.bin"
                result = self.converter.hpt_to_bin(
                    str(hpt_path), 
                    str(bin_path)
                )
                
                if result.success:
                    results['conversions'].append({
                        'format': 'bin',
                        'output': str(bin_path),
                        'platform': result.platform,
                        'size': result.binary_size
                    })
                    
                    # Analyze binary
                    analyzer = BinaryAnalyzer(str(bin_path), result.platform)
                    analysis = analyzer.quick_analysis()
                    results['analysis'] = analysis
                    
            # Convert to JSON
            if 'json' in self.output_formats:
                json_path = json_dir / f"{base_name}_metadata.json"
                result = self.converter.hpt_to_json(
                    str(hpt_path),
                    str(json_path),
                    extract_binary=False
                )
                
                if result.success:
                    results['conversions'].append({
                        'format': 'json',
                        'output': str(json_path)
                    })
                    
            logger.info(f"Processed HPT: {hpt_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to process HPT: {e}")
            results['success'] = False
            results['error'] = str(e)
            
        return results
        
    def create_tune_from_bridge_output(self, tune_data: Dict,
                                       output_path: str) -> str:
        """
        Create an HPT file from bridge-generated tune data
        
        Args:
            tune_data: Tune specification from bridge
            output_path: Output HPT path
            
        Returns:
            Path to created HPT
        """
        from .builder import HPTBuilder
        
        builder = HPTBuilder(
            platform=tune_data.get('platform', 'GM_E37'),
            vin=tune_data.get('vin', 'UNKNOWN'),
            calibration_id=tune_data.get('calibration_id', 'AUTO')
        )
        
        # If we have a base binary, load it
        if 'base_binary' in tune_data:
            builder.load_base_binary(tune_data['base_binary'])
            
            # Apply modifications
            for mod in tune_data.get('modifications', []):
                builder.modify_bytes(
                    offset=mod['offset'],
                    data=bytes.fromhex(mod['data']),
                    description=mod.get('description', '')
                )
        else:
            # Create minimal binary structure
            platform_info = self.converter.PLATFORMS.get(
                tune_data.get('platform', 'GM_E37'),
                {'binary_size': 1024*1024}
            )
            
            # Initialize empty binary
            builder.binary_data = bytes(platform_info['binary_size'])
            
        # Save
        return builder.save(output_path)


class BridgeHPTHandler:
    """
    Event handler for HPT files in the bridge
    """
    
    def __init__(self, extension: HPTBridgeExtension):
        self.extension = extension
        
    def on_file_received(self, filepath: str, bridge_context: Dict):
        """Called when an HPT file is dropped into the bridge"""
        results = self.extension.process_incoming_hpt(
            filepath,
            bridge_context.get('incoming_dir', './incoming')
        )
        
        return results


# Create a simple analyzer stub for the integration
class BinaryAnalyzer:
    """Analyze binary calibration files"""
    
    def __init__(self, bin_path: str, platform: str = None):
        self.bin_path = bin_path
        self.platform = platform
        
        with open(bin_path, 'rb') as f:
            self.data = f.read()
            
    def quick_analysis(self) -> Dict:
        """Quick analysis of binary"""
        return {
            'size': len(self.data),
            'platform': self.platform,
            'checksum': self._calc_checksum(),
            'empty_regions': self._find_empty_regions(),
            'data_regions': self._find_data_regions()
        }
        
    def _calc_checksum(self) -> int:
        """Calculate simple checksum"""
        return sum(self.data) & 0xFFFFFFFF
        
    def _find_empty_regions(self) -> List[Dict]:
        """Find empty (0xFF or 0x00) regions"""
        regions = []
        return regions  # Simplified
        
    def _find_data_regions(self) -> List[Dict]:
        """Find regions with data"""
        regions = []
        return regions  # Simplified
