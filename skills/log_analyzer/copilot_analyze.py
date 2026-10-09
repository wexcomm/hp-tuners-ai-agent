#!/usr/bin/env python3
"""
LFX Tuning Copilot — Enhanced Log Analyzer
Parses HP Tuners CSV logs and produces ACTIONABLE tuning suggestions
with specific VCM Editor table paths, cell coordinates, and safe ranges.

Usage:
    python3 copilot_analyze.py <path_to_hptuners_log.csv>
"""

import sys
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lfx_knowledge import (
    ALL_RULES, SPARK_RULES, TRANSMISSION_RULES, FUEL_RULES, TORQUE_RULES,
    RiskLevel, Confidence, TuningRule
)
from channels import ChannelResolver
from platforms import detect_platform, platform_banner, path_disclaimer
from platforms import detect_platform, platform_banner, path_disclaimer


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Finding:
    """A detected issue in the log, ready for suggestion mapping."""
    category: str           # "Spark", "Transmission", "Fuel", "Torque"
    severity: str           # "Critical", "Warning", "Info"
    description: str        # Human-readable finding
    affected_rpm_range: Optional[Tuple[float, float]] = None
    affected_load_range: Optional[Tuple[float, float]] = None
    sample_count: int = 0
    max_value: Optional[float] = None
    avg_value: Optional[float] = None
    raw_data: Dict = field(default_factory=dict)

@dataclass
class Suggestion:
    """A concrete tuning suggestion with VCM Editor navigation."""
    priority: int           # 1 = do first, higher = less urgent
    finding: Finding
    rule: TuningRule
    specific_cells: List[str] = field(default_factory=list)
    confidence_score: str = ""
    risk_score: str = ""
    before_after: str = ""


# =============================================================================
# LOG PARSER (v3 compatible)
# =============================================================================

def parse_hptuners_csv(path: str):
    """Parse HP Tuners CSV with [Channel Information] metadata."""
    with open(path, 'r') as f:
        lines = f.readlines()
    
    info_start = None
    data_start = None
    for i, line in enumerate(lines):
        if '[Channel Information]' in line:
            info_start = i + 1
        if '[Channel Data]' in line:
            data_start = i + 1
            break
    
    if not info_start or not data_start:
        raise ValueError("Could not find [Channel Information] or [Channel Data] sections")
    
    pid_row = lines[info_start].strip().split(',')
    name_row = lines[info_start + 1].strip().split(',')
    unit_row = lines[info_start + 2].strip().split(',')
    
    idx_to_name = {i: name for i, name in enumerate(name_row)}
    name_to_indices = defaultdict(list)
    for i, name in enumerate(name_row):
        name_to_indices[name].append(i)
    
    rows = []
    for line in lines[data_start:]:
        if not line.strip():
            continue
        vals = line.strip().split(',')
        if len(vals) < 2:
            continue
        rows.append(vals)
    
    return idx_to_name, name_to_indices, rows


def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def get_value(row, name_to_indices, name):
    """Get first non-empty value for a column name."""
    indices = name_to_indices.get(name, [])
    for idx in indices:
        if idx < len(row):
            val = row[idx]
            if val:
                return val
    return None


# =============================================================================
# FINDING DETECTORS
# =============================================================================

