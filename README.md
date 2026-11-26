<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/grant_aerona3/brand/dark_logo.png">
    <img src="custom_components/grant_aerona3/brand/logo.png" alt="Aerona3 Heat Pump" width="380">
  </picture>
</p>

# Unofficial Grant Aerona3 Heat Pump Integration for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.9.0+-blue.svg)](https://www.home-assistant.io/)
[![HACS / Marketplace](https://img.shields.io/badge/HACS%20%2F%20Marketplace-Custom-orange.svg)](https://hacs.xyz/)
[![Version](https://img.shields.io/github/v/release/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration?include_prereleases&color=brightgreen&label=Version)](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/releases)

An unofficial Home Assistant integration for **Grant Aerona3 air-source heat pumps**, communicating over Modbus (TCP or serial/RS485). It is not affiliated with or endorsed by Grant Engineering.

The integration reads and writes the heat pump's Modbus registers directly and exposes them as Home Assistant entities: sensors for live readings, numbers for setpoints and timers, switches for on/off features, and binary sensors for status flags.

## Features

- Works over Modbus TCP (e.g. via an RS485-to-Ethernet converter) or a local serial/RS485 connection
- Hardware feature toggles so you only get entities for the parts of the system you actually have (see below) — an install with everything ticked creates 150+ entities, most systems need far fewer
- Setpoint and timer control via number entities (DHW temperatures, weather-compensation curves, delays, hysteresis, etc.)
- Calculated COP and delta-T sensors based on a flow rate you configure
- Energy usage tracking and cost estimation sensors
- Options flow for changing scan interval, flow rate, and hardware toggles after setup, without removing the integration

## Hardware feature toggles

During setup (and later via **Settings → Devices & Services → Grant Aerona3 → Configure**) you tick which parts of your system are actually fitted. Unticked features are hidden from the UI and their Modbus registers are not polled, which also reduces the number of Modbus transactions per scan cycle.

| Toggle | What it covers |
|---|---|
| Hot water (DHW) cylinder | Domestic hot water cylinder heated by the heat pump |
| Buffer tank / volumiser | Buffer tank with temperature probe (terminals 11-12) |
| External heat source (EHS) | Hybrid boiler / external heat source for space heating (terminals 41-42) |
| Cooling mode | System configured to provide cooling as well as heating |
| Heating zones | Single zone, or dual zone with a second (slave) circuit |
| Backup / immersion heater | Electric backup heater fitted alongside the heat pump |
| Humidity sensor | Room humidity sensor wired to terminals 17-18 |
| Mixing valve / secondary circuit | 3-way mixing valve or low-loss header on terminals 4-5-6 and 13-14 |
| Additional outdoor sensor | Second outdoor temperature probe wired to terminals 9-10 |
| Low tariff / night mode signal | Wired to an economy-tariff or night-time noise-limiting signal (terminals 28-31) |
| Dehumidifier | Dehumidifier wired to terminal 45 |
| Advanced / installer settings | Frost-protection tuning, pump timing, error history, and terminal wiring switches — set once, rarely touched again |

Existing installs keep every entity after upgrading; the options above only change what a *new* install creates by default, and can be adjusted later from Configure either way.

## Experimental: flow offset and room trim

Off by default. Turn on **Experimental: flow temperature offset** under Configure to try it; turn it off again and the entities disappear. **Set the offset back to 0 before you turn it off**: switching it off does not touch the heat pump, so any offset still applied stays in the curve (you would then fix Tm1/Tm2 by hand).

**Flow offset.** A *Zone N flow offset* number (−5 to +5 °C in 0.5 steps) shifts your heating flow temperature up or down: in weather-compensation mode it moves the curve's max and min flow temperatures (Tm1 and Tm2) together, and in fixed-flow mode it moves the fixed setpoint. The outdoor-temperature points (Te1/Te2) and cooling are never touched, so the curve moves up and down, not sideways. Changes are limited to 24 a day, at least 30 minutes apart, to protect the unit's memory. A correction within 2 minutes of a change (up to 3 times) replaces that change instead of counting as a new one, so a mis-click can be undone. Flow is never taken below 23 °C or above the *Maximum flow temperature* option (default 55 °C, up to the unit's 60 °C limit). The offset stops where either end of the curve would hit one of those limits, so the curve keeps its shape: with a Tm2 of 25 °C, for example, the offset can go down by 2 °C at most.

**Fix the base curve first.** Installers set the starting curve from the design calculation, and it is often well off (45 °C at −3 °C outdoors is common and usually too hot). Use the offset for fine trimming around a curve you have already corrected. If you edit the curve registers yourself, the integration adopts your new curve as the baseline and resets the offset to 0.

**Room trim (optional).** Under Configure you can also enable a *Zone 1 room trim* climate entity. It holds a room target in Home Assistant and, every 30 minutes by default, moves the offset by at most 0.5 °C towards it using a room temperature sensor you choose. It is not a normal thermostat: the heat pump's own mode and room set point are read-only over Modbus. Choose a sensor in a representative room, not the heat pump controller's own reading (that controller is often in a warm cupboard). If the sensor goes unavailable or sends nothing new for 6 hours, or you turn the trim off, the offset returns to 0. If it sits at its limit for several checks, the entity says the base curve probably needs adjusting. It pauses in cooling mode.

## Experimental: flow temperature controller (preview)

Off by default, and in this version it **writes nothing to the heat pump**. Turn on **Experimental: flow temperature controller (preview)** under Configure, pick a room temperature sensor and, if you like, a Home Assistant schedule. A *Zone 1 suggested flow temperature* sensor then shows the fixed flow temperature a controller would choose, so you can judge it before anything controls your heating.

**How it chooses.** It starts from a line through two points you set (by default 40 °C flow at −3 °C outdoors and 28 °C at 15 °C), using the outdoor temperature averaged over the last hour. It then adds 1 °C of flow for each degree the room target is above 20 °C (and takes it away below), and 2 °C for each degree the room is below target. The result stays between your minimum (default 25 °C) and the *Maximum flow temperature* option. It is recalculated every 10 minutes.

**Targets.** 20 °C while the schedule is on, 17 °C while it is off, and 20 °C without a schedule. If the room sensor is unavailable or older than 6 hours, only the outdoor temperature is used.

**What to compare.** The sensor's attributes show each part of the sum and the current outgoing water temperature. The heat pump does not report the flow target its own curve is using, so that measured temperature is only meaningful while the unit is running.

**Before any control version:** the heat pump still decides when to run. An external room thermostat has to keep calling for heat, or a flow temperature controller has no effect.

## Quick Start

1. **Install** the integration (see the [Installation Guide](Docs/installation_guide.md))
2. **Add the integration** via Home Assistant: Settings → Devices & Services → Add Integration → Grant Aerona3 Heat Pump
3. **Choose connection type** and enter the details (IP address and port for Modbus TCP, or the serial device path for RS485)
4. **Tick the hardware toggles** that match your system
5. **Set your flow rate** for accurate COP calculation (see the [Flow Rate Guide](Docs/flow_rate_guide.md))
6. Entities for your selected hardware are created and start updating on the configured scan interval

## What you get

Exact entity counts depend on which hardware toggles are enabled. With everything ticked, the integration currently exposes:

- **Sensors** — temperatures (flow, return, outdoor, DHW tank, discharge, suction, defrost), power consumption, calculated COP and delta-T, compressor frequency, pump speed, operating mode, and energy usage/cost estimates
- **Binary sensors** — compressor running, defrost active, heating/DHW active, alarm status, backup heater status, frost protection, communication status, weather-compensation status
- **Switches** — weather compensation per zone, frost protection, anti-legionella, humidity compensation, night mode, terminal wiring options (gated by the toggles above)
- **Numbers** — every writable setpoint and timer on the heat pump (temperature setpoints, weather-compensation curves, delays, hysteresis, flow rate)

Note: the coordinator only polls a small, fixed subset of the coil registers on every refresh (to avoid Modbus timeouts), so a handful of the coil-backed switches show their last-known state rather than a live one between full refreshes.

## Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](Docs/installation_guide.md) | Step-by-step installation instructions |
| [Configuration Guide](Docs/configuration_guide.md) | Detailed configuration options |
| [Flow Rate Measurement](Docs/flow_rate_guide.md) | How to measure and configure flow rate for accurate COP |
| [Troubleshooting](Docs/troubleshooting_guide.md) | Common issues and solutions |
| [Register Reference](Docs/reference_files/) | Full list of supported registers |
| [Examples](Examples/) | Sample automations and dashboard cards |

## Requirements

- Home Assistant 2025.9.0 or newer
- Grant Aerona3 heat pump with a Modbus TCP or RS485 interface
- A network connection (Modbus TCP) or a serial/USB-RS485 connection between Home Assistant and the heat pump
- `pymodbus>=3.7.0,<4.0.0` and `pyserial>=3.4` (installed automatically)

## Screenshots

### Integration Setup
![Connection setup](Docs/images/initial_setup.png)
![Hardware toggles](Docs/images/initial_config.png)

### Entity Overview
![Entities](Docs/images/entity_list.jpeg)

### Flow Rate Configuration
![Flow Rates](Docs/images/Flow_Rates.jpeg)

### PCB Diagram
![PCB Diagram](Docs/images/PCB_Diag.jpeg)

## Hardware Setup (Modbus TCP)

If connecting over Modbus TCP via an RS485-to-Ethernet converter:

**Recommended:**
- [Waveshare RS232/485/422 to PoE ETH-B](https://www.waveshare.com/rs232-485-422-to-poe-eth-b.htm) — Power over Ethernet, industrial-grade

**Alternative:**
- [RS232 to RJ45 Ethernet Module](https://thepihut.com/products/rs232-to-rj45-ethernet-module) — basic functionality for budget setups

### Enclosure
- [Waterproof Enclosure](https://www.amazon.co.uk/Enclosure-Consumer-Waterproof-Terminals-Connectors/dp/B0BGSC2FF2) for outdoor-mounted converters

## Recommended HACS Dashboard Components

Not required, but useful for building dashboards with this integration:
```
lovelace-card-mod
apexcharts-card
mushroom
card-mod
energy-flow-card-plus
button-card
```

## Support & Contributing

- **Report Issues**: [GitHub Issues](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/issues) — please attach the file from Settings → Devices & Services → Grant Aerona3 → ⋮ → Download diagnostics ([details](Docs/troubleshooting_guide.md#download-diagnostics))
- **Feature Requests**: [GitHub Discussions](https://github.com/Si-GCG/Unofficial-Grant-Aerona3-Home-Assistant-Integration/discussions)
- **Documentation**: [Docs/](Docs/) folder
- Pull requests welcome — this is a solo-maintained project with no CI, so please run the checks in `.claude/skills/validate` (or the equivalent manual steps) before submitting

## Changelog

### v1.2.0
- **Breaking change**: removed the duplicate read-only `sensor.*` entity for every writable holding register (setpoints) — only the `number.*` entity remains, since it already showed the same value. If a dashboard, automation, or template referenced one of these sensors, point it at the matching `number.*` entity instead (see the [troubleshooting guide](Docs/troubleshooting_guide.md#dashboard-card-shows-entity-not-available-after-updating))
- Added 7 new optional-hardware toggles: backup/immersion heater, humidity sensor, mixing valve/secondary circuit, additional outdoor sensor, low-tariff/night-mode signal, dehumidifier, and a bundled "advanced/installer" group (frost-protection tuning, pump timing, error history, terminal wiring switches). Each hides the matching entities and stops polling those registers
- Existing installs keep every entity on upgrade; new installs default the optional toggles off

### v1.1.4
- Breaking change: removed the climate platform and its entities
- Simplified configuration by removing unused zone/DHW options
- Updated documentation and examples

### v1.1.2
- Home Assistant 2025.9.0b5 compatibility
- Entity naming improvements
- Enhanced options flow and error handling
- Added weather compensation and energy monitoring sensors

### v1.0.0
- Initial release

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Grant Engineering for the Aerona3 heat pump series
- The Home Assistant community
- Contributors and testers who helped improve this integration

## Useful Links

- [Renewable Heating Hub Forums](https://renewableheatinghub.co.uk/forums)
- [Open Energy Monitor](https://openenergymonitor.org)
- [Home Assistant Green](https://www.home-assistant.io/green/)

---

## Installation Methods

### Method 1: Marketplace or HACS (Recommended)

**Home Assistant 2026.11 or later (Marketplace)**
1. Open Settings → Marketplace
2. Add this repository as a custom repository (Add from link) using its GitHub URL
3. Install "Grant Aerona3 Heat Pump"
4. Restart Home Assistant

**Earlier versions (HACS)**
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three-dot menu → "Custom repositories"
4. Add this repository's URL
5. Install "Grant Aerona3 Heat Pump"
6. Restart Home Assistant

### Method 2: Manual Installation
1. Download the latest release
2. Copy `custom_components/grant_aerona3/` into your Home Assistant `custom_components/` directory
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services
