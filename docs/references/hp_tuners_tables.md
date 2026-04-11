# HP Tuners Table Reference

## Engine Tables

### Fuel

#### Base Fuel Mass
- **Purpose**: Base fuel injector pulse width calculation
- **Axis**: RPM x Load (or MAP)
- **Units**: mg/cylinder or ms
- **Effect**: Primary fuel delivery map
- **Safe Change**: ±5% increments
- **Critical**: Yes - too lean = detonation

#### Power Enrichment (PE)
- **Purpose**: Additional fuel at WOT
- **Trigger**: TPS > threshold, RPM > threshold
- **Units**: AFR target or multiplier
- **Default**: 12.5:1 - 13.0:1 AFR
- **Boosted**: 11.0:1 - 11.5:1 AFR
- **Safe Change**: 0.5 AFR increments

#### MAF Calibration
- **Purpose**: Converts MAF voltage to airflow
- **Format**: Voltage vs Airflow (g/s)
- **Critical**: Yes - affects all fuel calculations
- **Verification**: Compare calculated vs actual AFR

#### Injector Data
- **Flow Rate**: cc/min or lb/hr
- **Offset**: Opening time vs voltage
- **Slopes**: Low/High pulse width correction
- **Critical**: Yes - must match physical injectors

### Spark

#### Main Spark Advance
- **Purpose**: Primary ignition timing
- **Axis**: RPM x Load
- **Units**: Degrees BTDC
- **Effect**: Power, efficiency, knock margin
- **Safe Change**: 1-2 degrees increments
- **Critical**: Too much = knock, too little = power loss

#### Knock Retard (KR)
- **Purpose**: Reduce timing when knock detected
- **Max Retard**: Limit of timing pull
- **Sensitivity**: Knock sensor gain
- **Safe**: Enable always, 8-10° max retard

#### Cylinder Offset
- **Purpose**: Individual cylinder correction
- **Use**: Balance cylinder temps/power
- **Safe Change**: ±2 degrees

### Airflow

#### Throttle Area
- **Purpose**: Convert TPS % to airflow area
- **Effect**: Tip-in response, idle control
- **Modified Throttle Bodies**: Must rescale

#### Idle Airflow
- **Purpose**: Base idle air
- **Adjustments**: For cam overlap, displacement
- **Effect**: Idle stability

#### VVT (Variable Valve Timing)
- **Purpose**: Cam phasing control
- **Effect**: Power band, emissions, fuel economy
- **Tables**: Intake/exhaust cam advance vs RPM/Load

## Transmission Tables (6L80/6L90)

### Shift

#### Normal Shift Speeds
- **Axis**: MPH or RPM
- **Gear**: 1→2, 2→3, etc.
- **TPS**: Different maps for throttle position
- **Safe**: +200-400 RPM for performance

#### Performance Shift Speeds
- **Use**: In manual mode or sport
- **Higher**: Shift later for power
- **Limit**: Stay below redline

#### Quick Shift
- **Purpose**: Reduce shift time
- **Effect**: Firmer feel, more power to wheels
- **Tradeoff**: NVH (noise/vibration/harshness)

### Torque Management

#### Engine Torque Model
- **Purpose**: Predicts engine torque output
- **Tables**: Torque vs RPM/Throttle
- **Critical**: Must be accurate for trans life

#### Shift Torque Reduction
- **Purpose**: Reduce torque during shifts
- **Method**: Spark retard, fuel cut, throttle
- **Amount**: 0-100% torque
- **Safe**: Keep trans input torque < rating

#### TCC (Torque Converter Clutch)

##### Apply Schedule
- **RPM**: When to lock converter
- **Gear**: Which gears allow lockup
- **TPS**: Throttle position thresholds

##### Release Schedule
- **Conditions**: Downshift, low RPM, high load
- **Hysteresis**: Prevent hunting

### Line Pressure

#### Base Pressure
- **Normal**: 85-90 PSI
- **Performance**: 100-120 PSI
- **Too Low**: Slipping, burnt clutches
- **Too High**: Harsh shifts, pump wear

#### Adaptive Pressure
- **Purpose**: Learn clutch fill times
- **Reset**: After transmission work
- **Monitor**: Shift time adaptive counts

## Speed Density (VE)

