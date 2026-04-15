# Unofficial Grant Aerona3 Heat Pump Integration for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.9.0b5+-blue.svg)](https://www.home-assistant.io/)
[![Grant Aerona3](https://img.shields.io/badge/Grant%20Aerona3-Supported-green.svg)](https://www.grantuk.com/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![British Made](https://img.shields.io/badge/British%20Made-🇬🇧-red.svg)](#)
[![Version](https://img.shields.io/badge/Version-1.1.2-brightgreen.svg)](#)

A comprehensive Home Assistant integration for **Grant Aerona3 Heat Pumps** using Modbus TCP communication. This integration automatically discovers and creates entities for all available registers, providing complete monitoring and control of your heat pump system with **ASHP** entity prefixes for better organization.

## ✨ Features

- **🔧 Simple Setup**: Just enter IP address, port, and scan interval - no complex configuration
- **📊 Complete Monitoring**: All 248 Modbus registers automatically created as entities with `ashp_` prefixes
- **🌡️ Accurate COP Calculation**: Configure your flow rate for precise efficiency measurements
- **⚙️ Full Control**: Switches and number entities cover setpoints, DHW and weather compensation
- **🔢 Setpoint Management**: Number entities for all temperature and timing settings
- **📈 Real-time Data**: Temperature sensors, power consumption, compressor frequency, and more
- **🚨 System Monitoring**: Error detection, defrost mode, and system health indicators
- **🌦️ Weather Compensation**: Advanced adaptive weather compensation with dual heating curves
- **⚡ Energy Monitoring**: Comprehensive energy usage tracking and cost estimation
- **🔧 Options Flow**: Configure scan intervals and flow rates through the UI

## 🆕 What's New in v1.1.2

- ✅ **Home Assistant 2025.9.0b5 Compatibility**: Fully tested and compatible
- ✅ **ASHP Entity Prefixes**: All entities now use `ashp_` prefixes for better organization
- ✅ **Enhanced Options Flow**: Configure settings through the Home Assistant UI
- ✅ **Improved Error Handling**: Better connection management and error reporting
- ✅ **Code Quality**: Modern Python type hints and improved documentation
- ✅ **Weather Compensation**: Advanced adaptive weather compensation features
- ✅ **Energy Monitoring**: Enhanced COP calculations and energy tracking
- ✅ **Modbus Scanner**: Modbus Scanner Tool to find new Registers
## 🚀 Quick Start

1. **Install** the integration (see [Installation Guide](Docs/installation_guide.md))
2. **Add Integration** via Home Assistant UI (Settings → Devices & Services → Add Integration)
3. **Enter Details**: IP address (required), port (502), slave ID (1), scan interval (30s)
4. **Configure Options**: Set flow rate and adjust scan interval via integration options
5. **Enjoy**: 150+ entities automatically created with `ashp_` prefixes and ready to use!

## 📊 What You Get

### Sensors (50+ entities with `ashp_` prefix)
- **Temperatures**: Flow, return, outdoor, DHW tank, discharge, suction, defrost
- **Power & Performance**: Power consumption, COP, efficiency, energy usage
- **System Status**: Compressor frequency, pump speeds, operating modes
- **Configuration Values**: All current setpoints and settings (read-only)
- **Energy Monitoring**: Daily energy consumption, cost estimates, monthly projections

### Binary Sensors (10+ entities with `ashp_` prefix)
- **System Status**: Compressor running, defrost active, heating active, DHW active
- **Safety Systems**: Alarm status, backup heater, frost protection, communication status
- **Weather Compensation**: Zone 1 and Zone 2 weather compensation status

### Switches (20+ entities with `ashp_` prefix)
- **Weather Compensation**: Enable/disable for each zone
- **Frost Protection**: Room, outdoor, and DHW frost protection
- **System Features**: Anti-legionella, humidity compensation, night mode
- **Terminal Configuration**: Remote controller, sensors, pumps, valves

### Numbers (95+ entities with `ashp_` prefix)
- **Temperature Setpoints**: Zone flow temperatures, DHW temperatures
- **Weather Compensation**: Curve settings for optimal efficiency
- **Timing Settings**: Delays, timeouts, and cycle times
- **Flow Rate Configuration**: Set your measured flow rate for accurate COP

## 🌦️ Advanced Weather Compensation

The integration includes sophisticated weather compensation features:

- **Adaptive Weather Compensation**: Automatically adjusts flow temperatures based on outdoor conditions
- **Dual Heating Curves**: Primary and secondary curves for different operating modes
- **Boost Mode**: Temporary higher temperature settings for rapid heating
- **Zone-Specific Control**: Independent weather compensation for Zone 1 and Zone 2
- **Blueprint Automations**: Ready-to-use Home Assistant blueprints included

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [📋 Installation Guide](Docs/installation_guide.md) | Step-by-step installation instructions |
| [⚙️ Configuration Guide](Docs/configuration_guide.md) | Detailed configuration options |
| [📏 Flow Rate Measurement](Docs/flow_rate_guide.md) | How to measure and configure flow rate for accurate COP |
| [🔧 Troubleshooting](Docs/troubleshooting_guide.md) | Common issues and solutions |
| [📚 Register Reference](Docs/reference_files/) | Complete list of all 150+ registers |
| [🎯 Examples](Examples/) | Sample automations and dashboard cards |

## 🏠 Typical Grant Aerona3 Systems

This integration works with all Grant Aerona3 configurations:

- **🔥 Heating Only** (65% of installs): Single zone heating
- **🔥💧 Heating + DHW** (25% of installs): Heating with hot water cylinder  
- **🏠🏠 Dual Zone** (8% of installs): Separate upstairs/downstairs control
- **🔄 Boiler Replacement** (2% of installs): Full system replacement

## 🔧 Requirements

- **Home Assistant** 2025.9.0b5 or newer (tested and compatible)
- **Grant Aerona3 Heat Pump** with Modbus TCP interface
- **Network Connection** between Home Assistant and heat pump
- **Python Libraries**: `pymodbus>=3.6.8,<4.0.0` (automatically installed)

## 📸 Screenshots

### Integration Setup
![Config Flow](Docs/images/Initial_setup.jpeg)

### Entity Overview
![Entities](Docs/images/entity_list.jpeg)

### Flow Rate Configuration
![Flow Rates](Docs/images/Flow_Rates.jpeg)

### PCB Diagram
![PCB Diagram](Docs/images/PCB_Diag.jpeg)

## 🔌 Hardware Setup

### RS485 to Ethernet Converter
For reliable Modbus TCP communication, we recommend:

**New Version (Recommended):**
- [Waveshare RS232/485/422 to PoE ETH-B](https://www.waveshare.com/rs232-485-422-to-poe-eth-b.htm)
- Power over Ethernet support
- Industrial-grade reliability

**Alternative:**
- [RS232 to RJ45 Ethernet Module](https://thepihut.com/products/rs232-to-rj45-ethernet-module)
- Basic functionality for budget setups

### Enclosure
- [Waterproof Enclosure](https://www.amazon.co.uk/Enclosure-Consumer-Waterproof-Terminals-Connectors/dp/B0BGSC2FF2)
- Protects hardware from outdoor conditions

## 🎛️ Recommended HACS Components

For the best dashboard experience:
```
lovelace-card-mod
apexcharts-card
mushroom
card-mod
energy-flow-card-plus
button-card
```

## 🆘 Support & Contributing

- **🐛 Report Issues**: [GitHub Issues](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/discussions)
- **📖 Documentation**: [Docs/](Docs/) folder
- **🤝 Contributing**: Pull requests welcome!

## 🔄 Changelog

### v1.1.1 (Latest)
- ✅ Home Assistant 2025.9.0b5 compatibility
- ✅ Added ASHP entity prefixes for better organization
- ✅ Enhanced options flow for UI configuration
- ✅ Improved error handling and connection management
- ✅ Fixed binary sensor syntax errors
- ✅ Added weather compensation entities and controls
- ✅ Enhanced energy monitoring and COP calculations

### v1.0.0
- 🎉 Initial release
- 📊 150+ automatically created entities
- 🌡️ Complete temperature monitoring
- ⚙️ Full system control capabilities

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Grant Engineering for the Aerona3 heat pump series
- Home Assistant community for the excellent platform
- Contributors and testers who helped improve this integration

## 🔗 Useful Links

- [Renewable Heating Hub Forums](https://renewableheatinghub.co.uk/forums)
- [Open Energy Monitor](https://openenergymonitor.org)
- [Home Assistant Green](https://www.home-assistant.io/green/)

---

**Made with ❤️ for the Home Assistant community**

*If this integration helps you monitor and control your Grant Aerona3 heat pump, please consider giving it a ⭐ on GitHub!*

## 🚀 Installation Methods

### Method 1: HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add this repository URL
5. Install "Grant Aerona3 Heat Pump"
6. Restart Home Assistant

### Method 2: Manual Installation
1. Download the latest release
2. Copy `custom_components/grant_aerona3/` to your Home Assistant `custom_components/` directory
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services

---

*Last updated: January 2025 - Compatible with Home Assistant 2025.9.0b5*
