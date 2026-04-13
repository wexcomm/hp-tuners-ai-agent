#!/usr/bin/env python3
"""
Enhanced HP Tuners AI Agent v2.0
Integrates HPT file export, VCM Scanner import, PID database, and table templates
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Import our new modules
from hpt_file_exporter import HPTTuneFile, TuneComparator, HPTTable
from vcm_scanner_import import VCMScannerImporter, LogAnalyzer, TuneRecommendationEngine
from pid_database import PIDDatabase, LOGGING_PRESETS
from table_templates import (
    CompleteTuneBuilder, SparkTableGenerator, FuelTableGenerator,
    MAFCalibrationGenerator, VETableGenerator, TransmissionTableGenerator,
    TuneTable
)
from hp_tuners_agent import HPTunersAgent, ECUController, SafetyValidator
from dtc_database import DTCDatabase, DTCSeverity
from diagnostic_analyzer import DiagnosticAnalyzer, DiagnosticReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedHPTunersAgent(HPTunersAgent):
    """
    Enhanced agent with full HP Tuners VCM Suite integration
    """
    
    def __init__(self, port: str = None, backups_dir: str = "./tune_backups"):
        super().__init__(port, backups_dir)
        
        # New components
        self.pid_db = PIDDatabase()
        self.vcm_importer = VCMScannerImporter()
        self.dtc_db = DTCDatabase()
        self.diagnostic_analyzer: Optional[DiagnosticAnalyzer] = None
        self.current_hpt_tune: Optional[HPTTuneFile] = None
        
    def create_stage1_tune_package(self, octane: int = 93, 
                                    mods: List[str] = None) -> HPTTuneFile:
        """
        Create complete Stage 1 tune package
        Includes all tables for intake/exhaust modifications
        """
        if mods is None:
            mods = ["intake", "exhaust"]
            
        logger.info(f"Creating Stage 1 tune ({octane} octane, mods: {mods})")
        
        # Detect platform from ECU info if available
        platform = self._detect_platform()
        
        # Create HPT file
        vin = self.ecu.ecu_info.vin if self.ecu.ecu_info else "UNKNOWN"
        cal_id = self.ecu.ecu_info.calibration_id if self.ecu.ecu_info else "UNKNOWN"
        
        hpt = HPTTuneFile(vin=vin, calibration_id=cal_id, platform=platform)
        
        # Generate tables using templates
        tables = CompleteTuneBuilder.build_stage1_tune(
            vehicle=platform.lower(),
            octane=octane,
            mods=mods
        )
        
        # Convert and add to HPT file
        # Spark table
        spark_table = tables["spark_main"]
        spark_data = self._convert_table_to_hpt_format(spark_table)
        hpt.add_table(hpt.create_spark_table(
            spark_data,
            name=f"Spark Advance {octane}oct"
        ))
        
        # Fuel table
        fuel_table = tables["fuel_mass"]
        fuel_data = self._convert_table_to_hpt_format(fuel_table)
        hpt.add_table(hpt.create_fuel_mass_table(fuel_data))
        
        # MAF calibration
        maf_table = tables["maf"]
        voltage_points = list(zip(maf_table.row_axis.values, 
                                  [row[0] for row in maf_table.data]))
        hpt.add_table(hpt.create_maf_calibration(voltage_points))
        
        # Shift tables
        shift_normal = tables["shift_normal"]
        shift_data = self._convert_shift_table(shift_normal)
        hpt.add_table(hpt.create_shift_table(shift_data, name="Normal Shift Speeds"))
        
        shift_sport = tables["shift_sport"]
        shift_data = self._convert_shift_table(shift_sport)
        hpt.add_table(hpt.create_shift_table(shift_data, name="Performance Shift Speeds"))
        
        self.current_hpt_tune = hpt
        logger.info(f"Stage 1 tune created with {len(hpt.tables)} tables")
        
        return hpt
        
    def _detect_platform(self) -> str:
        """Detect GM platform from ECU calibration"""
        if not self.ecu.ecu_info:
            return "GM_E37"  # Default to LFX
            
        cal_id = self.ecu.ecu_info.calibration_id
        
        # Platform detection based on calibration ID patterns
        if cal_id.startswith("126"):  # LFX/LFY range
            return "GM_E37"
        elif cal_id.startswith("125"):  # LS3 range
            return "GM_E38"
        elif cal_id.startswith("1267"):  # Gen V
            return "GM_E41"
        else:
            return "GM_E37"  # Default
            
    def _convert_table_to_hpt_format(self, table: TuneTable) -> Dict[str, Dict[str, float]]:
        """Convert template table to HPT format"""
        result = {}
        for row_idx, row in enumerate(table.data):
            row_key = str(int(table.row_axis.values[row_idx]))
            result[row_key] = {}
            for col_idx, value in enumerate(row):
                col_key = str(int(table.col_axis.values[col_idx]))
                result[row_key][col_key] = value
        return result
        
    def _convert_shift_table(self, table: TuneTable) -> Dict[str, Dict[str, int]]:
        """Convert shift table to HPT format"""
        result = {}
        for col_idx, gear in enumerate(table.col_axis.values):
            gear_key = str(gear)
            result[gear_key] = {}
            for row_idx, row in enumerate(table.data):
                tps_key = str(int(table.row_axis.values[row_idx]))
                result[gear_key][tps_key] = int(row[col_idx])
        return result
        
    def export_tune(self, output_dir: str, format: str = "all") -> Dict[str, Path]:
        """
        Export tune in multiple formats
        
        Args:
            output_dir: Directory for output files
            format: 'hpt', 'csv', 'json', or 'all'
            
        Returns:
            Dictionary of exported file paths
        """
        if not self.current_hpt_tune:
            raise ValueError("No tune to export. Create a tune first.")
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format in ("json", "all"):
            json_path = output_dir / f"tune_{timestamp}.hpt.json"
            self.current_hpt_tune.export_json(json_path)
            exported["json"] = json_path
            
        if format in ("csv", "all"):
            csv_dir = output_dir / f"csv_tables_{timestamp}"
            csv_files = self.current_hpt_tune.export_csv_tables(csv_dir)
            exported["csv"] = csv_files
            
        # Generate tuning report
        report = self.current_hpt_tune.generate_tuning_report()
        report_path = output_dir / f"tuning_report_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        exported["report"] = report_path
        
        logger.info(f"Exported tune to {output_dir}")
        return exported
        
    def import_vcm_scanner_log(self, filepath: str) -> Dict:
        """
        Import and analyze a VCM Scanner CSV log
        
        Returns:
            Analysis summary with recommendations
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Log file not found: {filepath}")
            
        logger.info(f"Importing VCM Scanner log: {filepath}")
        
        # Import the log
        session = self.vcm_importer.import_csv(filepath)
        
        # Analyze
        analyzer = LogAnalyzer(session)
        summary = analyzer.generate_summary()
        
        # Generate recommendations
        engine = TuneRecommendationEngine(analyzer)
        recommendations = engine.generate_recommendations()
        
        result = {
            "file": filepath.name,
            "summary": summary,
            "recommendations": recommendations,
            "session": session
        }
        
        logger.info(f"Log analysis complete. Found {len(recommendations)} recommendations.")
        return result
        
    def get_pid_list(self, preset: str = "baseline") -> List[str]:
        """
        Get list of PIDs for logging
        
        Args:
            preset: 'baseline', 'performance', 'lfx_full', 'transmission'
            
        Returns:
            List of PID short names
        """
        if preset in LOGGING_PRESETS:
            return LOGGING_PRESETS[preset]["pids"]
            
        # Default to getting from database
        if preset == "lfx_full":
            return [p.short_name for p in self.pid_db.get_lfx_logging_pids()]
        elif preset == "performance":
            return [p.short_name for p in self.pid_db.get_performance_pids()]
        else:
            return [p.short_name for p in self.pid_db.get_essential_logging_pids()]
            
    def log_with_preset(self, preset: str = "baseline", 
                        duration: int = 300,
                        output: str = None) -> Path:
        """
        Log data using a predefined PID preset
        
        Args:
            preset: PID preset name
            duration: Logging duration in seconds
            output: Output CSV path
            
        Returns:
            Path to log file
        """
        pids = self.get_pid_list(preset)
        
        logger.info(f"Starting {preset} logging for {duration}s")
        logger.info(f"PIDs: {len(pids)} parameters")
        
        # Use parent class logging
        return self.log_baseline(duration=duration, output=output)
        
    def compare_tunes(self, tune1_path: str, tune2_path: str) -> Dict:
        """
        Compare two tune files and identify differences
        
        Returns:
            Comparison report
        """
        # Load tunes
        with open(tune1_path, 'r') as f:
            data1 = json.load(f)
        with open(tune2_path, 'r') as f:
            data2 = json.load(f)
            
        # Create comparison
        comparison = {
            "tune1": Path(tune1_path).name,
            "tune2": Path(tune2_path).name,
            "differences": {}
        }
        
        # Compare tables
        tables1 = set(data1.get("Tables", {}).keys())
        tables2 = set(data2.get("Tables", {}).keys())
        
        comparison["differences"]["added_tables"] = list(tables2 - tables1)
        comparison["differences"]["removed_tables"] = list(tables1 - tables2)
        
        # Compare common tables
        common = tables1 & tables2
        modified = []
        
        for table_name in common:
            t1 = data1["Tables"][table_name]
            t2 = data2["Tables"][table_name]
            
            # Simple comparison - check if data differs
            if t1.get("Data") != t2.get("Data"):
                modified.append(table_name)
                
        comparison["differences"]["modified_tables"] = modified
        
        return comparison
        
    def validate_against_logs(self, tune: HPTTuneFile, 
                               log_file: str) -> Dict:
        """
        Validate tune settings against logged data
        
        Checks:
        - Knock levels vs spark advance
        - Fuel trims vs fuel mass
        - Transmission temps vs line pressure
        """
        # Import log
        log_result = self.import_vcm_scanner_log(log_file)
        summary = log_result["summary"]
        
        validation = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check knock vs spark
        knock = summary.get("knock_analysis", {})
        if knock.get("max_retard", 0) > 4:
            validation["issues"].append(
                f"Knock detected ({knock['max_retard']}°) - reduce spark advance"
            )
            validation["valid"] = False
            
        # Check fuel trims
        fuel = summary.get("fuel_analysis", {})
        if fuel.get("correction_needed"):
            validation["issues"].append(
                f"Fuel trim issue: {fuel.get('recommendation')}"
            )
            validation["valid"] = False
            
        # Check transmission
        trans = summary.get("trans_analysis", {})
        if trans.get("max_slip", 0) > 100:
            validation["warnings"].append(
                f"High TCC slip detected ({trans['max_slip']} RPM)"
            )
            
        return validation
        
    def initialize_diagnostics(self):
        """Initialize diagnostic analyzer with current connection"""
        if self.ecu and self.ecu.connection:
            self.diagnostic_analyzer = DiagnosticAnalyzer(self.ecu.connection)
            logger.info("Diagnostic analyzer initialized")
        else:
            logger.warning("No ECU connection available for diagnostics")
            
    def read_dtcs(self) -> List[Dict]:
        """
        Read and analyze all DTCs from vehicle
        
        Returns:
            List of enriched DTC information
        """
        if not self.diagnostic_analyzer:
            self.initialize_diagnostics()
            
        if not self.diagnostic_analyzer:
            raise ConnectionError("No diagnostic connection available")
            
        return self.diagnostic_analyzer.read_all_dtcs()
        
    def analyze_dtcs(self) -> Dict:
        """
        Comprehensive DTC analysis with tuning recommendations
        
        Returns:
            Analysis report with recommendations
        """
        codes = self.read_dtcs()
        code_list = [c["code"] for c in codes]
        
        return self.dtc_db.analyze_codes(code_list)
        
    def pre_tune_diagnostic(self) -> Dict:
        """
        Perform complete pre-tune diagnostic inspection
        
        Returns:
            Diagnostic report with tuning clearance status
        """
        if not self.diagnostic_analyzer:
            self.initialize_diagnostics()
            
        if not self.diagnostic_analyzer:
            raise ConnectionError("No diagnostic connection available")
            
        # Full diagnostic report
        report = self.diagnostic_analyzer.generate_diagnostic_report()
        
        # Pre-tune inspection
        inspection = self.diagnostic_analyzer.pre_tune_inspection()
        
        return {
            "diagnostic_report": report.to_dict(),
            "pre_tune_inspection": inspection,
            "safe_to_tune": report.tuning_clearance and inspection.get("passed", False),
            "warnings": report.tuning_warnings + inspection.get("findings", [])
        }
        
    def clear_dtcs(self) -> bool:
        """Clear all DTCs and freeze frame data"""
        if not self.diagnostic_analyzer:
            self.initialize_diagnostics()
            
        if not self.diagnostic_analyzer:
            raise ConnectionError("No diagnostic connection available")
            
        return self.diagnostic_analyzer.clear_dtcs()
        
    def lookup_dtc(self, code: str) -> Optional[Dict]:
        """
        Look up DTC information
        
        Args:
            code: DTC code (e.g., "P0171")
            
        Returns:
            DTC information dictionary
        """
        dtc = self.dtc_db.get_dtc(code)
        return dtc.to_dict() if dtc else None
        
    def search_dtcs(self, query: str) -> List[Dict]:
        """
        Search DTC database
        
        Args:
            query: Search term
            
        Returns:
            List of matching DTCs
        """
        dtcs = self.dtc_db.search(query)
        return [d.to_dict() for d in dtcs]
        
    def get_tuning_related_dtcs(self) -> List[Dict]:
        """Get all tuning-related DTCs from database"""
        dtcs = self.dtc_db.get_tuning_related()
        return [d.to_dict() for d in dtcs]
        
    def generate_full_report(self, output_path: str = None) -> Dict:
        """
        Generate comprehensive tuning report
        
        Includes:
        - Vehicle information
        - Current tune summary
        - Diagnostic status
        - Recommended PIDs
        - Safety validation
        """
        report = {
            "generated": datetime.now().isoformat(),
            "vehicle": {},
            "tune": {},
            "diagnostics": {},
            "recommendations": {},
            "pid_presets": {}
        }
        
        # Vehicle info
        if self.ecu.ecu_info:
            report["vehicle"] = {
                "vin": self.ecu.ecu_info.vin,
                "calibration": self.ecu.ecu_info.calibration_id,
                "platform": self._detect_platform()
            }
            
        # Current tune
        if self.current_hpt_tune:
            report["tune"] = self.current_hpt_tune.generate_tuning_report()
            
        # DTC stats
        dtc_stats = self.dtc_db.get_statistics()
        report["diagnostics"]["dtc_database"] = {
            "total_codes": dtc_stats["total_codes"],
            "tuning_related": dtc_stats["tuning_related"],
            "top_categories": dict(list(dtc_stats["by_category"].items())[:5])
        }
        
        # PID presets
        for preset_name, preset_config in LOGGING_PRESETS.items():
            report["pid_presets"][preset_name] = {
                "description": preset_config["description"],
                "pid_count": len(preset_config["pids"]),
                "interval": preset_config["interval"]
            }
            
        # Export if path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
                
        return report


