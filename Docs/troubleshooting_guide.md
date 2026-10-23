# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Grant Aerona3 integration.

## Quick Diagnosis

### Integration Status Check
1. **Go to**: Settings → Devices & Services → Grant Aerona3
2. **Check status**: Should show "Connected" or number of entities
3. **Check entities**: Click device to see entity list

### Common Symptoms
| Symptom | Quick Check | Likely Cause |
|---------|-------------|--------------|
| No entities created | Integration installed? | Installation issue |
| All entities "Unavailable" | Can ping heat pump? | Network/connection issue |
| Some entities missing | Check heat pump model | Model differences |
| Wrong values displayed | Check units/scaling | Configuration issue |
| COP seems wrong | Flow rate configured? | Missing flow rate |

## Installation Issues

### Integration Not Found

**Symptoms**: "Grant Aerona3" doesn't appear in Add Integration

**Solutions**:
1. ✅ **Restart Home Assistant** after copying files
2. ✅ **Check file structure**:
   ```
   /config/custom_components/grant_aerona3/
   ├── __init__.py
   ├── manifest.json
   └── [other files]
   ```
3. ✅ **Check file permissions** (Linux: `chmod 644 *`)
4. ✅ **Clear browser cache** and refresh
5. ✅ **Check logs** for Python import errors

### Integration Setup Fails

**Symptoms**: Error during configuration flow

**Error**: `"Cannot connect to device"`

**Solutions**:
1. ✅ **Check all cables**:
2. ✅ **Verify IP address**: Ping heat pump from Home Assistant host
   ```bash
   ping 192.168.1.100
   ```
3. ✅ **Verify Modbus enabled**: Check heat pump network settings
4. ✅ **Try different slave ID**: Try 1, 2, or 3
5. ✅ **Check firewall**: Ensure port 502 is open
6. ✅ **Network segmentation**: Ensure same subnet or routing configured

**Error**: `"Invalid configuration"`

**Solutions**:
1. ✅ **Check IP format**: Must be valid IPv4 (e.g., 192.168.1.100)
2. ✅ **Port range**: Must be 1-65535
3. ✅ **Slave ID range**: Must be 1-247
4. ✅ **Scan interval**: Must be 10-300 seconds

## Connection Issues

### All Entities Unavailable

**Symptoms**: Entities show "Unavailable" or "Unknown"

**Diagnosis Steps**:

1. **Check network connectivity**:
   ```bash
   ping [heat_pump_ip]
   nmap -p 502 [heat_pump_ip]
   ```

2. **Check Home Assistant logs**:
   - Settings → System → Logs
   - Search for "grant_aerona3" or "modbus"

3. **Test Modbus connection**:
   - Use Modbus testing tool (e.g., QModMaster)
   - Try reading register 0 with slave ID 1

**Common Solutions**:

| Error in Logs | Solution |
|---------------|----------|
| `Connection timed out` | Check network, firewall, IP address |
| `Connection refused` | Verify Modbus TCP enabled on heat pump |
| `Modbus Error: [Input/Output] 1` | Wrong slave ID - try 1, 2, or 3 |
| `Modbus Error: [Input/Output] 2` | Invalid register address |
| `Modbus Error: [Input/Output] 3` | Register not supported on this model |

### Intermittent Connection

**Symptoms**: Entities go unavailable periodically

**Causes & Solutions**:

1. **Network instability**:
   - Check WiFi signal strength
   - Test with Ethernet connection
   - Check for network congestion

2. **Scan interval too fast**:
   - Increase from 30s to 60s
   - Heat pump may rate-limit connections

3. **Modbus queue overflow**:
   - Reduce number of enabled entities
   - Increase scan interval

4. **Heat pump busy**:
   - Some operations block Modbus access
   - Normal during defrost cycles

### Partial Entity Availability

**Symptoms**: Some entities work, others don't

**Causes**:

1. **Model differences**: Different Grant Aerona3 models support different registers
2. **Firmware version**: Newer/older firmware may have different register maps
3. **Configuration dependent**: Some registers only available when features enabled

