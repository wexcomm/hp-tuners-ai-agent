#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Tuning Bridge - Real-time file sync between AI Agent and VCM Suite

Watches folders and automatically:
- Exports generated tunes to VCM Editor compatible formats
- Imports and analyzes VCM Scanner logs
- Provides real-time recommendations

Usage:
    python src/live_tuning_bridge.py
    
Folder Structure:
    ./bridge/
    ├── outgoing/      # AI-generated tunes → Copy to VCM Editor
    ├── incoming/      # Drop VCM Scanner CSVs here for analysis
    ├── stock/         # Place stock .hpt exports here
    └── archive/       # Processed files archived here
"""

import os
import sys
import time
import json
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import logging

# Optional color output
try:
    from colorama import init, Fore, Style
    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""

# Fix Windows console encoding
import sys
if sys.platform == 'win32':
    import os
    os.system('chcp 65001 >nul 2>&1')  # Set UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Watchdog for file system monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    print("Warning: watchdog not installed. Run: pip install watchdog")
    sys.exit(1)

# Import our modules
sys.path.insert(0, str(Path(__file__).parent))
from enhanced_agent import EnhancedHPTunersAgent, quick_stage1_tune, analyze_log_file
from hpt_file_exporter import HPTTuneFile
from table_templates import CompleteTuneBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    """Configuration for the tuning bridge"""
    bridge_dir: str = "./bridge"
    outgoing_dir: str = "./bridge/outgoing"
    incoming_dir: str = "./bridge/incoming"
    stock_dir: str = "./bridge/stock"
    archive_dir: str = "./bridge/archive"
    
    # Auto-export settings
    auto_export_csv: bool = True
    auto_export_json: bool = True
    auto_generate_report: bool = True
    
    # Analysis settings
    auto_analyze_logs: bool = True
    knock_threshold: float = 4.0  # Degrees
    fuel_trim_threshold: float = 5.0  # Percent
    
    # Real-time alerts
    alert_on_knock: bool = True
    alert_on_lean: bool = True
    alert_on_rich: bool = True
    
    def ensure_dirs(self):
        """Create all required directories"""
        for attr in ['bridge_dir', 'outgoing_dir', 'incoming_dir', 
                     'stock_dir', 'archive_dir']:
            Path(getattr(self, attr)).mkdir(parents=True, exist_ok=True)


class ConsoleUI:
    """Simple console UI for live status display"""
    
    def __init__(self):
        self.status_lines = []
        self.last_log = []
        self.running = True
        
    def print_header(self):
        """Print the header banner"""
        self.clear()
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  🔧 LIVE TUNING BRIDGE{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Real-time sync between AI Agent ↔ VCM Suite{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print()
        
    def print_status(self, config: BridgeConfig):
        """Print current status"""
        print(f"{Fore.GREEN}📁 Bridge Directories:{Style.RESET_ALL}")
        print(f"   Outgoing: {config.outgoing_dir}  → Copy CSVs to VCM Editor")
        print(f"   Incoming: {config.incoming_dir}  ← Drop VCM Scanner logs here")
        print(f"   Stock:    {config.stock_dir}     ← Place stock tune exports")
        print(f"   Archive:  {config.archive_dir}")
        print()
        
    def print_log_entry(self, timestamp: str, level: str, message: str):
        """Print a log entry with colors"""
        color = Fore.WHITE
        if level == "SUCCESS":
            color = Fore.GREEN
        elif level == "WARNING":
            color = Fore.YELLOW
        elif level == "ERROR":
            color = Fore.RED
        elif level == "ANALYSIS":
            color = Fore.MAGENTA
        elif level == "TUNE":
            color = Fore.CYAN
            
        print(f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {color}{message}{Style.RESET_ALL}")
        
    def clear(self):
        """Clear console"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def update_display(self, config: BridgeConfig, recent_events: List[Dict]):
        """Update the full display"""
        self.print_header()
        self.print_status(config)
        
        print(f"{Fore.YELLOW}📊 Recent Activity:{Style.RESET_ALL}")
        if recent_events:
            for event in recent_events[-10:]:  # Last 10 events
                self.print_log_entry(
                    event['time'],
                    event['level'],
                    event['message']
                )
        else:
            print("   Waiting for files...")
        print()
        
        print(f"{Fore.BLUE}Press Ctrl+C to stop{Style.RESET_ALL}")