def detect_knock(res, rows) -> List[Finding]:
    """Detect knock retard events and map to specific RPM/load cells."""
    findings = []
    knock_events = []

    for i, row in enumerate(rows):
        kr = res.val(row, 'knock')
        if kr and kr > 0:
            rpm = res.val(row, 'rpm')
            load = res.val(row, 'load')
            knock_events.append({'kr': kr, 'rpm': rpm, 'load': load, 'idx': i})
    
    if not knock_events:
        return []
    
    # Group by RPM bins to identify affected cells
    rpm_bins = defaultdict(list)
    for e in knock_events:
        if e['rpm']:
            rbin = int(e['rpm'] / 500) * 500
            rpm_bins[rbin].append(e)
    
    # Find the worst RPM bins
    for rbin, events in sorted(rpm_bins.items()):
        max_kr = max(e['kr'] for e in events)
        avg_kr = sum(e['kr'] for e in events) / len(events)
        avg_load = sum(e['load'] for e in events if e['load']) / max(1, sum(1 for e in events if e['load']))
        
        if max_kr >= 2.0:
            severity = "Critical" if max_kr >= 4.0 else "Warning"
            findings.append(Finding(
                category="Spark",
                severity=severity,
                description=(
                    f"Knock retard detected: max {max_kr:.1f}°, avg {avg_kr:.1f}° "
                    f"in {len(events)} events @ {rbin}-{rbin+500} RPM"
                ),
                affected_rpm_range=(rbin, rbin + 500),
                affected_load_range=(avg_load - 10, avg_load + 10) if avg_load else None,
                sample_count=len(events),
                max_value=max_kr,
                avg_value=avg_kr,
                raw_data={'rpm_bin': rbin, 'events': events}
            ))
    
    return findings


def detect_gear_hunting(res, rows) -> List[Finding]:
    """Detect gear hunting in 4-5-6 range."""
    findings = []
    gear_data = []

    for i, row in enumerate(rows):
        gear = res.val(row, 'gear')
        if gear is not None:
            gear_data.append({
                'gear': int(gear),
                'time': res.val(row, 'time'),
                'idx': i
            })
    
    if not gear_data:
        return []
    
    hunts = []
    for i in range(len(gear_data) - 15):
        window = gear_data[i:i+15]
        gears = [g['gear'] for g in window]
        unique = set(gears)

        if len(unique) <= 3 and all(g in [4, 5, 6] for g in unique):
            changes = sum(1 for j in range(1, len(gears)) if gears[j] != gears[j-1])
            if changes >= 4:
                t_start = window[0]['time'] or 0
                t_end = window[-1]['time'] or 0
                hunts.append((t_start, t_end, gears, changes))
    
    # Deduplicate
    deduped = []
    for h in hunts:
        if not deduped or abs(h[0] - deduped[-1][0]) > 2.0:
            deduped.append(h)
    
    if deduped:
        findings.append(Finding(
            category="Transmission",
            severity="Warning",
            description=(
                f"Gear hunting detected: {len(deduped)} events in 4-5-6 range. "
                f"Trans rapidly oscillating between gears instead of holding."
            ),
            sample_count=len(deduped),
            raw_data={'hunts': deduped}
        ))
    
    return findings


def detect_shift_clunk(res, rows) -> List[Finding]:
    """Detect 1-2 shift harshness via RPM behavior."""
    findings = []

    # Look for rapid RPM drop + spike on 1-2 upshift
    shift_events = []
    for i in range(len(rows) - 5):
        gear_now = res.val(rows[i], 'gear')
        gear_next = res.val(rows[i+3], 'gear')

        if gear_now == 1 and gear_next == 2:
            rpm_now = res.val(rows[i], 'rpm')
            rpm_mid = res.val(rows[i+2], 'rpm')
            rpm_end = res.val(rows[i+4], 'rpm')

            if rpm_now and rpm_mid and rpm_end:
                # Clunk = RPM overshoots before settling
                if rpm_mid > rpm_now * 1.05 and rpm_end < rpm_mid:
                    shift_events.append({
                        'rpm_drop': rpm_now - rpm_end,
                        'overshoot': rpm_mid - rpm_now,
                        'idx': i
                    })
    
    if len(shift_events) >= 3:
        avg_overshoot = sum(e['overshoot'] for e in shift_events) / len(shift_events)
        findings.append(Finding(
            category="Transmission",
            severity="Warning",
            description=(
                f"1-2 shift clunk detected: {len(shift_events)} harsh shifts, "
                f"avg RPM overshoot {avg_overshoot:.0f} RPM"
            ),
            sample_count=len(shift_events),
            max_value=avg_overshoot,
            raw_data={'events': shift_events}
        ))
    
    return findings


