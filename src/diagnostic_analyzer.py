#!/usr/bin/env python3
"""
Diagnostic Analyzer Module
Integrates DTC reading, analysis, and tuning recommendations
"""

import obd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import logging

from dtc_database import DTCDatabase, DTC, DTCSeverity

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticReport:
    """Complete diagnostic report"""
    timestamp: str
    vin: str
    codes: List[Dict]
    analysis: Dict
    readiness: Dict
    freeze_frame: Optional[Dict] = None
    recommendations: List[Dict] = field(default_factory=list)
    tuning_clearance: bool = False
    tuning_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "vin": self.vin,
            "dtc_count": len(self.codes),
            "codes": self.codes,
            "analysis": self.analysis,
            "readiness_monitors": self.readiness,
            "freeze_frame": self.freeze_frame,
            "recommendations": self.recommendations,
            "tuning_clearance": self.tuning_clearance,
            "tuning_warnings": self.tuning_warnings
        }


class DiagnosticAnalyzer:
    """
    Advanced diagnostic analyzer with DTC integration
    """
    
    def __init__(self, connection: obd.OBD = None):
        self.connection = connection
        self.dtc_db = DTCDatabase()
        
    def set_connection(self, connection: obd.OBD):
        """Set OBD connection"""
        self.connection = connection
        
    def read_all_dtcs(self) -> List[Dict]:
        """
        Read all DTCs from vehicle and enrich with database info
        """
        if not self.connection:
            raise ConnectionError("No OBD connection")
            
        codes = []
        
        # Read stored DTCs
        response = self.connection.query(obd.commands.GET_DTC)
        if response.is_successful():
            for code, description in response.value:
                enriched = self._enrich_dtc(code, description)
                codes.append(enriched)
                
        return codes
        
    def _enrich_dtc(self, code: str, description: str = None) -> Dict:
        """Enrich DTC with database information"""
        dtc = self.dtc_db.get_dtc(code)
        
        if dtc:
            return {
                "code": code,
                "description": dtc.description,
                "category": dtc.category,
                "severity": dtc.severity.value,
                "tuning_related": dtc.tuning_related,
                "symptoms": dtc.symptoms,
                "possible_causes": dtc.possible_causes,
                "affected_systems": dtc.affected_systems
            }
        else:
            return {
                "code": code,
                "description": description or "Unknown code",
                "category": "Unknown",
                "severity": "Unknown",
                "tuning_related": False
            }
            
    def get_freeze_frame(self) -> Optional[Dict]:
        """Get freeze frame data for first DTC"""
        if not self.connection:
            return None
            
        # Note: python-obd may not support freeze frame directly
        # This is a placeholder for the concept
        logger.info("Freeze frame data not available via OBD")
        return None
        
    def check_readiness(self) -> Dict:
        """Check readiness monitor status"""
        if not self.connection:
            raise ConnectionError("No OBD connection")
            
        readiness = {}
        
        # Read readiness status
        response = self.connection.query(obd.commands.STATUS)
        if response.is_successful():
            status = response.value
            readiness = {
                "mil_on": status.MIL,
                "dtc_count": status.DTC_count,
                "ignition_type": status.ignition_type,
                "monitors": {}
            }
            
            # Get supported monitors
            for monitor in status.__dict__:
                if hasattr(status, monitor) and monitor not in ['MIL', 'DTC_count', 'ignition_type']:
                    try:
                        val = getattr(status, monitor)
                        if isinstance(val, obd.protocols.OBDStatus):
                            readiness["monitors"][monitor] = val.name
                    except:
                        pass
                        
        return readiness
        
    def clear_dtcs(self) -> bool:
        """Clear all DTCs and freeze frame data"""
        if not self.connection:
            raise ConnectionError("No OBD connection")
            
        response = self.connection.query(obd.commands.CLEAR_DTC)
        if response.is_successful():
            logger.info("DTCs cleared successfully")
            return True
        else:
            logger.error("Failed to clear DTCs")
            return False
            
    def generate_diagnostic_report(self) -> DiagnosticReport:
        """Generate complete diagnostic report"""
        
        # Get VIN
        vin_response = self.connection.query(obd.commands.VIN)
        vin = str(vin_response.value) if vin_response.is_successful() else "Unknown"
        
        # Read DTCs
        codes = self.read_all_dtcs()
        
        # Analyze codes
        code_list = [c["code"] for c in codes]
        analysis = self.dtc_db.analyze_codes(code_list)
        
        # Check readiness
        readiness = self.check_readiness()
        
        # Get freeze frame
        freeze_frame = self.get_freeze_frame()
        
        # Assess tuning clearance
        tuning_clearance, tuning_warnings = self._assess_tuning_clearance(codes, analysis)
        
        return DiagnosticReport(
            timestamp=datetime.now().isoformat(),
            vin=vin,
            codes=codes,
            analysis=analysis,
            readiness=readiness,
            freeze_frame=freeze_frame,
            recommendations=analysis.get("recommendations", []),
            tuning_clearance=tuning_clearance,
            tuning_warnings=tuning_warnings
        )
        
    def _assess_tuning_clearance(self, codes: List[Dict], 
                                  analysis: Dict) -> Tuple[bool, List[str]]:
        """
        Assess if vehicle is safe to tune
        
        Returns:
            (clearance_granted, warnings)
        """
        warnings = []
        
        # Check for critical DTCs
        critical_codes = [c for c in codes 
                         if c.get("severity") == DTCSeverity.CRITICAL.value]
        if critical_codes:
            warnings.append(f"CRITICAL: {len(critical_codes)} critical DTC(s) present")
            for c in critical_codes[:3]:
                warnings.append(f"  - {c['code']}: {c['description']}")
            return False, warnings
            
        # Check for misfires
        misfire_codes = [c for c in codes if "Misfire" in c.get("description", "")]
        if misfire_codes:
            warnings.append("CRITICAL: Misfire detected - do not tune until fixed")
            return False, warnings
            
        # Check for severe fuel system issues
        fuel_codes = [c for c in codes 
                     if c.get("category") == "Fuel System" and 
                     c.get("severity") == DTCSeverity.SEVERE.value]
        if fuel_codes:
            warnings.append("WARNING: Severe fuel system issues detected")
            for c in fuel_codes:
                warnings.append(f"  - {c['code']}: Fix before tuning")
            return False, warnings
            
        # Check for VVT issues
        vvt_codes = [c for c in codes if c.get("category") == "VVT System"]
        if vvt_codes:
            warnings.append("WARNING: VVT system codes present")
            warnings.append("  → Check oil level/quality and VVT operation")
            
        # Check for transmission issues
        trans_codes = [c for c in codes if c.get("category") == "Transmission"]
        if trans_codes:
            warnings.append("WARNING: Transmission codes present")
            warnings.append("  → Verify transmission health before power increase")
            
        # Check for tuning-related codes
        tuning_codes = [c for c in codes if c.get("tuning_related")]
        if tuning_codes:
            warnings.append(f"INFO: {len(tuning_codes)} tuning-related code(s) present")
            warnings.append("  → Clear codes after fixing issues, verify before tuning")
            
        # MIL status
        if analysis.get("readiness", {}).get("mil_on"):
            warnings.append("WARNING: Check Engine Light is ON")
            
        # If we got here with only warnings (no critical issues)
        if not warnings:
            return True, ["✓ Vehicle appears ready for tuning"]
        else:
            # Has warnings but not critical
            has_critical = any("CRITICAL" in w for w in warnings)
            return not has_critical, warnings
            
    def pre_tune_inspection(self) -> Dict:
        """
        Perform comprehensive pre-tune inspection
        
        Checks:
        1. DTC status
        2. Readiness monitors
        3. Key sensor readings
        4. Fuel trims
        """
        inspection = {
            "timestamp": datetime.now().isoformat(),
            "passed": False,
            "checks": {},
            "findings": [],
            "recommendations": []
        }
        
        # Check 1: DTC Status
        codes = self.read_all_dtcs()
        inspection["checks"]["dtc_check"] = {
            "passed": len(codes) == 0,
            "code_count": len(codes),
            "codes": [c["code"] for c in codes]
        }
        
        if codes:
            inspection["findings"].append(f"{len(codes)} DTC(s) present")
            
        # Check 2: Readiness Monitors
        readiness = self.check_readiness()
        incomplete = [m for m, status in readiness.get("monitors", {}).items() 
                     if status != "COMPLETE"]
        inspection["checks"]["readiness_check"] = {
            "passed": len(incomplete) <= 2,  # Some incomplete OK
            "incomplete_monitors": incomplete
        }
        
        if incomplete:
            inspection["findings"].append(f"{len(incomplete)} readiness monitors incomplete")
            
        # Check 3: Basic sensor readings
        sensor_checks = {}
        
        # Coolant temp
        coolant = self.connection.query(obd.commands.COOLANT_TEMP)
        if coolant.is_successful():
            temp = coolant.value.magnitude
            sensor_checks["coolant_temp"] = {
                "value": temp,
                "passed": 70 <= temp <= 110
            }
            if temp < 70:
                inspection["findings"].append(f"Engine not at operating temp ({temp}°C)")
                
        # Fuel trims
        stft = self.connection.query(obd.commands.SHORT_FUEL_TRIM_1)
        ltft = self.connection.query(obd.commands.LONG_FUEL_TRIM_1)
        if stft.is_successful() and ltft.is_successful():
            stft_val = stft.value.magnitude
            ltft_val = ltft.value.magnitude
            sensor_checks["fuel_trims"] = {
                "stft": stft_val,
                "ltft": ltft_val,
                "passed": abs(stft_val) < 10 and abs(ltft_val) < 10
            }
            if abs(stft_val) > 10 or abs(ltft_val) > 10:
                inspection["findings"].append(f"Fuel trims high: STFT={stft_val:.1f}%, LTFT={ltft_val:.1f}%")
                
        # O2 sensor
        o2 = self.connection.query(obd.commands.O2_B1S1)
        if o2.is_successful():
            voltage = o2.value.magnitude if hasattr(o2.value, 'magnitude') else o2.value
            sensor_checks["o2_sensor"] = {
                "voltage": voltage,
                "passed": 0.1 <= voltage <= 0.9
            }
            
        inspection["checks"]["sensor_check"] = sensor_checks
        
        # Overall pass/fail
        all_passed = all(c.get("passed", False) for c in inspection["checks"].values())
        inspection["passed"] = all_passed
        
        # Generate recommendations
        if not all_passed:
            inspection["recommendations"].append("Fix all issues before proceeding with tune")
        if incomplete:
            inspection["recommendations"].append("Complete drive cycle to set all readiness monitors")
        if sensor_checks.get("fuel_trims", {}).get("passed") == False:
            inspection["recommendations"].append("Address fuel trim issues - check for vacuum leaks or MAF calibration")
            
        return inspection
        
    def monitor_for_dtcs_during_logging(self, duration_seconds: int = 300) -> List[Dict]:
        """
        Monitor for new DTCs during data logging
        
        Useful for detecting issues during WOT pulls
        """
        import time
        
        logger.info(f"Monitoring for DTCs during {duration_seconds}s logging...")
        
        # Get baseline DTCs
        baseline_codes = set(c["code"] for c in self.read_all_dtcs())
        new_codes = []
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # Check every 10 seconds
            time.sleep(10)
            
            current_codes = self.read_all_dtcs()
            for code_info in current_codes:
                code = code_info["code"]
                if code not in baseline_codes and code not in [c["code"] for c in new_codes]:
                    logger.warning(f"NEW DTC DETECTED: {code} - {code_info['description']}")
                    new_codes.append(code_info)
                    
        return new_codes