class OutgoingHandler(FileSystemEventHandler):
    """Handles files placed in outgoing folder (tune generation requests)"""
    
    def __init__(self, bridge: 'LiveTuningBridge'):
        self.bridge = bridge
        
    def on_created(self, event):
        if not event.is_directory:
            self.bridge.handle_outgoing_file(event.src_path)
            
    def on_modified(self, event):
        if not event.is_directory:
            self.bridge.handle_outgoing_file(event.src_path)


class IncomingHandler(FileSystemEventHandler):
    """Handles VCM Scanner log files dropped in incoming folder"""
    
    def __init__(self, bridge: 'LiveTuningBridge'):
        self.bridge = bridge
        
    def on_created(self, event):
        if not event.is_directory:
            self.bridge.handle_incoming_file(event.src_path)


class LiveTuningBridge:
    """
    Real-time bridge between AI Agent and VCM Suite
    """
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self.config.ensure_dirs()
        
        self.ui = ConsoleUI()
        self.agent = EnhancedHPTunersAgent()
        self.events: List[Dict] = []
        
        self.observer = Observer()
        self.running = False
        
        # Initialize handlers
        self.outgoing_handler = OutgoingHandler(self)
        self.incoming_handler = IncomingHandler(self)
        
    def log(self, level: str, message: str):
        """Log an event"""
        event = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message
        }
        self.events.append(event)
        logger.info(f"[{level}] {message}")
        
    def handle_outgoing_file(self, filepath: str):
        """Process a tune generation request"""
        filepath = Path(filepath)
        
        # Skip non-JSON files (config files only)
        if filepath.suffix != '.json':
            return
            
        # Skip if already processed
        if filepath.name.startswith('processing_'):
            return
            
        self.log("TUNE", f"Processing tune request: {filepath.name}")
        
        try:
            # Read tune configuration
            with open(filepath, 'r') as f:
                config = json.load(f)
                
            # Generate tune
            vin = config.get('vin', 'UNKNOWN')
            octane = config.get('octane', 93)
            mods = config.get('mods', ['intake', 'exhaust'])
            tune_type = config.get('type', 'stage1')
            
            # Create tune
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_name = f"{tune_type}_{vin}_{octane}oct_{timestamp}"
            output_dir = Path(self.config.outgoing_dir) / output_name
            
            if tune_type == 'stage1':
                self._generate_stage1_tune(vin, octane, mods, output_dir)
            else:
                self.log("WARNING", f"Unknown tune type: {tune_type}")
                return
                
            # Archive the request file
            archive_path = Path(self.config.archive_dir) / f"request_{timestamp}.json"
            shutil.move(str(filepath), str(archive_path))
            
            self.log("SUCCESS", f"Tune exported to: {output_dir}")
            
            # Show summary
            self._show_tune_summary(output_dir)
            
        except Exception as e:
            self.log("ERROR", f"Failed to process tune: {e}")
            
    def _generate_stage1_tune(self, vin: str, octane: int, mods: List[str], 
                               output_dir: Path):
        """Generate Stage 1 tune package"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate tables
        tables = CompleteTuneBuilder.build_stage1_tune(
            vehicle="gm_lfx",
            octane=octane,
            mods=mods
        )
        
        # Export CSV tables for VCM Editor
        CompleteTuneBuilder.export_tune_package(tables, output_dir)
        
        # Also export as JSON
        hpt = HPTTuneFile(vin=vin, calibration_id="AUTO", platform="GM_E37")
        
        # Add spark table
        spark = tables['spark_main']
        spark_data = self._convert_to_hpt_format(spark)
        hpt.add_table(hpt.create_spark_table(spark_data, name=f"Spark {octane}oct"))
        
        # Add fuel table
        fuel = tables['fuel_mass']
        fuel_data = self._convert_to_hpt_format(fuel)
        hpt.add_table(hpt.create_fuel_mass_table(fuel_data))
        
        # Export JSON
        hpt.export_json(output_dir / "tune.hpt.json")
        
        # Generate report
        report = hpt.generate_tuning_report()
        with open(output_dir / "tuning_report.json", 'w') as f:
            json.dump(report, f, indent=2)
            
    def _convert_to_hpt_format(self, table) -> Dict:
        """Convert TuneTable to HPT format"""
        result = {}
        for row_idx, row in enumerate(table.data):
            row_key = str(int(table.row_axis.values[row_idx]))
            result[row_key] = {}
            for col_idx, value in enumerate(row):
                col_key = str(int(table.col_axis.values[col_idx]))
                result[row_key][col_key] = value
        return result
        
    def _show_tune_summary(self, output_dir: Path):
        """Display tune summary"""
        report_file = output_dir / "tuning_report.json"
        if report_file.exists():
            with open(report_file, 'r') as f:
                report = json.load(f)
                
            self.log("TUNE", f"  Tables: {report['Summary']['TotalTables']}")
            self.log("TUNE", f"  Categories: {', '.join(report['Summary']['Categories'])}")
            
            for name, table in report['Tables'].items():
                self.log("TUNE", f"  → {name}: {table['Min']:.1f} to {table['Max']:.1f} {table['Units']}")
                
    def handle_incoming_file(self, filepath: str):
        """Process a VCM Scanner log file"""
        filepath = Path(filepath)
        
        # Only process CSV files
        if filepath.suffix.lower() != '.csv':
            return
            
        # Wait for file to be fully written
        time.sleep(0.5)
        
        self.log("ANALYSIS", f"Analyzing log: {filepath.name}")
        
        try:
            # Analyze the log
            results = analyze_log_file(str(filepath))
            
            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save analysis report
            report_path = Path(self.config.incoming_dir) / f"analysis_{filepath.stem}_{timestamp}.json"
            with open(report_path, 'w') as f:
                json.dump(results, f, indent=2)
                
            # Display summary
            self._show_analysis_summary(results)
            
            # Check for issues
            self._check_for_issues(results)
            
            # Archive the original log
            archive_path = Path(self.config.archive_dir) / f"{filepath.stem}_{timestamp}.csv"
            shutil.move(str(filepath), str(archive_path))
            
            self.log("SUCCESS", f"Analysis complete: {report_path.name}")
            
        except Exception as e:
            self.log("ERROR", f"Failed to analyze log: {e}")
            
    def _show_analysis_summary(self, results: Dict):
        """Display analysis summary"""
        summary = results.get('summary', {})
        
        # RPM range
        rpm_range = summary.get('rpm_range', {})
        self.log("ANALYSIS", f"  RPM Range: {rpm_range.get('min', 0):.0f} - {rpm_range.get('max', 0):.0f}")
        
        # WOT events
        wot_events = summary.get('wot_events', 0)
        self.log("ANALYSIS", f"  WOT Events: {wot_events}")
        
        # Knock analysis
        knock = summary.get('knock_analysis', {})
        if knock.get('max_retard', 0) > 0:
            self.log("ANALYSIS", f"  Knock: {knock.get('total_events', 0)} events, max {knock.get('max_retard', 0):.1f}° retard")
        else:
            self.log("ANALYSIS", f"  Knock: None detected ✓")
            
        # Fuel analysis
        fuel = summary.get('fuel_analysis', {})
        self.log("ANALYSIS", f"  Fuel: {fuel.get('recommendation', 'N/A')}")
        
    def _check_for_issues(self, results: Dict):
        """Check for critical issues and alert"""
        summary = results.get('summary', {})
        recommendations = results.get('recommendations', [])
        
        # Check knock
        knock = summary.get('knock_analysis', {})
        if knock.get('max_retard', 0) > self.config.knock_threshold:
            self.log("WARNING", f"⚠️  KNOCK DETECTED: {knock.get('max_retard', 0):.1f}° - Reduce timing!")
            
        # Check recommendations
        for rec in recommendations:
            if rec.get('priority') in ['CRITICAL', 'HIGH']:
                self.log("WARNING", f"⚠️  [{rec.get('priority')}] {rec.get('category')}: {rec.get('action')}")
                
    def create_tune_request(self, vin: str, octane: int = 93, 
                            mods: List[str] = None, tune_type: str = 'stage1'):
        """Create a tune generation request file"""
        if mods is None:
            mods = ['intake', 'exhaust']
            
        request = {
            'vin': vin,
            'octane': octane,
            'mods': mods,
            'type': tune_type,
            'created': datetime.now().isoformat()
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        request_file = Path(self.config.outgoing_dir) / f"request_{timestamp}.json"
        
        with open(request_file, 'w') as f:
            json.dump(request, f, indent=2)
            
        self.log("TUNE", f"Created tune request: {request_file.name}")
        return request_file
        
    def quick_generate(self, vin: str, octane: int = 93, 
                       mods: List[str] = None) -> Path:
        """Quickly generate a tune and return output path"""
        self.log("TUNE", f"Quick generating Stage 1 tune for {vin}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_name = f"stage1_{vin}_{octane}oct_{timestamp}"
        output_dir = Path(self.config.outgoing_dir) / output_name
        
        self._generate_stage1_tune(vin, octane, mods or ['intake', 'exhaust'], output_dir)
        
        self.log("SUCCESS", f"Tune ready at: {output_dir}")
        return output_dir
        
    def start(self):
        """Start the bridge"""
        if not HAS_WATCHDOG:
            print("ERROR: watchdog not installed. Run: pip install watchdog")
            return
            
        self.running = True
        
        # Setup watchers
        self.observer.schedule(
            self.outgoing_handler, 
            self.config.outgoing_dir, 
            recursive=False
        )
        self.observer.schedule(
            self.incoming_handler, 
            self.config.incoming_dir, 
            recursive=False
        )
        
        self.observer.start()
        
        self.log("INFO", "Live Tuning Bridge started")
        self.log("INFO", f"Watching: {self.config.outgoing_dir}")
        self.log("INFO", f"Watching: {self.config.incoming_dir}")
        
        try:
            while self.running:
                self.ui.update_display(self.config, self.events)
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the bridge"""
        self.running = False
        self.observer.stop()
        self.observer.join()
        self.log("INFO", "Bridge stopped")
        
    def print_instructions(self):
        """Print usage instructions"""
        # Use ASCII-safe characters for Windows compatibility
        print(f"""
{Fore.CYAN}========================================================================
                     LIVE TUNING BRIDGE - USAGE                         
========================================================================{Style.RESET_ALL}

{Fore.GREEN}1. GENERATE A TUNE (Auto-Export to VCM Editor):{Style.RESET_ALL}

   Create a request file in: {self.config.outgoing_dir}
   
   Example request.json:
   {{
     "vin": "2G1WB5E37D1157819",
     "octane": 93,
     "mods": ["intake", "exhaust"],
     "type": "stage1"
   }}
   
   Or use Python:
   >>> bridge = LiveTuningBridge()
   >>> bridge.quick_generate(vin="YOURVIN", octane=93)

{Fore.YELLOW}2. ANALYZE VCM SCANNER LOGS:{Style.RESET_ALL}

   Simply drop your VCM Scanner CSV export into:
   {self.config.incoming_dir}
   
   The AI will automatically analyze and alert you to issues.

{Fore.MAGENTA}3. IMPORT TO VCM EDITOR:{Style.RESET_ALL}

   After tune generation, find your files in:
   {self.config.outgoing_dir}
   
   Look for the CSV tables folder and copy values into VCM Editor:
   - spark_main.csv -> Engine > Spark > Main Spark Advance
   - fuel_mass.csv  -> Engine > Fuel > Base Fuel Mass
   - maf.csv        -> Engine > Airflow > MAF Calibration
   - shift_*.csv    -> Transmission > Shift -> [Normal/Performance]

{Fore.CYAN}========================================================================{Style.RESET_ALL}
""")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Tuning Bridge for VCM Suite')
    parser.add_argument('--quick', '-q', help='Quick generate tune (VIN)', default=None)
    parser.add_argument('--octane', '-o', type=int, default=93, help='Octane rating')
    parser.add_argument('--mods', '-m', nargs='+', default=['intake', 'exhaust'], 
                        help='Modifications')
    parser.add_argument('--instructions', '-i', action='store_true',
                        help='Show usage instructions')
    
    args = parser.parse_args()
    
    bridge = LiveTuningBridge()
    
    if args.instructions:
        bridge.print_instructions()
        return
        
    if args.quick:
        # Quick generate mode
        output = bridge.quick_generate(args.quick, args.octane, args.mods)
        print(f"\nTune ready at:")
        print(f"  {output}")
        print(f"\n  CSV tables ready to copy to VCM Editor!")
        return
    
    # Interactive mode
    bridge.print_instructions()
    input("\nPress Enter to start the bridge...")
    bridge.start()


if __name__ == "__main__":
    main()
