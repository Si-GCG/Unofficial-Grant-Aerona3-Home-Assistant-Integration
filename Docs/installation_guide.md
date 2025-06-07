# Installation Guide

This guide will walk you through installing the Grant Aerona3 Heat Pump integration for Home Assistant.

## Prerequisites

Before installing, ensure you have:

- **Home Assistant** 2023.1 or newer
- **Grant Aerona3 Heat Pump** 
- **MODBUS to Ethernet/USB Adapter** 
- **Modbus TCP enabled** on your heat pump (usually enabled by default)
- **Network access** from Home Assistant to the Modbus adapter IP address

## 🔧 **Hardware Requirements**

### Modbus Communication Setup
You'll need a way to connect Home Assistant to your Grant Aerona3's Modbus interface:

#### Recommended: Waveshare RS485 to Ethernet Converter
- **Model**: RS232/485/422 to POE ETH (B)
- **Default IP**: 192.168.1.200
- **Port**: 502
- **Wiring to Grant Aerona3**:
  - RS485+ (orange wire) → terminal 15
  - RS485- (orange/white wire) → terminal 16
  - GND → terminal 32

#### Alternative: USB to RS485 Converter
- Connect via USB to your Home Assistant device
- Requires serial configuration

### Grant Aerona3 Modbus Settings
- **Baud Rate**: 19200 bps
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 2
- **Slave Address**: 1 (default)
- **Enable Modbus**: Must be enabled in service menu parameter 51-15 set to 1, or coil register 15 

## Method 1: HACS Installation (Recommended)

### Step 1: Install HACS
If you haven't already, install [HACS (Home Assistant Community Store)](https://hacs.xyz/docs/setup/download).

### Step 2: Add Custom Repository
1. Open HACS in Home Assistant
2. Click on **Integrations**
3. Click the **⋮** menu (three dots) in the top right
4. Select **Custom repositories**
5. Add this repository:
   - **Repository**: `https://github.com/yourusername/grant-aerona3-hass`
   - **Category**: `Integration`
6. Click **Add**

### Recommended additional components
```
lovelace-card-mod
apexcharts-card.js?v=2.1.2
mushroom.js
card-mod.js
energy-flow-card-plus.js
button-card.js

```
### Step 3: Install Integration
1. Search for "Grant Aerona3" in HACS
2. Click **Download**
3. **Restart Home Assistant**

## Method 2: Manual Installation

