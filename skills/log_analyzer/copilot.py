#!/usr/bin/env python3
"""
LFX Tuning Copilot — Main CLI
Your AI tuning partner for 2012-2013 Chevy Impala LFX 3.6L

Usage:
    python3 copilot.py analyze <log.csv>              # Analyze a log file
    python3 copilot.py session new "Description"      # Create new tuning session
    python3 copilot.py session list                   # List all sessions
    python3 copilot.py session show <id>              # Show session history
    python3 copilot.py change <session_id> <table> <param> <old> <new>  # Log a change
    python3 copilot.py compare <log1> <log2>          # Compare before/after logs
    python3 copilot.py wot <log.csv>                   # WOT pull deep-dive (premium)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from copilot_analyze import (
    parse_hptuners_csv, detect_knock, detect_gear_hunting, detect_shift_clunk,
    detect_tcc_slip, detect_fuel_trims, detect_torque_limiting,
    detect_upshift_reluctance, generate_suggestions, print_report
)
from session_tracker import SessionTracker


def cmd_analyze(args):
    """Analyze a log file with optional session tracking."""
    if len(args) < 1:
        print("Usage: python3 copilot.py analyze <log.csv> [--session <id>] [--platform lfx|gm_generic|generic]")
        sys.exit(1)
    
    log_path = args[0]
    session_id = None
    platform = None
    
    if "--session" in args:
        idx = args.index("--session")
        if idx + 1 < len(args):
            session_id = int(args[idx + 1])
    if "--platform" in args:
        idx = args.index("--platform")
        if idx + 1 < len(args):
            platform = args[idx + 1]
    
    print(f"🏎️  HP Tuners Copilot — Analyzing: {log_path}")
    print()
    
    from copilot_analyze import run_full_analysis, print_report
    all_findings, suggestions, rows_count, platform, res = run_full_analysis(log_path, platform)
    resolved = sum(1 for v in res._map.values() if v)
    print(f"Loaded {rows_count:,} data rows | {resolved}/{len(res._map)} canonical channels resolved")
    print(f"Found {len(all_findings)} issues")
    
    print_report(suggestions, rows_count, log_path, platform)
    
    # Track in session if requested
    if session_id:
        tracker = SessionTracker()
        tracker.log_analysis(
            session_id, log_path,
            findings=[{'category': f.category, 'severity': f.severity,
                      'description': f.description, 'sample_count': f.sample_count,
                      'max_value': f.max_value, 'avg_value': f.avg_value} for f in all_findings],
            suggestions=[{'priority': s.priority, 'action': s.before_after,
                         'confidence': s.confidence_score, 'risk': s.risk_score} for s in suggestions]
        )
        print(f"\n📊 Logged to session {session_id}")
        tracker.close()
    
    return len(all_findings)


def cmd_session(args):
    """Manage tuning sessions."""
    tracker = SessionTracker()
    
    if len(args) < 1:
        print("Usage: python3 copilot.py session <new|list|show> [args...]")
        tracker.close()
        sys.exit(1)
    
    subcmd = args[0]
    
    if subcmd == "new":
        desc = " ".join(args[1:]) if len(args) > 1 else ""
        sid = tracker.create_session(description=desc)
        print(f"✅ Created session {sid}")
        print(f"   Use: python3 copilot.py analyze <log.csv> --session {sid}")
        
    elif subcmd == "list":
        sessions = tracker.list_sessions()
        if not sessions:
            print("No sessions yet. Create one with: python3 copilot.py session new")
        else:
            print("📋 Tuning Sessions")
            print("-" * 60)
            for s in sessions:
                status = "🟢" if s.get('status') == 'active' else "⚪"
                print(f"  {status} [{s['id']}] {s['created_at']} — {s['description'] or '(no description)'}")
                print(f"      Baseline: {s.get('baseline_log') or 'N/A'}")
    
    elif subcmd == "show":
        if len(args) < 2:
            print("Usage: python3 copilot.py session show <session_id>")
            tracker.close()
            sys.exit(1)
        
        sid = int(args[1])
        history = tracker.get_session_history(sid)
        
        if not history['session']:
            print(f"Session {sid} not found")
            tracker.close()
            sys.exit(1)
        
        s = history['session']
        print("=" * 60)
        print(f"  📁 Session {sid}: {s.get('description', '')}")
        print(f"  Vehicle: {s.get('vehicle', 'N/A')}")
        print(f"  Created: {s.get('created_at', 'N/A')}")
        print(f"  Baseline: {s.get('baseline_log', 'N/A')}")
        print("=" * 60)
        
        if history['changes']:
            print(f"\n  🔧 Changes Made ({history['change_count']})")
            print("  " + "-" * 56)
            for c in history['changes']:
                print(f"  [{c['made_at']}] {c['table_name']}: {c['old_value']} → {c['new_value']}")
                print(f"    Path: {c['vcm_path']}")
                print(f"    Reason: {c['reason']}")
        
        if history['logs']:
            print(f"\n  📊 Analysis Logs ({history['log_count']})")
            print("  " + "-" * 56)
            for l in history['logs']:
                print(f"  [{l['logged_at']}] {l['log_path']}")
                if l['notes']:
                    print(f"    Notes: {l['notes']}")
    
    else:
        print(f"Unknown session command: {subcmd}")
    
    tracker.close()


def cmd_change(args):
    """Log a tuning change to a session."""
    if len(args) < 5:
        print("Usage: python3 copilot.py change <session_id> <table> <param> <old_val> <new_val> [reason]")
        sys.exit(1)
    
    session_id = int(args[0])
    table = args[1]
    param = args[2]
    old_val = args[3]
    new_val = args[4]
    reason = " ".join(args[5:]) if len(args) > 5 else ""
    
    tracker = SessionTracker()
    tracker.log_change(session_id, table, "", param, old_val, new_val, reason)
    print(f"✅ Logged change to session {session_id}: {table} {param}: {old_val} → {new_val}")
    tracker.close()


def cmd_wot(args):
    """WOT pull deep-dive analysis."""
    if len(args) < 1:
        print("Usage: python3 copilot.py wot <log.csv> [--min-rpm 2000]")
        sys.exit(1)
    try:
        from wot_analyze import analyze_wot_pulls, print_wot_report
    except ImportError:
        print()
        print("  ⭐ WOT pull deep-dive is part of HP Tuners Copilot PREMIUM.")
        print("     Get it on Agensi: https://www.agensi.io")
        print("     (premium adds per-pull scoring, cross-pull comparison,")
        print("      and false-knock detection outside WOT)")
        print()
        sys.exit(0)
    log_path = args[0]
    min_rpm = 2000.0
    if "--min-rpm" in args:
        min_rpm = float(args[args.index("--min-rpm") + 1])
    pulls, res, rows = analyze_wot_pulls(log_path, min_rpm=min_rpm)
    print_wot_report(pulls, log_path, res, rows)


def cmd_compare(args):
    """Compare two logs (before/after)."""
    if len(args) < 2:
        print("Usage: python3 copilot.py compare <before.csv> <after.csv>")
        sys.exit(1)
    
    log1, log2 = args[0], args[1]
    
    print(f"🔬 Comparing: {log1} → {log2}")
    print()
    
    # Quick comparison of key metrics
    for label, path in [("BEFORE", log1), ("AFTER", log2)]:
        _, name_to_indices, rows = parse_hptuners_csv(path)
        
        kr_vals = [float(get_value(r, name_to_indices, 'Total Knock Retard') or 0) for r in rows]
        kr_vals = [v for v in kr_vals if v > 0]
        
        tcc_slips = []
        for r in rows:
            slip = float(get_value(r, name_to_indices, 'TCC Slip') or 0)
            gear = int(float(get_value(r, name_to_indices, 'Trans Current Gear') or 0))
            if gear in [4, 5, 6]:
                tcc_slips.append(abs(slip))
        
        ltft = [float(get_value(r, name_to_indices, 'Long Term Fuel Trim Bank 1 (SAE)') or 0) for r in rows]
        ltft = [v for v in ltft if v != 0]
        
        print(f"  {label}:")
        print(f"    Knock events: {len(kr_vals)} (max: {max(kr_vals) if kr_vals else 0:.1f}°)")
        print(f"    TCC avg slip (4-6): {sum(tcc_slips)/max(1,len(tcc_slips)):.0f} RPM")
        print(f"    LTFT avg: {sum(ltft)/max(1,len(ltft)):+.1f}%")
        print()
    
    print("  💡 Interpretation:")
    print("    - Knock ↓ = good")
    print("    - TCC slip ↓ = good")
    print("    - LTFT closer to 0 = good")


def get_value(row, name_to_indices, name):
    """Helper for compare command."""
    indices = name_to_indices.get(name, [])
    for idx in indices:
        if idx < len(row):
            val = row[idx]
            if val:
                return val
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == "analyze":
        cmd_analyze(args)
        sys.exit(0)  # findings are the product, not an error condition
    elif cmd == "session":
        cmd_session(args)
    elif cmd == "change":
        cmd_change(args)
    elif cmd == "wot":
        cmd_wot(args)
    elif cmd == "compare":
        cmd_compare(args)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
