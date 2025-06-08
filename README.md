# Grant Aerona3 Heat Pump Integration for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-blue.svg)](https://www.home-assistant.io/)
[![Grant Aerona3](https://img.shields.io/badge/Grant%20Aerona3-Supported-green.svg)](https://www.grantuk.com/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![British Made](https://img.shields.io/badge/British%20Made-🇬🇧-red.svg)](#)


A comprehensive Home Assistant integration for **Grant Aerona3 Heat Pumps** using Modbus TCP communication. This integration automatically discovers and creates entities for all available registers, providing complete monitoring and control of your heat pump system.

## ✨ Features

- **🔧 Simple Setup**: Just enter IP address, port, and scan interval - no complex configuration
- **📊 Complete Monitoring**: All 150+ Modbus registers automatically created as entities
- **🌡️ Accurate COP Calculation**: Configure your flow rate for precise efficiency measurements
- **🏠 Zone Control**: Climate entities for heating zones with temperature control
- **⚙️ Full Control**: Switches for weather compensation, frost protection, and system settings
- **🔢 Setpoint Management**: Number entities for all temperature and timing settings
- **📈 Real-time Data**: Temperature sensors, power consumption, compressor frequency, and more
- **🚨 System Monitoring**: Error detection, defrost mode, and system health indicators

## 🚀 Quick Start

1. **Install** the integration (see [Installation Guide](Docs/installation_guide.md))
2. **Add Integration** via Home Assistant UI
3. **Enter Details**: IP address (required), port (502), slave ID (1), scan interval (30s)
4. **Configure Flow Rate**: Set your measured flow rate for accurate COP calculations
5. **Enjoy**: 150+ entities automatically created and ready to use!

## 📊 What You Get

### Sensors (50+ entities)
- **Temperatures**: Flow, return, outdoor, DHW tank, discharge, suction, defrost
- **Power & Performance**: Power consumption, COP, efficiency, energy usage
- **System Status**: Compressor frequency, pump speeds, operating modes
- **Configuration Values**: All current setpoints and settings (read-only)

### Binary Sensors (30+ entities)
- **System Status**: Running, defrost mode, error status
- **Configuration States**: Weather compensation, frost protection, terminal enables
- **Safety Systems**: Flow switch, backup heater status, alarm states

### Switches (20+ entities)
- **Weather Compensation**: Enable/disable for each zone
- **Frost Protection**: Room, outdoor, and DHW frost protection
- **System Features**: Anti-legionella, humidity compensation, night mode
- **Terminal Configuration**: Remote controller, sensors, pumps, valves

### Numbers (95+ entities)
- **Temperature Setpoints**: Zone flow temperatures, DHW temperatures
- **Weather Compensation**: Curve settings for optimal efficiency
- **Timing Settings**: Delays, timeouts, and cycle times
- **Flow Rate Configuration**: Set your measured flow rate for accurate COP

### Climate Entities
- **Zone 1**: Main heating zone control
- **Zone 2**: Secondary zone control (if configured)

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [📋 Installation Guide](Docs/installation_guide.md) | Step-by-step installation instructions |
| [⚙️ Configuration Guide](Docs/configuration_guide.md) | Detailed configuration options |
| [📏 Flow Rate Measurement](Docs/flow_rate_guide.md) | How to measure and configure flow rate for accurate COP |
| [🔧 Troubleshooting](Docs/troubleshooting_guide.md) | Common issues and solutions |
| [📚 Register Reference](Docs/reference_files/) | Complete list of all 150+ registers |
| [🎯 Examples](examples/) | Sample automations and dashboard cards |

## 🏠 Typical Grant Aerona3 Systems

This integration works with all Grant Aerona3 configurations:

- **🔥 Heating Only** (65% of installs): Single zone heating
- **🔥💧 Heating + DHW** (25% of installs): Heating with hot water cylinder  
- **🏠🏠 Dual Zone** (8% of installs): Separate upstairs/downstairs control
- **🔄 Boiler Replacement** (2% of installs): Full system replacement

## 🔧 Requirements

- **Home Assistant** 2023.1 or newer
- **Grant Aerona3 Heat Pump** with Modbus TCP interface
- **Network Connection** between Home Assistant and heat pump
- **Python Libraries**: `pymodbus` (automatically installed)

## 📸 Screenshots

### Integration Setup
![Config Flow](/Docs/images/Initial_setup.jpeg)

### Set Area
![Area](/Docs/images/set_area.jpeg)

### Entity Overview
![Entities](/Docs/images/entity_list.jpeg)

### Dashboard Example
![Dashboard](docs/images/dashboard-example.png)

### Recommended additional HACS components
```
lovelace-card-mod
apexcharts-card.js?v=2.1.2
mushroom.js
card-mod.js
energy-flow-card-plus.js
button-card.js
```
## 🆘 Support & Contributing

- **🐛 Report Issues**: [GitHub Issues](https://github.com/yourusername/grant-aerona3-hass/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/yourusername/grant-aerona3-hass/discussions)
- **📖 Documentation**: [docs/](docs/) folder
- **🤝 Contributing**: Pull requests welcome!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Grant Engineering for the Aerona3 heat pump series
- Home Assistant community for the excellent platform
- Contributors and testers who helped improve this integration

## 📄 Links
https://renewableheatinghub.co.uk/forums

https://openenergymonitor.org

https://www.home-assistant.io/green/

https://thepihut.com/products/rs232-to-rj45-ethernet-module

New version https://www.waveshare.com/rs232-485-422-to-poe-eth-b.htm

https://www.amazon.co.uk/Enclosure-Consumer-Waterproof-Terminals-Connectors/dp/B0BGSC2FF2

---

**Made with ❤️ for the Home Assistant community**

*If this integration helps you monitor and control your Grant Aerona3 heat pump, please consider giving it a ⭐ on GitHub!*
