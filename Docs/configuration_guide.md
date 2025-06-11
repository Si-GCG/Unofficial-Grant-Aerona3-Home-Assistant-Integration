# Configuration Guide

This guide covers all configuration options and entity management for the Grant Aerona3 integration.

## Initial Configuration

The integration uses a simple configuration flow with just the essentials:

| Setting | Default | Description | Notes |
|---------|---------|-------------|--------|
| **Host** | *required* | IP address of heat pump | e.g., `192.168.1.100` |
| **Port** | `502` | Modbus TCP port | Usually 502 for Grant Aerona3 |
| **Slave ID** | `1` | Modbus device identifier | Usually 1, try 2 or 3 if needed |
| **Scan Interval** | `30` | Polling frequency (seconds) | 30s recommended, 10-300s range |

### Scan Interval Guidelines

| Interval | Use Case | Pros | Cons |
|----------|----------|------|------|
| **10-15s** | Monitoring critical systems | Real-time data | Higher network/CPU load |
| **30s** | Normal monitoring | Good balance | *Recommended* |
| **60s** | Basic monitoring | Lower system load | Less responsive |
| **120s+** | Background monitoring | Minimal impact | Slow updates |

## Entity Overview

The integration automatically creates **150+ entities** across multiple platforms:

### Platform Summary
- **🌡️ Sensors**: 50+ temperature, power, status sensors
- **🔘 Binary Sensors**: 30+ on/off status indicators  
- **🔄 Switches**: 20+ configuration toggles
- **🔢 Numbers**: 95+ setpoint controls
- **🏠 Climate**: 1-2 zone controls

## Sensor Entities

### Temperature Sensors
| Entity | Description | Typical Range | Units |
|--------|-------------|---------------|-------|
| `sensor.return_water_temperature` | Water returning to heat pump | 25-45°C | °C |
| `sensor.outgoing_water_temperature` | Water leaving heat pump | 30-55°C | °C |
| `sensor.outdoor_air_temperature` | Outside air temperature | -20 to 35°C | °C |
| `sensor.dhw_tank_temperature` | Hot water cylinder temp | 40-70°C | °C |
| `sensor.discharge_temperature` | Compressor discharge | 40-80°C | °C |
| `sensor.suction_temperature` | Compressor suction | -10 to 20°C | °C |
| `sensor.defrost_temperature` | Defrost sensor | -20 to 20°C | °C |

### Performance Sensors
| Entity | Description | Typical Range | Units |
|--------|-------------|---------------|-------|
| `sensor.power_consumption` | Electrical power input | 1-8 kW | W |
| `sensor.cop` | Coefficient of Performance | 2.0-6.0 | - |
| `sensor.system_efficiency` | Overall efficiency | 50-85% | % |
| `sensor.energy_consumption` | Cumulative energy | Increasing | kWh |

### System Status Sensors
| Entity | Description | Values |
|--------|-------------|--------|
| `sensor.selected_operating_mode` | Current operation mode | Off, Heating, Cooling |
| `sensor.compressor_operating_frequency` | Compressor speed | 0-120 Hz |
| `sensor.fan_control_number_of_rotation` | Fan speed | 0-1500 RPM |
| `sensor.water_pump_control_number_of_rotation` | Pump speed | 0-2500 RPM |

## Binary Sensor Entities

### System Status
| Entity | Description |
|--------|-------------|
| `binary_sensor.system_status` | Overall system running state |
| `binary_sensor.defrost_mode` | Defrost cycle active |
| `binary_sensor.error_status` | Any errors present |

### Configuration Status
| Entity | Description |
|--------|-------------|
| `binary_sensor.heating_weather_compensation_zone_1` | Zone 1 weather compensation |
| `binary_sensor.anti_legionella_function` | Anti-legionella cycle |
| `binary_sensor.frost_protection_based_on_outdoor_temperature` | Frost protection active |

## Switch Entities

### Weather Compensation Controls
| Entity | Description | Impact |
|--------|-------------|--------|
| `switch.heating_weather_compensation_zone_1` | Zone 1 weather compensation | 10-15% energy savings |
| `switch.heating_weather_compensation_zone_2` | Zone 2 weather compensation | Zone-specific savings |
| `switch.cooling_weather_compensation_zone_1` | Zone 1 cooling compensation | Summer efficiency |

### Safety & Protection
| Entity | Description | Recommendation |
|--------|-------------|----------------|
| `switch.frost_protection_based_on_outdoor_temperature` | Outdoor frost protection | ✅ Keep enabled |
| `switch.frost_protection_based_on_room_temperature` | Indoor frost protection | ✅ Keep enabled |
| `switch.anti_legionella_function` | DHW legionella protection | ✅ Keep enabled (if DHW) |

### Terminal Configuration
| Entity | Description | When to Enable |
|--------|-------------|----------------|
| `switch.terminal_7_8_dhw_tank_temperature_probe` | DHW temperature sensor | If you have thermistor on your hot water cylinder |
| `switch.terminal_11_12_buffer_tank_temperature_probe` | Buffer tank sensor | If you have buffer tank and have a Thermistor on the buffer tank |
| `switch.terminal_26_27_flow_switch` | Flow switch monitoring | ✅ Usually enabled |