def detect_tcc_slip(res, rows) -> List[Finding]:
    """Detect TCC slip issues."""
    findings = []
    slip_by_gear = defaultdict(list)

    for row in rows:
        slip = res.val(row, 'tcc_slip')
        gear = res.val(row, 'gear')
        if slip is not None and gear is not None and int(gear) in [4, 5, 6]:
            slip_by_gear[int(gear)].append(abs(slip))
    
    for gear, slips in slip_by_gear.items():
        avg_slip = sum(slips) / len(slips)
        excessive = [s for s in slips if s > 50]
        
        if excessive:
            findings.append(Finding(
                category="Transmission",
                severity="Warning" if len(excessive) / len(slips) < 0.3 else "Critical",
                description=(
                    f"TCC excessive slip in {gear}th gear: {len(excessive)}/{len(slips)} samples "
                    f"above 50 RPM (avg {avg_slip:.0f} RPM)"
                ),
                sample_count=len(excessive),
                avg_value=avg_slip,
                raw_data={'gear': gear}
            ))
    
    return findings


def detect_fuel_trims(res, rows) -> List[Finding]:
    """Detect lean/rich conditions via fuel trims."""
    findings = []

    for bank, canon in [(1, 'ltft1'), (2, 'ltft2')]:
        if not res.available(canon):
            continue
        vals = [res.val(row, canon) for row in rows]
        ltft = [x for x in vals if x is not None]

        if ltft:
            avg_ltft = sum(ltft) / len(ltft)
            if abs(avg_ltft) > 8:
                condition = "lean" if avg_ltft > 0 else "rich"
                findings.append(Finding(
                    category="Fuel",
                    severity="Warning" if abs(avg_ltft) < 12 else "Critical",
                    description=(
                        f"Fuel trim {condition}: Bank {bank} LTFT avg {avg_ltft:+.1f}% "
                        f"over {len(ltft)} samples"
                    ),
                    sample_count=len(ltft),
                    avg_value=avg_ltft,
                    raw_data={'bank': bank}
                ))

    return findings


def detect_torque_limiting(res, rows) -> List[Finding]:
    """Detect when throttle is limited despite pedal at 100%."""
    findings = []

    wot_samples = []
    for row in rows:
        pedal = res.val(row, 'pedal')
        tps = res.val(row, 'tps')

        if pedal and pedal >= 95 and tps and tps < 98:
            wot_samples.append({'pedal': pedal, 'tps': tps})
    
    if wot_samples:
        avg_tps = sum(s['tps'] for s in wot_samples) / len(wot_samples)
        findings.append(Finding(
            category="Torque",
            severity="Info" if avg_tps > 95 else "Warning",
            description=(
                f"Torque management limiting throttle: {len(wot_samples)} samples "
                f"with pedal ≥95% but throttle only {avg_tps:.1f}%"
            ),
            sample_count=len(wot_samples),
            avg_value=avg_tps,
            raw_data={'samples': wot_samples}
        ))
    
    return findings


def detect_upshift_reluctance(res, rows) -> List[Finding]:
    """Detect when trans holds gears too long at light throttle."""
    findings = []
    reluctant = []

    for i, row in enumerate(rows):
        gear = res.val(row, 'gear')
        rpm = res.val(row, 'rpm')
        tps = res.val(row, 'tps')

        if gear is not None and int(gear) in [3, 4, 5] and rpm and rpm > 2500 and tps and tps < 20:
            reluctant.append({'rpm': rpm, 'tps': tps, 'gear': int(gear), 'idx': i})
    
    if len(reluctant) >= 10:
        # Find continuous stretches
        stretches = []
        cur = [reluctant[0]]
        for r in reluctant[1:]:
            if r['idx'] - cur[-1]['idx'] <= 3:
                cur.append(r)
            else:
                if len(cur) >= 5:
                    stretches.append(cur)
                cur = [r]
        if len(cur) >= 5:
            stretches.append(cur)
        
        if stretches:
            findings.append(Finding(
                category="Transmission",
                severity="Info",
                description=(
                    f"Upshift reluctance: {len(stretches)} events where trans held "
                    f"gear {stretches[0][0]['gear']} above 2500 RPM with light throttle (<20% TPS)"
                ),
                sample_count=len(stretches),
                raw_data={'stretches': stretches}
            ))
    
    return findings