**Solutions**:
1. ✅ **Check entity attributes** for register addresses
2. ✅ **Compare with manual** for your specific model
3. ✅ **Disable problematic entities** if not needed
4. ✅ **Check heat pump configuration** for relevant features

### Dashboard Card Shows "Entity Not Available" After Updating

**Symptoms**: A dashboard card, automation, or template that used to work now shows a greyed-out/unavailable entity after updating the integration (v1.2.0+), for a setpoint such as DHW comfort temperature, a flow temperature curve point, or similar.

**Cause**: As of v1.2.0, every *writable* holding register (setpoints you can change) no longer has a separate read-only `sensor.*` entity — only the `number.*` entity remains, since it already showed the same value and the sensor was a pure duplicate. If something referenced `sensor.dhw_comfort_set_temperature` (for example), that entity no longer exists.

**Solutions**:
1. ✅ **Find the broken reference**: Settings → Automations & Scenes, or edit the dashboard card in YAML mode, and look for `sensor.*` entity IDs tied to a setpoint rather than a live reading.
2. ✅ **Switch it to the matching `number.*` entity** — go to Settings → Devices & Services → Grant Aerona3 → Entities, search for the setting by name, and copy the `number.` entity ID shown there (the exact slug can vary slightly by Home Assistant version, so copy it rather than guessing).
3. ✅ **Dashboard cards that need a read-only display** (e.g. a stat card) still work fine pointing at a `number.*` entity — it just also lets you edit the value from that card, which for most setpoint cards is the more useful behaviour anyway.
4. This only affects registers that were *writable* (setpoints). Read-only diagnostic registers (e.g. temperature readings, error codes) kept their `sensor.*` entity unchanged.

## Data Issues

### Wrong Temperature Values

**Symptoms**: Temperatures showing incorrect values

**Common Issues**:

| Display | Expected | Issue | Solution |
|---------|----------|-------|----------|
| 235°C | 23.5°C | Scaling x10 | Check const.py scaling factors |
| 2.35°C | 23.5°C | Scaling ÷10 | Verify register configuration |
| -40°C | 20°C | Signed/unsigned | Check raw value processing |

**Diagnosis**:
1. ✅ **Check raw values** in entity attributes
2. ✅ **Verify scaling factors** in const.py
3. ✅ **Compare with heat pump display**
4. ✅ **Check register documentation**

### COP Calculation Issues

**Symptoms**: COP values seem unrealistic

| COP Reading | Likely Issue | Solution |
|-------------|--------------|----------|
| > 8.0 | Flow rate too high | Reduce flow rate setting |
| < 1.5 | Flow rate too low or power measurement issue | Increase flow rate or check power sensor |
| Negative | Temperature sensor issue | Check flow/return temperature sensors |
| Fluctuating wildly | Unstable readings | Increase scan interval, check during steady state |

**Diagnosis Steps**:
1. ✅ **Check flow rate configuration**: Should be 15-30 L/min typically
2. ✅ **Verify temperature difference**: Should be 3-8°C typically
3. ✅ **Check power consumption**: Should match heat pump specifications
4. ✅ **Test during steady state**: Avoid readings during startup/defrost

### Power Consumption Issues

**Symptoms**: Power readings incorrect

**Common Issues**:
- **Reading in watts vs kilowatts**: Check scaling factor
- **Including/excluding backup heater**: May affect total power
- **Measurement point**: Some models measure compressor only vs total

**Solutions**:
1. ✅ **Compare with electricity meter** over time
2. ✅ **Check during known load conditions**
3. ✅ **Verify register documentation** for what's included
4. ✅ **Account for auxiliary loads** (pumps, fans, controls)

## Performance Issues

### Slow Response Times

**Symptoms**: Long delays updating entity values

**Causes & Solutions**:

1. **Scan interval too long**:
   - Decrease from 60s to 30s
   - Balance responsiveness vs load

2. **Network latency**:
   - Check ping times to heat pump
   - Consider network optimization

3. **Modbus queue backup**:
   - Too many simultaneous requests
   - Stagger requests or reduce entities

### High CPU/Network Usage

**Symptoms**: Home Assistant performance impact

**Solutions**:

