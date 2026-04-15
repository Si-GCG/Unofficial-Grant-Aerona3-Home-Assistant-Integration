# Release Notes - v1.1.4

## 🚀 Major Changes

### Climate Platform Removal
- **Removed climate entities** - Eliminated the climate platform that was not providing significant value
- **Simplified integration** - Reduced complexity by removing unnecessary climate abstractions
- **Maintained functionality** - All core monitoring and control features remain intact

## 🔧 Technical Changes

### Platform Cleanup
- Deleted `climate.py` platform implementation (505 lines removed)
- Removed `Platform.CLIMATE` from integration setup
- Cleaned up climate domain references from HACS manifest
- Removed climate translations from `strings.json`

### Configuration Simplification
- Removed zone/DHW configuration options from options flow:
  - `enable_zone_1`
  - `zone_1_cooling`
  - `enable_zone_2`
  - `zone_2_cooling`
  - `enable_dhw`

### Documentation Updates
- Updated README.md to remove climate entity claims
- Modified configuration guide to clarify control via switches/numbers
- Updated installation guide file list
- Cleaned up Lovelace dashboard examples

## 📊 What You Get Now

The integration now provides **150+ entities** across:
- **🌡️ Sensors**: Temperature, power, efficiency monitoring
- **🔘 Binary Sensors**: System status indicators
- **🔄 Switches**: Weather compensation, frost protection controls
- **🔢 Numbers**: All temperature setpoints and configuration

## 🔄 Migration Notes

### For Existing Users
- **Climate entities will be removed** - Any existing climate entities will disappear
- **Use switches and numbers** - Control heating via the available switch and number entities
- **No data loss** - All sensor data and configuration remains intact

### Control Methods
Instead of climate entities, use:
- **Weather compensation switches** for zone control
- **Number entities** for temperature setpoints
- **DHW switches** for hot water control

## ✅ Benefits

- **Reduced complexity** - Fewer entity types to manage
- **Better performance** - Less overhead from unused climate abstractions
- **Clearer control** - Direct access to underlying heat pump settings
- **Maintained compatibility** - All other features work exactly as before

---

**Breaking Change**: Climate entities have been removed. Users should migrate to using the switch and number entities for heat pump control.