![PCB Diagram](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/blob/main/Docs/images/PCB_Diag.jpeg)

## Number Entities

### Zone 1 Temperature Controls
| Entity | Description | Typical Range | Units |
|--------|-------------|---------------|-------|
| `number.fixed_flow_temp_zone_1` | Fixed flow temperature | 25-45°C | °C |
| `number.max_flow_temp_zone1` | Maximum flow temp | 35-60°C | °C |
| `number.min_flow_temp_zone1` | Minimum flow temp | 20-35°C | °C |

### DHW (Hot Water) Controls
| Entity | Description | Typical Range | Notes |
|--------|-------------|---------------|-------|
| `number.dhw_comfort_set_temperature` | Comfort mode temperature | 45-65°C | Daily use |
| `number.dhw_economy_set_temperature` | Economy mode temperature | 40-55°C | Energy saving |
| `number.anti_legionella_set_point` | Legionella protection temp | 60-70°C | Weekly cycle |

### Weather Compensation Settings
| Entity | Description | Typical Range | Purpose |
|--------|-------------|---------------|---------|
| `number.min_outdoor_air_temperature_zone1` | Design outdoor temp (cold) | -5 to 5°C | Curve bottom |
| `number.max_outdoor_air_temperature_zone1` | Design outdoor temp (mild) | 15-20°C | Curve top |

### Flow Rate Configuration
| Entity | Description | Range | Notes |
|--------|-------------|-------|-------|
| `number.flow_rate` | System flow rate | 10-50 L/min | **Important for accurate COP** |

## Climate Entities

### Zone Controls
| Entity | Description | Features |
|--------|-------------|----------|
| `climate.zone_1` | Main heating zone | Temperature control, mode switching |
| `climate.zone_2` | Secondary zone | Available if Zone 2 configured |

#### Climate Features
- **Temperature Control**: Set target flow temperature
- **HVAC Modes**: Off, Heat, Cool, Auto
- **Current Temperature**: Shows return water temperature
- **Attributes**: Flow temp, outdoor temp, compressor frequency

## Entity Configuration

### Enabling/Disabling Entities

Entities are automatically created based on available data. To manage them:

1. **Hide unused entities**:
   ```
   Settings → Devices & Services → Grant Aerona3 → [Entity] → Settings → Disabled
   ```

2. **Customize entity names**:
   ```
   Settings → Devices & Services → Grant Aerona3 → [Entity] → Settings → Name
   ```

3. **Set entity categories**:
   - **Config**: Configuration entities (already set)
   - **Diagnostic**: Diagnostic/troubleshooting entities
   - **None**: Primary entities shown in main UI

### Recommended Entity Customizations

#### High Priority (Dashboard)
- `sensor.cop` - Main efficiency metric
- `sensor.power_consumption` - Current power usage
- `sensor.outdoor_air_temperature` - Weather reference
- `sensor.outgoing_water_temperature` - Flow temperature
- `climate.zone_1` - Zone control

#### Medium Priority (Monitoring)
- `binary_sensor.system_status` - Running state
- `binary_sensor.defrost_mode` - Defrost indicator
- `sensor.compressor_operating_frequency` - System load
- `sensor.dhw_tank_temperature` - Hot water status

#### Low Priority (Diagnostic)
- Most holding register sensors (setpoint displays)
- Terminal configuration binary sensors
- Advanced timing and control numbers

## Advanced Configuration

### Weather Compensation Setup

Weather compensation automatically adjusts flow temperature based on outdoor conditions for optimal efficiency.

#### Zone 1 Configuration
1. **Enable weather compensation**:
   ```
   switch.heating_weather_compensation_zone_1: ON
   ```

2. **Set curve parameters**:
   - `number.min_outdoor_air_temperature_zone1`: `-5°C` (coldest design day)
   - `number.max_outdoor_air_temperature_zone1`: `18°C` (mild weather cutoff)
   - `number.max_flow_temp_zone1`: `45°C` (coldest day flow temp)
   - `number.min_flow_temp_zone1`: `25°C` (mild day flow temp)

#### Example Weather Compensation Curve
```
Outdoor Temp → Flow Temp
-5°C       → 45°C  (Maximum heating)
 0°C       → 40°C
 5°C       → 35°C
10°C       → 30°C
15°C       → 27°C
18°C       → 25°C  (Minimum heating)
```

### DHW (Hot Water) Configuration

If you have a hot water cylinder:

#### Enable DHW Components
1. **Enable DHW temperature probe**:
   ```
   switch.terminal_7_8_dhw_tank_temperature_probe: ON
   ```

2. **Configure temperatures**:
   - `number.dhw_comfort_set_temperature`: `50°C`
   - `number.dhw_economy_set_temperature`: `45°C`
   - `number.anti_legionella_set_point`: `65°C`

3. **Set DHW priority**:
   - `number.dhw_production_priority_setting`: 
     - `1` = DHW priority over heating
     - `2` = Heating priority over DHW