1. **Increase scan interval**: 30s → 60s → 120s
2. **Disable unused entities**: Focus on essential monitoring
3. **Check for excessive automation triggers**: Avoid triggering on every update
4. **Monitor system resources**: Check HA system info

### Memory Issues

**Symptoms**: Integration consuming excessive memory

**Rare but possible causes**:
1. **Data accumulation**: Energy sensor accumulating without reset
2. **Log accumulation**: Excessive debug logging enabled
3. **Memory leak**: Report as bug if confirmed

## Heat Pump Specific Issues

### Modbus Not Responding

**Symptoms**: Integration worked before, now fails

**Heat pump side checks**:

1. **Restart heat pump**: Power cycle or controller reset
2. **Check network settings**: IP may have changed (DHCP)
3. **Verify Modbus still enabled**: Settings may have reset
4. **Check for firmware updates**: May affect Modbus behavior

### Different Model Behavior

**Grant Aerona3 model variations**:

| Model | Common Differences |
|-------|-------------------|
| **6kW** | Fewer sensors, simplified controls |
| **8kW** | Standard sensor set |
| **12kW** | Additional performance sensors |
| **16kW** | Advanced monitoring, dual circuits |

**Solutions**:
1. ✅ **Disable unsupported entities**
2. ✅ **Check model-specific documentation**
3. ✅ **Report missing registers** for your model

### Firmware Compatibility

**Symptoms**: Integration worked, stopped after heat pump service

**Possible causes**:
1. **Firmware update**: New firmware may change register addresses
2. **Configuration reset**: Service may have reset Modbus settings
3. **Hardware replacement**: Controller replacement

## Getting Help

### Before Reporting Issues

Collect this information:

#### System Information
- **Home Assistant version**: Settings → About
- **Integration version**: Check GitHub releases
- **Grant Aerona3 model**: Check heat pump label
- **Firmware version**: Check heat pump display

#### Network Information
- **Heat pump IP address**: From integration config
- **Network setup**: Same subnet? VLANs? WiFi/Ethernet?
- **Ping results**: Can HA reach heat pump?

#### Configuration Details
- **Scan interval**: Current setting
- **Slave ID**: Current setting
- **Enabled entities**: How many working/failing?

#### Error Details
- **Specific error messages**: From logs
- **When issue started**: After what change?
- **Affected entities**: All or specific ones?

### Log Collection

#### Enable Debug Logging
Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.grant_aerona3: debug
    pymodbus: debug
```

#### View Logs
1. Settings → System → Logs
2. Filter for "grant_aerona3"
3. Copy relevant error messages

### Diagnostic Data

#### Entity State Information
For problematic entities, provide:
- Entity ID
- Current state
- Attributes (especially raw_value)
- Expected vs actual values

#### Network Diagnostic
```bash
# Test basic connectivity
ping [heat_pump_ip]

# Test Modbus port
nmap -p 502 [heat_pump_ip]

# Test from HA container (if using Docker)
docker exec homeassistant ping [heat_pump_ip]
```

### Where to Get Help

1. **📖 Documentation**: Check all docs first
2. **🔍 Search Issues**: [GitHub Issues](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/issues)
3. **🆕 New Issue**: Create detailed issue report
4. **💬 Discussions**: [GitHub Discussions](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/discussions)
5. **🏠 Community**: Home Assistant Community Forum

### Issue Templates

#### Bug Report Template
```
**Describe the bug**
Brief description of what's wrong

**System Information**
- Home Assistant version: 
- Integration version: 
- Grant Aerona3 model: 
- Heat pump firmware: 

**Configuration**
- Host: [IP address]
- Port: [port]
- Slave ID: [ID]
- Scan interval: [seconds]

**Expected behavior**
What should happen

**Actual behavior**
What actually happens

**Logs**
```
[paste relevant log entries]
```

**Additional context**
Any other relevant information
```

#### Feature Request Template
```
**Feature Description**
Clear description of requested feature

**Use Case**
Why this feature would be useful

**Proposed Solution**
How you think it should work

**Additional Context**
Any other relevant information
```

---

**Still having issues?** Don't hesitate to ask for help - the community is here to support you!