# Convenience functions for quick operations
def quick_stage1_tune(vin: str, octane: int = 93, 
                      output_dir: str = "./tunes") -> Path:
    """
    Quick Stage 1 tune generation without vehicle connection
    
    Args:
        vin: Vehicle VIN
        octane: Octane rating (87, 89, 91, 93)
        output_dir: Output directory
        
    Returns:
        Path to exported tune
    """
    agent = EnhancedHPTunersAgent()
    
    # Create tune without connection
    hpt = HPTTuneFile(vin=vin, calibration_id="AUTO", platform="GM_E37")
    
    # Generate Stage 1 tables
    tables = CompleteTuneBuilder.build_stage1_tune(octane=octane)
    
    # Export
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"stage1_{vin}_{octane}oct_{timestamp}"
    
    CompleteTuneBuilder.export_tune_package(tables, output_path)
    
    logger.info(f"Stage 1 tune exported to {output_path}")
    return output_path


def analyze_log_file(log_path: str) -> Dict:
    """
    Quick log analysis without vehicle connection
    
    Args:
        log_path: Path to VCM Scanner CSV
        
    Returns:
        Analysis results with recommendations
    """
    agent = EnhancedHPTunersAgent()
    return agent.import_vcm_scanner_log(log_path)


if __name__ == "__main__":
    # Demo: Create Stage 1 tune
    print("=" * 60)
    print("Enhanced HP Tuners AI Agent v2.0 Demo")
    print("=" * 60)
    
    # Example 1: Quick tune generation
    print("\n1. Generating Stage 1 tune...")
    tune_path = quick_stage1_tune(
        vin="2G1WB5E37D1157819",
        octane=93,
        output_dir="./demo_tunes"
    )
    print(f"   Exported to: {tune_path}")
    
    # Example 2: PID database query
    print("\n2. PID Database:")
    db = PIDDatabase()
    print(f"   Total PIDs: {len(db.pids)}")
    print(f"   Essential logging: {len(db.get_essential_logging_pids())}")
    print(f"   LFX performance: {len(db.get_lfx_logging_pids())}")
    
    # Example 3: Logging presets
    print("\n3. Logging Presets:")
    for name, preset in LOGGING_PRESETS.items():
        print(f"   - {name}: {preset['description']} ({len(preset['pids'])} PIDs)")
        
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
