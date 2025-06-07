# Flow Rate Measurement Guide

Accurate flow rate measurement is crucial for precise COP (Coefficient of Performance) calculations. This guide explains why flow rate matters and how to measure and configure it.

## Why Flow Rate Matters

The **Coefficient of Performance (COP)** measures how efficiently your heat pump converts electricity into heat:

```
COP = Heat Output ÷ Electrical Input
```

To calculate heat output accurately, we need:
- **Flow Rate** (L/min): How much water flows through the system
- **Temperature Difference** (°C): Between flow and return temperatures
- **Specific Heat of Water**: 4.18 kJ/kg·K (constant)

**Without flow rate**: COP calculation is just an estimate
**With flow rate**: COP calculation is thermodynamically accurate

## Typical Grant Aerona3 Flow Rates

| Heat Pump Model | Typical Flow Rate | Range |
|----------------|-------------------|-------|
| **Aerona3 6kW** | 16 L/min | 15-18 L/min |
| **Aerona3 8kW** | 20 L/min | 18-22 L/min |
| **Aerona3 12kW** | 22 L/min | 20-25 L/min |
| **Aerona3 16kW** | 27 L/min | 25-30 L/min |

*Note: Actual flow rates depend on system design, pump settings, and resistance*

## Method 1: Temporary Flow Meter (Most Accurate)

### Equipment Needed
- **Ultrasonic flow meter** (rental ~£50/day)
- **Clamp-on flow meter** (purchase ~£200-500)
- **Inline flow meter** (requires plumbing, ~£100-300)

### Steps
1. **Identify measurement point**: 
   - Primary flow pipe (22mm or 28mm copper)
   - Between heat pump and first split/valve
   - Straight pipe section (no bends within 10 pipe diameters)

2. **Install/attach flow meter**:
   - **Ultrasonic**: Clamp sensors on pipe exterior
   - **Inline**: Install in line (requires plumbing)
   - **Clamp-on**: Attach around pipe

3. **Take measurements**:
   - Run heat pump in normal heating mode
   - Wait for steady state (10-15 minutes)
   - Record flow rate over 10 minutes
   - Take readings at different outdoor temperatures if possible

4. **Calculate average**:
   - Average the readings
   - This is your system flow rate

### Professional Measurement
Many heating engineers have ultrasonic flow meters and can measure this during a service visit.

## Method 2: Pump Curve Calculation

If you know your system pump model and settings, you can estimate flow rate from pump curves.

### Steps
1. **Identify your pump**:
   - Check pump nameplate
   - Note speed setting (1, 2, 3 or %)
   - Record pump model number

2. **Find pump curve data**:
   - Download pump manual/datasheet
   - Find performance curve for your speed setting

3. **Estimate system resistance**:
   - Typical Grant Aerona3 systems: 15-25 kPa at design flow
   - Include: pipe runs, radiators/UFH, heat exchanger

4. **Read flow rate from curve**:
   - Find intersection of pressure and flow
   - This gives approximate flow rate

### Common Grant Aerona3 Pumps
- **Grundfos UPS 25-60**: 20-25 L/min at speed 2
- **Grundfos Alpha2 25-60**: 18-23 L/min at medium setting
- **Wilo Yonos Para**: 19-24 L/min at typical settings

## Method 3: Energy Balance Calculation

This method uses known heating output to back-calculate flow rate.

### Requirements
- Known heating output (kW) - from heat pump display or manual
- Measured flow and return temperatures
- Steady-state operation

### Formula
```
Flow Rate (L/min) = (Heating Output × 60) ÷ (4.18 × Temperature Difference)
```

### Example
- Heating output: 8 kW
- Flow temperature: 35°C
- Return temperature: 30°C
- Temperature difference: 5°C

```
Flow Rate = (8 × 60) ÷ (4.18 × 5) = 480 ÷ 20.9 = 23 L/min
```

## Method 4: Manufacturer Specifications

Check your Grant Aerona3 installation manual for design flow rates.

### Typical Design Values
- **Heating only systems**: 15-20 L/min
- **Heating + DHW systems**: 18-25 L/min
- **Large systems (>12kW)**: 22-30 L/min

*Note: Actual flow may differ from design values*

## Configuring Flow Rate in Home Assistant

Once you've measured your flow rate:

### Step 1: Find the Entity
1. Go to **Settings** → **Devices & Services**
2. Find **Grant Aerona3 Heat Pump**
3. Look for **"Grant Aerona3 Flow Rate"** number entity

### Step 2: Set the Value
1. Click on the entity
2. Enter your measured flow rate
3. Units are in **L/min** (litres per minute)
4. Range: 10-50 L/min, step 0.5

### Step 3: Verify COP Calculation
1. Check the **"Grant Aerona3 COP"** sensor
2. In attributes, you should see:
   - `calculation_method: "accurate_with_flow_rate"`
   - `flow_rate_used: "XX.X L/min"`
   - `formula: "COP = (Flow Rate × Specific Heat × ΔT) / Electrical Power"`

## Validating Your Flow Rate

### Check COP Values
With correct flow rate, your COP should be:
- **Winter (outdoor 0°C)**: 2.5 - 3.5
- **Spring/Autumn (outdoor 10°C)**: 3.0 - 4.5
- **Mild weather (outdoor 15°C)**: 4.0 - 6.0

### Red Flags
If your COP calculations show:
- **COP > 8**: Flow rate probably too high
- **COP < 2**: Flow rate probably too low
- **Erratic readings**: Check temperature sensors

### Cross-Reference with Bills
Compare calculated energy consumption with actual electricity bills to validate accuracy.

## Flow Rate Automation

You can create automations to adjust flow rate seasonally or based on system changes:

```yaml
# Example: Seasonal flow rate adjustment
automation:
  - alias: "Adjust flow rate for winter"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature
        below: 5
    action:
      - service: number.set_value
        target:
          entity_id: number.grant_aerona3_flow_rate
        data:
          value: 22  # Winter flow rate
```

## Troubleshooting Flow Rate Issues

### Flow Rate Seems Wrong
- ✅ Check pump speed settings
- ✅ Verify no air in system
- ✅ Check for partially closed valves
- ✅ Confirm measurement location
- ✅ Compare with system design

### COP Still Inaccurate
- ✅ Verify temperature sensors are working
- ✅ Check power measurement accuracy
- ✅ Ensure steady-state operation during measurement
- ✅ Confirm no simultaneous DHW heating

### Professional Help
Consider hiring a heating engineer with flow measurement equipment for the most accurate results.

## Summary

1. **Measure flow rate** using temporary flow meter (most accurate)
2. **Set the value** in Home Assistant number entity
3. **Verify COP calculation** switches to accurate method
4. **Monitor COP values** for realistic results
5. **Validate with energy bills** over time

Accurate flow rate measurement transforms your COP readings from estimates to precise efficiency measurements, helping you optimize your heat pump performance and track energy savings.

---

**Need help?** See [Troubleshooting Guide](troubleshooting.md) or ask on [GitHub Issues](https://github.com/yourusername/grant-aerona3-hass/issues).