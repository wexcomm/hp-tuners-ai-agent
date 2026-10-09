#!/usr/bin/env python3
"""
Channel Resolution — fuzzy channel-name matching across platforms.

HP Tuners channel names vary by vehicle, year, make, and logging profile.
The SAE-standard PIDs are similar but rarely identical. This module maps
canonical names ('rpm', 'knock', 'ltft1', ...) to whatever a given log
actually contains, via exact → case-insensitive → substring matching with
per-channel reject lists to avoid near-miss columns.

Used by copilot_analyze.py (full-log diagnostics) and wot_analyze.py
(WOT pull deep-dive). Add new canonical names + candidates as new
platforms turn up in real logs — that's the whole game here.
"""

from typing import Dict, List, Optional
from collections import defaultdict

# Candidate names in preference order. Optional per-channel reject
# substrings disqualify near-matches during the substring phase —
# e.g. we want elapsed "Time", not "Time of Latest Shift"; pedal position,
# not "Accelerator Pedal Position Sensor 1".
CHANNEL_CANDIDATES = {
    'pedal':      ['Accelerator Pedal Position', 'Accel Pedal Position', 'APP (%)', 'Accelerator Pedal'],
    'tps':        ['Throttle Position', 'Throttle Position (SAE)', 'Throttle %', 'Absolute Throttle Position'],
    'rpm':        ['Engine RPM (SAE)', 'Engine RPM', 'RPM'],
    'knock':      ['Total Knock Retard', 'Knock Retard', 'Total Knock Retard (SAE)'],
    'spark':      ['Timing Advance (SAE)', 'Timing Advance', 'Spark Advance', 'Ignition Timing'],
    'gear':       ['Trans Current Gear', 'Current Gear', 'Gear', 'Transmission Gear'],
    'tcc_slip':   ['TCC Slip', 'TCC Slip RPM', 'Torque Converter Slip'],
    'tcc_state':  ['TCC State', 'TCC Command', 'TCC PWM'],
    'iat':        ['Intake Air Temp', 'Intake Air Temperature (SAE)', 'IAT'],
    'clt':        ['Coolant Temp', 'Coolant Temperature (SAE)', 'ECT', 'Engine Coolant Temp'],
    'load':       ['Absolute Load (SAE)', 'Calculated Load (SAE)', 'Calculated Engine Load (SAE)', 'Engine Load'],
    'maf':        ['MAF Frequency', 'Mass Airflow (SAE)', 'MAF (g/s)', 'Mass Air Flow', 'MAF'],
    'afr_cmd':    ['Air-Fuel Ratio Commanded', 'Commanded Equivalence Ratio (SAE)', 'Commanded AFR', 'Commanded EQ Ratio'],
    'afr_wide':   ['Wideband AFR', 'Air Fuel Ratio', 'AFR'],
    'time':       ['Time (sec)', 'Time', 'Elapsed Time'],
    'ltft1':      ['Long Term Fuel Trim Bank 1 (SAE)', 'Long Term Fuel Trim Bank 1', 'LTFT Bank 1', 'LTFT B1'],
    'ltft2':      ['Long Term Fuel Trim Bank 2 (SAE)', 'Long Term Fuel Trim Bank 2', 'LTFT Bank 2', 'LTFT B2'],
    'stft1':      ['Short Term Fuel Trim Bank 1 (SAE)', 'Short Term Fuel Trim Bank 1', 'STFT Bank 1', 'STFT B1'],
    'stft2':      ['Short Term Fuel Trim Bank 2 (SAE)', 'Short Term Fuel Trim Bank 2', 'STFT Bank 2', 'STFT B2'],
    'vss':        ['Vehicle Speed (SAE)', 'Vehicle Speed', 'VSS', 'MPH'],
    'ethanol':    ['Ethanol Fuel % (SAE)', 'Ethanol %', 'Fuel Alcohol Content', 'Ethanol Concentration'],
    'baro':       ['Barometric Pressure (SAE)', 'Barometric Pressure', 'BARO'],
}

REJECT_SUBSTRINGS = {
    'time':  ['latest', 'of ', 'shift'],
    'tps':   ['sensor', 'desired', 'duty', 'learn', 'b (sae)', 'relative', 'actuator', 'offset'],
    'pedal': ['sensor', 'power', 'average', 'position d', 'position e', 'position 1', 'position 2'],
    'rpm':   [' commanded', 'desired'],
    'gear':  ['ratio'],
    'knock': ['learn'],
    'maf':   ['frequency corr'],
    'spark': ['base'],
    'vss':   ['sensor'],
}


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


class ChannelResolver:
    """Resolve canonical channel names against whatever a log actually has.

    Usage:
        res = ChannelResolver(name_to_indices)
        res.available('rpm')      # bool
        res.val(row, 'knock')     # float or None
        res.missing()             # ['tcc_state', ...]
        res.map                   # {'rpm': 'Engine RPM (SAE)', ...}
    """

    def __init__(self, name_to_indices: Dict[str, list]):
        self.name_to_indices = name_to_indices
        lowered = {n.lower(): n for n in name_to_indices.keys()}
        self._map: Dict[str, Optional[str]] = {}
        for canon, candidates in CHANNEL_CANDIDATES.items():
            resolved = None
            # exact, then case-insensitive exact
            for cand in candidates:
                if cand in name_to_indices:
                    resolved = cand
                    break
                if cand.lower() in lowered:
                    resolved = lowered[cand.lower()]
                    break
            # substring fallback
            if not resolved:
                rejects = REJECT_SUBSTRINGS.get(canon, [])
                for cand in candidates:
                    key = cand.lower()
                    for log_name_lower, log_name in lowered.items():
                        if any(r in log_name_lower for r in rejects):
                            continue
                        if key in log_name_lower or log_name_lower in key:
                            resolved = log_name
                            break
                    if resolved:
                        break
            self._map[canon] = resolved

    def available(self, canon: str) -> bool:
        return self._map.get(canon) is not None

    def missing(self) -> List[str]:
        return [c for c in CHANNEL_CANDIDATES if not self.available(c)]

    def actual(self, canon: str) -> Optional[str]:
        """The log's actual column name for a canonical channel."""
        return self._map.get(canon)

    def val(self, row, canon: str) -> Optional[float]:
        name = self._map.get(canon)
        if not name:
            return None
        for idx in self.name_to_indices.get(name, []):
            if idx < len(row) and row[idx]:
                return _safe_float(row[idx])
        return None