### Volumetric Efficiency
- **Purpose**: Calculate airflow without MAF
- **Format**: VE % vs RPM/MAP
- **Use**: MAFless tuning or backup
- **Calculation**: Requires displacement, IAT, MAP

### Dynamic Airflow
- **Purpose**: Real-time airflow calculation
- **Tables**: Cylinder airmass vs RPM
- **Critical**: All fuel/spark references this

## Safety & Limits

### Rev Limiter
- **Fuel Cut**: Hard limit
- **Soft Cut**: Spark retard before fuel cut
- **Set**: 200-400 RPM below mechanical limit

### Speed Limiter
- **Purpose**: Top speed restriction
- **Remove**: Set to 255 or max
- **Legal**: Check local laws

### Engine Temp
- **Fan Control**: Coolant temp thresholds
- **Fuel Enrichment**: Cold start, warm-up
- **Spark Retard**: Very high temp protection

### Torque Limits
- **Purpose**: Cap output torque
- **Use**: Driveline protection
- **Tables**: By gear, by mode

## Common Tuning Scenarios

### Cold Air Intake
1. **MAF**: Scale +8-12% for increased flow
2. **Spark**: +2° timing for cooler IAT
3. **PE**: May need slight enrichment

### Headers
1. **MAF**: Verify with wideband
2. **Spark**: Can advance 2-4° (less heat in manifolds)
3. **Fuel**: Often runs leaner - monitor trims

### Cam Swap
1. **Idle Air**: +20-50% for overlap
2. **MAF**: New VE curve
3. **Spark**: Re-map for new dynamics
4. **VVT**: Optimize if variable cam

### Turbo/Supercharger
1. **MAF**: Rescale for positive pressure
2. **Spark**: Retard under boost (0.5°/psi typical)
3. **Fuel**: Rich under boost (11.0-11.5:1)
4. **Torque Limits**: Set to hardware rating
5. **Boost Cut**: Safety limit

### Flex Fuel (E85)
1. **Fuel**: +30% mass for ethanol energy density
2. **Spark**: Can advance 4-6° (higher octane)
3. **Cranking**: Enrich 50%+
4. **Compensation**: Enable flex fuel sensor

## HP Tuners Editor Navigation

### Main Menu
1. **Engine** → Fuel, Spark, Airflow
2. **Transmission** → Shift, TCC, Torque
3. **System** → Limits, Fans, Speedo
4. **Fueling** → Injectors, PE, trims

### Table View
- **Axis**: Click to edit breakpoints
- **Data**: Tab through cells
- **Graph**: Right-click → Graph vs RPM
- **Compare**: Open multiple calibrations

### Special Functions
- **Read**: Vehicle → Read entire ECU
- **Write**: Write calibration only
- **Write Entire**: OS + calibration (rare)
- **Save**: .tun file format

### Logging
1. **VCM Scanner**: Data logging tool
2. **PIDs**: Select parameters to log
3. **Triggers**: Start/stop conditions
4. **Export**: CSV for analysis

## PID List for Logging

### Essential
- Engine RPM (PID 0C)
- Vehicle Speed (PID 0D)
- Calculated Load (PID 04)
- Throttle Position (PID 11)
- MAF Rate (PID 10)
- Spark Advance (PID 0E)
- O2 Sensor (PID 14, 15)
- Short Fuel Trim (PID 06, 08)
- Long Fuel Trim (PID 07, 09)
- Coolant Temp (PID 05)
- Intake Temp (PID 0F)

### Performance
- Knock Retard (Mode 22)
- Fuel Pressure (if equipped)
- Oil Temp (Mode 22)
- Trans Temp (Mode 22)
- Boost Pressure (turbos)

### Transmission
- Trans Slip (calculated)
- Gear Command
- TCC State
- Line Pressure
- Shift Time

## Tips

1. **Log Before Change**: Always have baseline
2. **One Change at a Time**: Isolate effects
3. **Verify with Wideband**: Don't trust only narrowband
4. **Monitor IAT**: Hot air causes knock
5. **Check Fuel Trims**: ±5% is good, ±10% needs tuning
6. **Save Iterations**: Keep version history
7. **Test Drive**: Highway, city, WOT, part throttle
8. **Cold Start**: Don't ignore drivability
9. **Transmission Health**: Keep shift times < 0.3s
10. **Documentation**: Note every change