#### DHW Scheduling Example
```yaml
# Morning boost
automation:
  - alias: "DHW Morning Boost"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.dhw_comfort_set_temperature
        data:
          value: 55
```

### Dual Zone Configuration

For systems with two heating zones or those wishing to set a dual set point:

#### Enable Zone 2
1. **Enable weather compensation**:
   ```
   switch.heating_weather_compensation_zone_2: ON
   ```

2. **Configure Zone 2 curve** (typically 5°C lower than Zone 1):
   - `number.max_flow_temp_zone2`: `40°C`
   - `number.min_flow_temp_zone2`: `20°C`

3. **Enable Zone 2 pump**:
   ```
   switch.terminal_49_pump2: ON
   ```

### Frost Protection Configuration

Essential for system protection:

#### Outdoor Frost Protection
```
switch.frost_protection_based_on_outdoor_temperature: ON
number.start_temperature_of_frost_protection_on_outdoor_air_temp: 2°C
number.hysteresis_of_outdoor_air_temperature: 2°C
```

#### Water System Frost Protection
```
switch.frost_protection_based_on_flow_temp: ON
number.water_temperature_of_frost_protection: 35°C
```

## Performance Optimization

### Efficiency Settings

#### Optimal Weather Compensation
- **Enable** for both heating and cooling
- **Set appropriate curves** for your heat emitters:
  - **Radiators**: Higher temperatures (35-45°C max)
  - **Underfloor heating**: Lower temperatures (25-35°C max)

#### Night Mode Setup
```
switch.terminal_28_29_night_mode: ON
number.max_frequency_of_night_mode: 60  # Hz (reduced for quiet operation)
```

#### Pump Optimization
```
number.type_of_configuration_of_main_water_pump: 1  # Temperature based
```

### Monitoring Setup

#### Essential Automations
1. **High power alert**:
```yaml
automation:
  - alias: "Heat pump high power consumption"
    trigger:
      - platform: numeric_state
        entity_id: sensor.power_consumption
        above: 6000  # Watts
        for: "00:10:00"
    action:
      - service: notify.mobile_app
        data:
          message: "Heat pump power consumption high: {{ states('sensor.power_consumption') }}W"
```

2. **Low COP warning**:
```yaml
automation:
  - alias: "Heat pump low efficiency"
    trigger:
      - platform: numeric_state
        entity_id: sensor.cop
        below: 2.0
        for: "00:30:00"
    action:
      - service: notify.mobile_app
        data:
          message: "Heat pump COP low: {{ states('sensor.cop') }}"
```

#### Energy Monitoring Dashboard
Add these entities to your energy dashboard:
- `sensor.power_consumption` (Power)
- `sensor.energy_consumption` (Energy)

## Entity State Management

### Entity States and Troubleshooting

#### Common Entity States
- **Available**: Entity working normally
- **Unavailable**: Communication lost with heat pump
- **Unknown**: Entity exists but no data received yet

#### Troubleshooting Unavailable Entities
1. **Check network connectivity**
2. **Verify Modbus slave ID**
3. **Check scan interval** (may be too fast)
4. **Review logs** for Modbus errors

### Entity Restoration

Entities automatically restore their last known values after Home Assistant restart. Number entities (setpoints) maintain their configured values.

## Integration Options

The integration can be reconfigured after setup:

1. **Go to**: Settings → Devices & Services → Grant Aerona3
2. **Click**: Configure
3. **Modify**: Connection settings
4. **Test**: New configuration

### Reconfiguration Options
- Change scan interval for performance tuning
- Update IP address if heat pump network changes
- Modify port/slave ID for troubleshooting

## Best Practices

### Scan Interval Selection
- **Start with 30 seconds** - good balance
- **Increase to 60 seconds** if experiencing network issues
- **Decrease to 15 seconds** only for critical monitoring
- **Monitor Home Assistant performance** - don't overload

### Entity Organization
1. **Create areas** for different zones
2. **Use entity categories** to organize UI
3. **Hide diagnostic entities** from main dashboard
4. **Group related entities** in dashboard cards

### Backup Configuration
Important settings to backup:
- Flow rate configuration
- Weather compensation curves
- DHW temperature setpoints
- Safety protection settings

## Troubleshooting Configuration

### Common Issues

#### Entities Not Updating
- Check scan interval (not too fast/slow)
- Verify network stability
- Check Home Assistant logs for Modbus errors

#### Incorrect Values
- Verify scaling is correct (should be automatic)
- Check register addresses match heat pump model
- Confirm Modbus slave ID

#### Performance Issues
- Increase scan interval
- Reduce number of enabled entities
- Check network latency to heat pump

### Getting Help

When reporting configuration issues, include:
- Home Assistant version
- Grant Aerona3 model and firmware
- Integration version
- Specific entities having issues
- Log entries with errors
- Network configuration details

---

**Next Steps:**
- [Set up flow rate measurement](flow_rate_guide.md)
- [Review troubleshooting guide](troubleshooting_guide.md)
- [Explore automation examples](../Examples/examples_automation.yaml)
- [Explore dashboard examples](../Examples/examples_lovelace.yaml)
