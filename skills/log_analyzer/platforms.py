#!/usr/bin/env python3
"""
Platform packs — what the Copilot knows about specific vehicle platforms.

The rule ENGINE is universal: knock heuristics, fuel-trim thresholds, TCC slip
limits, gear-hunt detection work on any HP Tuners CSV because the physics is
the same. What's platform-specific is WHERE the tables live in the editor
(VCM Editor paths, axis conventions, table names).

Packs layer on top of the engine:
  - lfx        → exact VCM Editor paths for GM LFX 3.6L (2012-13 Impala etc.)
  - gm_generic → GM-wide guidance; engine-family specifics marked as such
  - generic    → honest fallback: adjustment logic + "find the analogous table"

Auto-detection uses channel fingerprints (some exports carry no VIN). Override
with --platform on the CLI. New packs are data, not code — add an entry plus
its fingerprint channels.
"""

from typing import Dict, List, Optional

PACKS: Dict[str, dict] = {
    'lfx': {
        'label': 'GM LFX 3.6L V6 (2010-2015: Impala, Camaro, ATS, CTS, Equinox…)',
        'exact_paths': True,
        'path_note': (
            "VCM Editor paths reference GM LFX calibration structure "
            "(E39/E39A ECM + 6T40/6T45/6T50 TCM)."
        ),
        'engines': ['LFX', 'LLT (partial — verify timing limits)', 'LFW'],
    },
    'gm_generic': {
        'label': 'GM (generic — exact table paths not in this pack)',
        'exact_paths': False,
        'path_note': (
            "Rules shown use the LFX reference platform's paths. Your calibration "
            "has the same FUNCTIONS (main spark, line pressure, TCC apply, shift "
            "time) under GM-standard naming — locate the analogous table in your "
            "editor before editing."
        ),
        'engines': [],
    },
    'generic': {
        'label': 'Unknown / other make',
        'exact_paths': False,
        'path_note': (
            "This log doesn't match a known GM fingerprint, so the Copilot "
            "provides the diagnostic finding + adjustment logic, and YOU locate "
            "the matching table in your platform's editor. The knock-retard and "
            "fuel-trim heuristics are combustion physics — they hold anywhere. "
            "Transmission advice assumes a modern automatic with a lockup "
            "converter and electronic line pressure; verify before applying."
        ),
        'engines': [],
    },
}

# Channels that indicate a GM 6-speed automatic (6T40/6T45/6T50/6L series share
# these pressure-control-solenoid channels). Presence ⇒ at least gm_generic.
GM_FINGERPRINTS = [
    'PCS 1 Cmd Pressure',
    'PCS 2 Cmd Pressure',
    'Fill Pressure Cmd',
    'TCC Desired Slip',
]


def detect_platform(name_to_indices: Dict[str, list]) -> str:
    """Best-effort platform detection from channel names.

    Returns 'lfx' only via explicit user flag elsewhere — there is no
    channel-only way to prove an LFX. Presence of GM TCM fingerprints
    ⇒ 'gm_generic'; otherwise 'generic'.
    """
    for f in GM_FINGERPRINTS:
        if f in name_to_indices:
            return 'gm_generic'
    # TCC + gear without PCS is still likely GM, but weaker evidence
    if 'TCC Slip' in name_to_indices and 'Trans Current Gear' in name_to_indices:
        return 'gm_generic'
    return 'generic'


def get_pack(pack_id: str) -> dict:
    return PACKS.get(pack_id, PACKS['generic'])


def platform_banner(pack_id: str) -> str:
    p = get_pack(pack_id)
    return f"Platform: {p['label']}"


def path_disclaimer(pack_id: str) -> Optional[str]:
    """Show under the report when exact paths aren't guaranteed."""
    p = get_pack(pack_id)
    if p['exact_paths']:
        return None
    return p['path_note']