# =============================================================================
# SUGGESTION GENERATOR
# =============================================================================

def generate_suggestions(findings: List[Finding]) -> List[Suggestion]:
    """Map findings to concrete tuning suggestions using the knowledge base."""
    suggestions = []
    
    for finding in findings:
        # Find matching rules
        matched_rules = []
        
        if finding.category == "Spark" and "Knock" in finding.description:
            # If knock is present, only show reduction rules, NOT increase rules
            if finding.max_value and finding.max_value > 0:
                matched_rules = [r for r in SPARK_RULES if r.adjustment.direction == "decrease"]
            else:
                matched_rules = [r for r in SPARK_RULES if r.adjustment.direction == "increase"]
        elif finding.category == "Transmission":
            if "hunting" in finding.description.lower():
                matched_rules = [r for r in TRANSMISSION_RULES if "hunting" in r.symptom.lower()]
            elif "clunk" in finding.description.lower() or "harsh" in finding.description.lower():
                matched_rules = [r for r in TRANSMISSION_RULES if "clunk" in r.symptom.lower()]
            elif "slip" in finding.description.lower():
                matched_rules = [r for r in TRANSMISSION_RULES if "slip" in r.symptom.lower()]
            elif "reluctance" in finding.description.lower():
                matched_rules = [r for r in TRANSMISSION_RULES if "reluctance" in r.symptom.lower()]
            else:
                matched_rules = TRANSMISSION_RULES
        elif finding.category == "Fuel":
            if "lean" in finding.description.lower():
                matched_rules = [r for r in FUEL_RULES if "lean" in r.symptom.lower()]
            elif "rich" in finding.description.lower():
                matched_rules = [r for r in FUEL_RULES if "rich" in r.symptom.lower()]
            else:
                matched_rules = FUEL_RULES
        elif finding.category == "Torque":
            matched_rules = TORQUE_RULES
        
        # Generate suggestions from matched rules
        for rule in matched_rules:
            priority = 1 if finding.severity == "Critical" else (2 if finding.severity == "Warning" else 3)
            
            # Build specific cell descriptions
            cells = []
            for cell in rule.affected_cells:
                cell_desc = f"  📍 {cell.table_name}\n     Path: {cell.vcm_path}\n     Axes: {cell.axis_hint}"
                if finding.affected_rpm_range:
                    cell_desc += f"\n     Affected RPM: {finding.affected_rpm_range[0]:.0f}-{finding.affected_rpm_range[1]:.0f}"
                if finding.affected_load_range:
                    cell_desc += f"\n     Affected Load: {finding.affected_load_range[0]:.0f}%-{finding.affected_load_range[1]:.0f}%"
                cells.append(cell_desc)
            
            suggestions.append(Suggestion(
                priority=priority,
                finding=finding,
                rule=rule,
                specific_cells=cells,
                confidence_score=rule.confidence.value.upper(),
                risk_score=rule.risk.value.upper(),
                before_after=f"Adjust: {rule.adjustment.parameter} → {rule.adjustment.amount}"
            ))
    
    # Sort by priority
    suggestions.sort(key=lambda s: s.priority)
    return suggestions


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def print_report(suggestions: List[Suggestion], rows_count: int, log_path: str, platform: str = None):
    """Print a beautiful, actionable tuning report."""
    print("=" * 80)
    print("  🏎️  HP TUNERS COPILOT — ANALYSIS REPORT")
    print("=" * 80)
    print(f"  Log: {log_path}")
    print(f"  Data rows: {rows_count:,}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if platform:
        print(f"  {platform_banner(platform)}")
    print()

    disc = path_disclaimer(platform) if platform else None
    if disc:
        print(f"  ℹ️  {disc}")
        print()
    
    if not suggestions:
        print("  ✅ No tuning issues detected. Log looks healthy!")
        print()
        print("  💡 Tip: If you're looking for power gains, try a WOT pull log and")
        print("     check for conservative timing (zero knock retard = potential headroom).")
        return
    
    # Group by priority
    critical = [s for s in suggestions if s.priority == 1]
    warnings = [s for s in suggestions if s.priority == 2]
    info = [s for s in suggestions if s.priority == 3]
    
    if critical:
        print("  🔴 CRITICAL — Fix These First")
        print("  " + "-" * 76)
        for s in critical:
            _print_suggestion(s)
        print()
    
    if warnings:
        print("  🟡 WARNINGS — Address Soon")
        print("  " + "-" * 76)
        for s in warnings:
            _print_suggestion(s)
        print()
    
    if info:
        print("  🟢 INFO — Optional Improvements")
        print("  " + "-" * 76)
        for s in info:
            _print_suggestion(s)
        print()
    
    print("=" * 80)
    print("  📋 NEXT STEPS")
    print("=" * 80)
    print("  1. Make ONE change at a time in VCM Editor")
    print("  2. Flash the tune")
    print("  3. Log the same driving conditions")
    print("  4. Re-run this analyzer to verify improvement")
    print("  5. Repeat until all issues are resolved")
    print()
    print("  ⚠️  Always save your stock tune before making changes!")
    print("  ⚠️  Use a battery charger when flashing!")
    print("=" * 80)


def _print_suggestion(s: Suggestion):
    """Print a single suggestion block."""
    icon = "🔴" if s.priority == 1 else ("🟡" if s.priority == 2 else "🟢")
    print(f"\n  {icon} {s.finding.description}")
    print(f"     Confidence: {s.confidence_score} | Risk: {s.risk_score}")
    print()
    print(f"     📝 WHY: {s.rule.explanation}")
    print()
    print(f"     🔧 ACTION: {s.before_after}")
    for cell in s.specific_cells:
        print(cell)
    print()
    print(f"     ✅ VERIFY WITH: {', '.join(s.rule.verify_with)}")


# =============================================================================
# MAIN
# =============================================================================

def run_full_analysis(log_path: str, platform: str = None):
    """Parse → resolve channels → detect → suggest.
    Returns (findings, suggestions, rows_count, platform, resolver)."""
    idx_to_name, name_to_indices, rows = parse_hptuners_csv(log_path)
    res = ChannelResolver(name_to_indices)
    if not platform:
        platform = detect_platform(name_to_indices)

    all_findings = []
    all_findings.extend(detect_knock(res, rows))
    all_findings.extend(detect_gear_hunting(res, rows))
    all_findings.extend(detect_shift_clunk(res, rows))
    all_findings.extend(detect_tcc_slip(res, rows))
    all_findings.extend(detect_fuel_trims(res, rows))
    all_findings.extend(detect_torque_limiting(res, rows))
    all_findings.extend(detect_upshift_reluctance(res, rows))

    suggestions = generate_suggestions(all_findings)
    return all_findings, suggestions, len(rows), platform, res


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 copilot_analyze.py <log.csv> [--platform lfx|gm_generic|generic]")
        sys.exit(1)

    log_path = sys.argv[1]
    platform = None
    if "--platform" in sys.argv:
        platform = sys.argv[sys.argv.index("--platform") + 1]

    _, suggestions, rows_count, platform, res = run_full_analysis(log_path, platform)
    resolved = sum(1 for v in res._map.values() if v)
    print(f"[channels] resolved {resolved}/{len(res._map)} canonical channels")
    print_report(suggestions, rows_count, log_path, platform)


if __name__ == '__main__':
    main()