def quick_diagnostic_check(port: str = None) -> Dict:
    """
    Quick standalone diagnostic check
    
    Usage:
        results = quick_diagnostic_check("/dev/rfcomm0")
        print(f"DTCs found: {len(results['codes'])}")
        print(f"Safe to tune: {results['tuning_clearance']}")
    """
    import obd
    
    connection = obd.OBD(port) if port else obd.OBD()
    
    analyzer = DiagnosticAnalyzer(connection)
    report = analyzer.generate_diagnostic_report()
    
    return report.to_dict()


if __name__ == "__main__":
    # Demo the diagnostic analyzer
    print("=" * 60)
    print("Diagnostic Analyzer Demo")
    print("=" * 60)
    
    # Simulate DTC analysis without vehicle connection
    db = DTCDatabase()
    
    test_codes = ["P0171", "P0300", "P0420"]
    print(f"\nAnalyzing codes: {test_codes}")
    
    analysis = db.analyze_codes(test_codes)
    
    print(f"\nCodes Found: {len(analysis['codes_found'])}")
    print(f"Critical Issues: {len(analysis['critical_issues'])}")
    print(f"Tuning Impact: {len(analysis['tuning_impact'])}")
    
    print("\nDetailed Code Info:")
    for code_info in analysis['codes_found']:
        print(f"\n  {code_info['code']}: {code_info['description']}")
        print(f"    Category: {code_info['category']}")
        print(f"    Severity: {code_info['severity']}")
        if code_info['tuning_related']:
            print(f"    ⚠️ TUNING RELATED")
            
    print("\nRecommendations:")
    for rec in analysis['recommendations']:
        print(f"\n  [{rec['priority']}] {rec['category']}")
        print(f"    {rec['message']}")
        print(f"    → {rec['action']}")
        print(f"    Codes: {', '.join(rec['codes'])}")
        
    print("\n" + "=" * 60)