### Step 1: Download Files
1. Download the latest release from [GitHub Releases](https://github.com/yourusername/grant-aerona3-hass/releases)
2. Extract the ZIP file

### Step 2: Copy Files
1. Copy the `grant_aerona3` folder to your Home Assistant `custom_components` directory:
   ```
   /config/custom_components/grant_aerona3/
   ```

2. Your directory structure should look like:
   ```
   /config/
   ├── custom_components/
   │   └── grant_aerona3/
   │       ├── __init__.py
   │       ├── config_flow.py
   │       ├── coordinator.py
   │       ├── sensor.py
   │       ├── binary_sensor.py
   │       ├── switch.py
   │       ├── number.py
   │       ├── climate.py
   │       ├── const.py
   │       └── manifest.json
   ```

### Step 3: Restart Home Assistant
Restart Home Assistant to load the integration.

## Setting Up the Integration

### Step 1: Find Your Heat Pump's IP Address

You need to find your Grant Aerona3's IP address. Try these methods:

#### Option A: Check Your Router
1. Log into your router's admin panel
2. Look for connected devices
3. Find "Grant" or "Aerona3" or look for the MAC address starting with common heat pump manufacturers

#### Option B: Network Scan
Use a network scanner app on your phone or computer to scan for devices on your network.

#### Option C: Check Heat Pump Display
Some Grant Aerona3 units show the IP address on the control panel:
1. Navigate to network settings on the heat pump display
2. Look for "IP Address" or "Network Status"

### Step 2: Add Integration to Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Grant Aerona3"
4. Click on **Grant Aerona3 Heat Pump**

### Step 3: Configure Connection

Enter your heat pump's network details:

| Field | Default | Description |
|-------|---------|-------------|
| **Host** | *required* | IP address of your Grant Aerona3 (e.g., `192.168.1.100`) |
| **Port** | `502` | Modbus TCP port (usually 502) |
| **Slave ID** | `1` | Modbus slave ID (usually 1) |
| **Scan Interval** | `30` | How often to poll data (seconds) |

#### Connection Settings Explained:

- **Host**: The IP address of your heat pump on your network
- **Port**: The Modbus TCP port - Grant Aerona3 typically uses port 502
- **Slave ID**: The Modbus device ID - Grant Aerona3 typically uses ID 1
- **Scan Interval**: How frequently to read data from the heat pump (30 seconds is recommended)

### Step 4: Test Connection

1. Click **Submit**
2. The integration will test the connection
3. If successful, you'll see a confirmation
4. If failed, check your network settings and try again

## Post-Installation Setup

### Step 1: Verify Entities
After successful installation, you should see 150+ new entities:

1. Go to **Settings** → **Devices & Services**
2. Find "Grant Aerona3 Heat Pump" 
3. Click on it to see all entities

### Step 2: Configure Flow Rate (Important!)
For accurate COP (Coefficient of Performance) calculations:

1. Find the **"Grant Aerona3 Flow Rate"** number entity
2. Set it to your measured flow rate (see [Flow Rate Measurement Guide](flow-rate-measurement.md))
3. Typical values:
   - **6kW model**: 15-18 L/min
   - **8kW model**: 18-22 L/min
   - **12kW model**: 20-25 L/min
   - **16kW model**: 25-30 L/min

### Step 3: Create Dashboard
Add entities to your dashboard - see [Examples](../examples/) for dashboard card configurations.

## Troubleshooting Installation

### Common Issues

#### "Cannot connect to device"
- ✅ Check the IP address is correct
- ✅ Ensure Home Assistant can reach the heat pump (try ping)
- ✅ Verify Modbus TCP is enabled on the heat pump
- ✅ Check firewall settings
- ✅ Try a different port if 502 doesn't work

#### "Integration not found"
- ✅ Ensure you've restarted Home Assistant after copying files
- ✅ Check the file structure matches exactly
- ✅ Verify all files were copied correctly

#### "No entities created"
- ✅ Check the logs for errors: **Settings** → **System** → **Logs**
- ✅ Verify the heat pump is responding to Modbus commands
- ✅ Try increasing the scan interval to 60 seconds

#### "Entities show 'Unavailable'"
- ✅ Check network connectivity between Home Assistant and heat pump
- ✅ Verify Modbus slave ID is correct (try 1, 2, or 3)
- ✅ Ensure heat pump Modbus interface is functioning

### Getting Help

If you're still having issues:

1. **Check the logs**: Settings → System → Logs, look for "grant_aerona3" errors
2. **Review troubleshooting**: See [Troubleshooting Guide](troubleshooting.md)
3. **Ask for help**: [GitHub Issues](https://github.com/yourusername/grant-aerona3-hass/issues)

Include this information when asking for help:
- Home Assistant version
- Grant Aerona3 model
- Network setup (same subnet, VLANs, etc.)
- Error messages from logs
- Configuration details (but not passwords!)

## Next Steps

- 📏 [Configure flow rate](flow-rate-measurement.md) for accurate COP calculations
- ⚙️ [Review configuration options](configuration.md)
- 🎯 [Set up automations](../examples/automations.yaml)
- 📊 [Create dashboard cards and install EMONCMS](../examples/lovelace-cards.yaml), here is a great video from Speak to the Geek telling you how to set up EMONCMS: https://www.youtube.com/watch?v=VOGLjONINqM


---

**Installation complete!** Your Grant Aerona3 heat pump is now fully integrated with Home Assistant.