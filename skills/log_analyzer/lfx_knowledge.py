"""
LFX Tuning Copilot — Knowledge Base
Maps symptoms, log findings, and vehicle conditions to specific
HP Tuners VCM Editor tables, cells, and safe adjustment ranges.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"        # Reducing values, well-tested
    MEDIUM = "medium"  # Moderate changes, verify with logs
    HIGH = "high"      # Aggressive changes, dyno recommended
    CRITICAL = "critical"  # Danger zone, expert only

class Confidence(Enum):
    HIGH = "high"      # Reproducible issue, known fix
    MEDIUM = "medium"  # Likely correct, but verify
    LOW = "low"        # Educated guess

@dataclass
class TableCell:
    """A specific cell in an HP Tuners table."""
    table_name: str           # Human-readable table name
    vcm_path: str             # VCM Editor navigation path
    axis_hint: str            # What the axes are (e.g., "RPM x Load")
    description: str = ""

@dataclass
class Adjustment:
    """A specific adjustment recommendation."""
    parameter: str            # What to change (e.g., "Spark Advance")
    direction: str            # "increase", "decrease", "set"
    amount: str               # Human-readable amount (e.g., "-2°")
    min_safe: float           # Minimum safe value
    max_safe: float           # Maximum safe value
    unit: str = ""

@dataclass
class TuningRule:
    """A rule that maps a symptom to a tuning action."""
    symptom: str              # What the log shows
    condition: str            # When this rule applies
    affected_cells: List[TableCell]
    adjustment: Adjustment
    risk: RiskLevel
    confidence: Confidence
    explanation: str          # Why this fix works
    verify_with: List[str] = field(default_factory=list)  # Log parameters to verify after

# =============================================================================
# SPARK TIMING RULES
# =============================================================================

SPARK_RULES = [
    TuningRule(
        symptom="Knock Retard detected",
        condition="Total Knock Retard > 2° in any cell, reproducible across 3+ pulls",
        affected_cells=[
            TableCell(
                table_name="Main Spark - High Octane",
                vcm_path="Engine → Spark → Main Spark → High Octane",
                axis_hint="RPM (x) vs. Absolute Load % (y)",
                description="Primary spark advance table for 91+ octane fuel"
            ),
            TableCell(
                table_name="Main Spark - Low Octane",
                vcm_path="Engine → Spark → Main Spark → Low Octane",
                axis_hint="RPM (x) vs. Absolute Load % (y)",
                description="Fallback table when knock is persistent"
            ),
        ],
        adjustment=Adjustment(
            parameter="Spark Advance",
            direction="decrease",
            amount="-2° per 2° of knock retard observed (max -4°)",
            min_safe=10.0,
            max_safe=35.0,
            unit="degrees"
        ),
        risk=RiskLevel.LOW,
        confidence=Confidence.HIGH,
        explanation=(
            "The LFX has good knock sensor sensitivity. Stock timing is conservative "
            "for 87 octane. On 91 octane, you may have added timing that was too "
            "aggressive for your fuel quality or atmospheric conditions. Reducing timing "
            "in the affected RPM/load cells eliminates knock."
        ),
        verify_with=["Total Knock Retard", "Timing Advance (SAE)", "Engine RPM", "Absolute Load"]
    ),
    TuningRule(
        symptom="No Knock Retard, conservative timing",
        condition="KR = 0° consistently, fuel is 91+ octane, no heat soak",
        affected_cells=[
            TableCell(
                table_name="Main Spark - High Octane",
                vcm_path="Engine → Spark → Main Spark → High Octane",
                axis_hint="RPM (x) vs. Absolute Load % (y)",
                description="Primary spark advance table"
            ),
        ],
        adjustment=Adjustment(
            parameter="Spark Advance",
            direction="increase",
            amount="+1° to +2° in 2000-5000 RPM range, verify no KR",
            min_safe=10.0,
            max_safe=38.0,
            unit="degrees"
        ),
        risk=RiskLevel.MEDIUM,
        confidence=Confidence.MEDIUM,
        explanation=(
            "If knock sensors show zero retard across multiple WOT pulls on quality fuel, "
            "there may be headroom for more timing. Add 1° at a time, log, verify no KR "
            "before adding more. Stop if KR exceeds 2°."
        ),
        verify_with=["Total Knock Retard", "Timing Advance (SAE)", "Intake Air Temp"]
    ),
]

# =============================================================================
# TRANSMISSION RULES — 6T40
# =============================================================================

TRANSMISSION_RULES = [
    TuningRule(
        symptom="1-2 shift clunk or harshness",
        condition="Felt/knock on 1-2 upshift, especially under light-medium throttle",
        affected_cells=[
            TableCell(
                table_name="Line Pressure - PCS 1 (1st Gear)",
                vcm_path="Transmission → General → Line Pressure → PCS 1",
                axis_hint="Usually fixed per gear",
                description="Line pressure for 1st gear clutch pack"
            ),
            TableCell(
                table_name="Shift Time - 1-2",
                vcm_path="Transmission → Shift → Shift Time → 1-2",
                axis_hint="Throttle % (x)",
                description="Time allowed for 1-2 shift completion"
            ),
            TableCell(
                table_name="Torque Reduction - 1-2",
                vcm_path="Transmission → Shift → Torque Reduction → 1-2",
                axis_hint="Throttle % (x)",
                description="How much engine torque to cut during 1-2 shift"
            ),
            TableCell(
                table_name="Fermi Overlap - 1-2",
                vcm_path="Transmission → Shift → Fermi Overlap → 1-2",
                axis_hint="Throttle % (x)",
                description="Overlap between releasing and applying clutches"
            ),
        ],
        adjustment=Adjustment(
            parameter="1-2 Shift Feel",
            direction="increase",
            amount="PCS 1: +15-20%, Shift Time: 0.35→0.25s, Torque Cut: 40%→20-25%, Fermi: 150→100-120ms",
            min_safe=0.0,
            max_safe=100.0,
            unit="varies"
        ),
        risk=RiskLevel.MEDIUM,
        confidence=Confidence.HIGH,
        explanation=(
            "The 1-2 clunk in 6T40 is a well-known issue caused by low line pressure in 1st, "
            "combined with aggressive torque cut and too-fast clutch handoff. Raising pressure "
            "and reducing torque cut while slightly slowing the shift eliminates the clunk without "
            "causing slip."
        ),
        verify_with=["PCS 1 Cmd Pressure", "Trans Current Gear", "Engine RPM", "Throttle Position"]
    ),
    TuningRule(
        symptom="Gear hunting in 4-5-6",
        condition="Trans rapidly oscillating between 4th, 5th, 6th on light throttle, slight hills",
        affected_cells=[
            TableCell(
                table_name="Upshift RPM - 4-5, 5-6",
                vcm_path="Transmission → Shift → Upshift → Normal",
                axis_hint="Throttle % (x)",
                description="RPM thresholds for upshifts"
            ),
            TableCell(
                table_name="Downshift RPM - 5-4, 6-5",
                vcm_path="Transmission → Shift → Downshift → Normal",
                axis_hint="Throttle % (x)",
                description="RPM thresholds for downshifts"
            ),
            TableCell(
                table_name="TCC Lockup - 4th, 5th, 6th",
                vcm_path="Transmission → TCC → Apply/Release",
                axis_hint="Vehicle Speed (x) vs. Throttle % (y)",
                description="Torque converter clutch lockup schedule"
            ),
        ],
        adjustment=Adjustment(
            parameter="Shift Schedule & TCC",
            direction="increase",
            amount="Upshift RPM: +300-500 per gear. TCC: lock 5-10 mph later in 4-6",
            min_safe=1000.0,
            max_safe=6000.0,
            unit="RPM / mph"
        ),
        risk=RiskLevel.LOW,
        confidence=Confidence.HIGH,
        explanation=(
            "Gear hunting happens when the transmission is programmed for maximum fuel economy. "
            "The TCC locks too early and the upshift RPM is too low, so any slight load change "
            "forces a downshift. Raising both keeps the trans in gear longer and prevents the "
            "busy-shifting feeling."
        ),
        verify_with=["Trans Current Gear", "TCC Slip", "TCC Desired Slip", "Vehicle Speed", "Throttle Position"]
    ),
    TuningRule(
        symptom="Upshift reluctance (high RPM, light throttle)",
        condition="RPM > 2500, TPS < 20%, gear held in 3rd/4th/5th longer than desired",
        affected_cells=[
            TableCell(
                table_name="Upshift RPM - Normal",
                vcm_path="Transmission → Shift → Upshift → Normal",
                axis_hint="Throttle % (x)",
                description="RPM at which upshifts occur under normal driving"
            ),
            TableCell(
                table_name="Downshift RPM - Normal",
                vcm_path="Transmission → Shift → Downshift → Normal",
                axis_hint="Throttle % (x)",
                description="RPM at which downshifts occur"
            ),
        ],
        adjustment=Adjustment(
            parameter="Upshift RPM",
            direction="decrease",
            amount="Lower upshift RPM by 200-300 in light-throttle cells (0-25% TPS)",
            min_safe=1200.0,
            max_safe=4500.0,
            unit="RPM"
        ),
        risk=RiskLevel.LOW,
        confidence=Confidence.MEDIUM,
        explanation=(
            "If the transmission is holding gears too long at light throttle, the upshift RPM "
            "is set too high for those cells. Lowering it makes the trans shift sooner, which "
            "improves drivability and fuel economy in light-load cruising."
        ),
        verify_with=["Trans Current Gear", "Engine RPM", "Throttle Position", "Vehicle Speed"]
    ),
    TuningRule(
        symptom="Shift flare (RPM rises during shift)",
        condition="RPM spikes during upshift before settling in next gear",
        affected_cells=[
            TableCell(
                table_name="Line Pressure - Shift Event",
                vcm_path="Transmission → General → Line Pressure → Shift",
                axis_hint="Gear / Throttle %",
                description="Pressure during shift events"
            ),
            TableCell(
                table_name="Shift Time",
                vcm_path="Transmission → Shift → Shift Time",
                axis_hint="Gear / Throttle %",
                description="Time allowed for shifts"
            ),
        ],
        adjustment=Adjustment(
            parameter="Shift Pressure",
            direction="increase",
            amount="+10-15% line pressure during affected shift. Slightly increase shift time (+0.02s)",
            min_safe=0.0,
            max_safe=100.0,
            unit="%"
        ),
        risk=RiskLevel.MEDIUM,
        confidence=Confidence.HIGH,
        explanation=(
            "Flare means the releasing clutch is letting go before the applying clutch has enough "
            "pressure to grab. More line pressure during the shift event fixes this. Don't go too "
            "aggressive or shifts get harsh."
        ),
        verify_with=["Engine RPM", "Trans Current Gear", "PCS Cmd Pressures"]
    ),
    TuningRule(
        symptom="TCC not locking or excessive slip",
        condition="TCC Slip > 50 RPM in 4th/5th/6th at cruising speed, TCC commanded on",
        affected_cells=[
            TableCell(
                table_name="TCC Apply Pressure",
                vcm_path="Transmission → TCC → Apply Pressure",
                axis_hint="Vehicle Speed (x) vs. Throttle % (y)",
                description="Pressure applied to TCC solenoid"
            ),
            TableCell(
                table_name="TCC Apply/Release Speed",
                vcm_path="Transmission → TCC → Apply/Release",
                axis_hint="Gear / Throttle %",
                description="Speed thresholds for TCC engagement"
            ),
        ],
        adjustment=Adjustment(
            parameter="TCC Pressure / Lockup Speed",
            direction="increase",
            amount="TCC pressure: +10-15%. Lockup speed: raise 5-10 mph if hunting occurs.",
            min_safe=0.0,
            max_safe=100.0,
            unit="varies"
        ),
        risk=RiskLevel.LOW,
        confidence=Confidence.MEDIUM,
        explanation=(
            "Excessive TCC slip wastes fuel and generates heat. More apply pressure forces the "
            "lockup clutch to engage harder. If TCC hunting is the issue (lock/unlock/lock), "
            "raising the lockup speed prevents the borderline conditions that cause cycling."
        ),
        verify_with=["TCC Slip", "TCC Desired Slip", "Trans Fluid Temp", "Vehicle Speed"]
    ),
]

# =============================================================================
# FUEL RULES
# =============================================================================

FUEL_RULES = [
    TuningRule(
        symptom="Lean condition (positive fuel trims)",
        condition="LTFT > +8% consistently, especially at idle or cruise",
        affected_cells=[
            TableCell(
                table_name="VE Table (Volumetric Efficiency)",
                vcm_path="Engine → Fuel → VE → Primary",
                axis_hint="RPM (x) vs. MAP / Load (y)",
                description="Base fuel calculation table"
            ),
            TableCell(
                table_name="MAF Calibration",
                vcm_path="Engine → Airflow → MAF",
                axis_hint="Frequency / Voltage (x)",
                description="Mass Airflow sensor calibration curve"
            ),
        ],
        adjustment=Adjustment(
            parameter="VE or MAF",
            direction="increase",
            amount="VE: +5-8% in affected cells. OR MAF: rescale if intake mod installed.",
            min_safe=0.0,
            max_safe=120.0,
            unit="%"
        ),
        risk=RiskLevel.MEDIUM,
        confidence=Confidence.MEDIUM,
        explanation=(
            "Positive LTFT means the PCM is adding fuel beyond base calculation. If you have "
            "an intake mod, the MAF curve may be wrong. If stock, the VE table may be slightly "
            "off for your engine's actual airflow characteristics."
        ),
        verify_with=["Short Term Fuel Trim Bank 1", "Long Term Fuel Trim Bank 1", "Mass Airflow", "Commanded EQ Ratio"]
    ),
    TuningRule(
        symptom="Rich condition (negative fuel trims)",
        condition="LTFT < -8% consistently",
        affected_cells=[
            TableCell(
                table_name="VE Table",
                vcm_path="Engine → Fuel → VE → Primary",
                axis_hint="RPM (x) vs. MAP / Load (y)",
                description="Base fuel calculation table"
            ),
        ],
        adjustment=Adjustment(
            parameter="VE",
            direction="decrease",
            amount="-5-8% in affected cells",
            min_safe=0.0,
            max_safe=120.0,
            unit="%"
        ),
        risk=RiskLevel.MEDIUM,
        confidence=Confidence.MEDIUM,
        explanation=(
            "Negative LTFT means the PCM is pulling fuel. The VE table is over-estimating airflow "
            "in those cells. Reduce VE to match actual airflow."
        ),
        verify_with=["Short Term Fuel Trim Bank 1", "Long Term Fuel Trim Bank 1", "Mass Airflow"]
    ),
]

# =============================================================================
# TORQUE MANAGEMENT RULES
# =============================================================================

TORQUE_RULES = [
    TuningRule(
        symptom="Throttle not reaching 100% at WOT",
        condition="Max TPS during WOT pull < 99%, pedal at 100%",
        affected_cells=[
            TableCell(
                table_name="Driver Demand",
                vcm_path="Engine → Torque → Driver Demand",
                axis_hint="Pedal % (x) vs. RPM (y)",
                description="How much throttle the PCM allows per pedal input"
            ),
            TableCell(
                table_name="Torque Limiters",
                vcm_path="Engine → Torque → Limiters",
                axis_hint="Various",
                description="Maximum allowed torque by condition"
            ),
        ],
        adjustment=Adjustment(
            parameter="Driver Demand / Torque Limits",
            direction="increase",
            amount="Raise driver demand at 100% pedal to allow 100% throttle. Raise torque limiters if needed.",
            min_safe=0.0,
            max_safe=100.0,
            unit="%"
        ),
        risk=RiskLevel.MEDIUM,
        confidence=Confidence.HIGH,
        explanation=(
            "If pedal is 100% but throttle won't go past 95%, the PCM is limiting torque. This is "
            "common in fleet/taxi calibrations. Raising driver demand at max pedal position unlocks "
            "full throttle response."
        ),
        verify_with=["Throttle Position", "Accelerator Pedal Position", "Engine Torque", "Delivered Engine Torque"]
    ),
]

# =============================================================================
# MASTER RULE LIST
# =============================================================================

ALL_RULES = SPARK_RULES + TRANSMISSION_RULES + FUEL_RULES + TORQUE_RULES


def find_rules_by_symptom(symptom_substring: str) -> List[TuningRule]:
    """Find rules whose symptom contains the given substring (case-insensitive)."""
    return [r for r in ALL_RULES if symptom_substring.lower() in r.symptom.lower()]


def get_rules_for_category(category: str) -> List[TuningRule]:
    """Get rules by category name."""
    cats = {
        "spark": SPARK_RULES,
        "timing": SPARK_RULES,
        "transmission": TRANSMISSION_RULES,
        "trans": TRANSMISSION_RULES,
        "fuel": FUEL_RULES,
        "torque": TORQUE_RULES,
    }
    return cats.get(category.lower(), [])
