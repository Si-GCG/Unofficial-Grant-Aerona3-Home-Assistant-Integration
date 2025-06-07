"""Constants for Grant Aerona3 Heat Pump integration."""
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
    UnitOfFrequency,
    PERCENTAGE,
)
# Domain
DOMAIN = "grant_aerona3"
# Device information
MANUFACTURER = "Grant"
MODEL = "Aerona3"

# Operating modes
OPERATING_MODES = {
    0: "Off",
    1: "Heating",
    2: "Cooling", 
    3: "DHW",
    4: "Auto"
}

# DHW (Domestic Hot Water) modes
DHW_MODES = {
    0: "Off",
    1: "Comfort",
    2: "Economy",
    3: "Boost"
}

# Days of the week
DAYS_OF_WEEK = {
    0: "Monday",
    1: "Tuesday", 
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}

# Climate modes mapping
CLIMATE_MODES = {
    "off": 0,
    "heat": 1,
    "cool": 2,
    "auto": 4
}

# Error codes mapping
ERROR_CODES = {
    0: "No Error",
    1: "High Pressure",
    2: "Low Pressure", 
    3: "Compressor Overload",
    4: "Fan Motor Error",
    5: "Water Flow Error",
    6: "Temperature Sensor Error",
    7: "Communication Error"
}


# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30

# Register types
INPUT_REGISTERS = "input"
HOLDING_REGISTERS = "holding"
COIL_REGISTERS = "coil"

# INPUT REGISTERS - Fixed scaling for temperatures
INPUT_REGISTER_MAP = {
    0: {
        "name": "Return Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Fixed: was 0.1, now 1
        "offset": 0,
        "description": "Return water temperature"
    },
    1: {
        "name": "Compressor Operating Frequency",
        "unit": UnitOfFrequency.HERTZ,
        "device_class": SensorDeviceClass.FREQUENCY,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Correct: frequencies don't need scaling
        "offset": 0,
        "description": "Compressor operating frequency"
    },
    2: {
        "name": "Discharge Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Fixed: was 0.1, now 1
        "offset": 0,
        "description": "Discharge temperature"
    },
    3: {
        "name": "Current Consumption Value",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 100,  # ✅ Correct: power often needs scaling
        "offset": 0,
        "description": "Current consumption value"
    },
    4: {
        "name": "Fan Control Number Of Rotation",
        "unit": "rpm",
        "device_class": None,
        "state_class": None,
        "scale": 10,  # ✅ Correct: RPM scaling
        "offset": 0,
        "description": "Fan control number of rotation"
    },
    5: {
        "name": "Defrost Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Fixed: was 0.1, now 1
        "offset": 0,
        "description": "Defrost temperature"
    },
    6: {
        "name": "Outdoor Air Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Fixed: was 0.1, now 1
        "offset": 0,
        "description": "Outdoor air temperature"
    },
    7: {
        "name": "Water Pump Control Number Of Rotation",
        "unit": "rpm",
        "device_class": None,
        "state_class": None,
        "scale": 100,  # ✅ Correct: pump RPM scaling
        "offset": 0,
        "description": "Water pump control number of rotation"
    },
    8: {
        "name": "Suction Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Fixed: was 0.1, now 1
        "offset": 0,
        "description": "Suction temperature"
    },
    9: {
        "name": "Outgoing Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 1, now 0.1
        "offset": 0,
        "description": "Outgoing water temperature"
    },
    10: {
        "name": "Selected Operating Mode",
        "unit": None,
        "device_class": None,
        "state_class": None,
        "scale": 1,  # ✅ Correct: mode values don't need scaling
        "offset": 0,
        "description": "Selected operating mode (0=Heating/Cooling OFF, 1=Heating, 2=Cooling)"
    },
    11: {
        "name": "Room Air Set Temperature of Zone 1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 0.5, should be 0.1
        "offset": 0,
        "description": "Room air set temperature of Zone1(Master)"
    },
    12: {
        "name": "Room Air Set Temperature Of Zone 2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 0.5, should be 0.1
        "offset": 0,
        "description": "Room air set temperature of Zone2(Slave)"
    },
    16: {
        "name": "DHW Tank Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 0.5, should be 0.1
        "offset": 0,
        "description": "DHW tank temperature (Terminal 7-8)"
    },
    17: {
        "name": "Outdoor Air Temperature - Remote Sensor",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 0.5, should be 0.1
        "offset": 0,
        "description": "Outdoor air temperature (Terminal 9-10)"
    },
    18: {
        "name": "Buffer Tank Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 0.5, should be 0.1
        "offset": 0,
        "description": "Buffer tank temperature (Terminal 11-12)"
    },
    19: {
        "name": "Mix Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  # ✅ Fixed: was 0.5, should be 0.1
        "offset": 0,
        "description": "Mix water temperature (Terminal 13-14)"
    },
    32: {
        "name": "Plate Heat Exchanger Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # ✅ Fixed: was 0.1, should be 1
        "offset": 0,
        "description": "Plate heat exchanger temperature"
    },
}

# Holding Registers (Read/Write configuration settings)
HOLDING_REGISTER_MAP = {
    2: {
        "name": "Fixed Flow Temp Zone 1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Heating Zone1, Fixed Outgoing water set point in Heating"
    },
    3: {
        "name": "Max Flow Temp Zone1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Heating mode (Tm1) Zone1"
    },
    4: {
        "name": "Min Flow Temp Zone1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Heating mode (Tm2) Zone1"
    },
    5: {
        "name": "Min. Outdoor Air Temperature Zone1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone1"
    },
    6: {
        "name": "Max. Outdoor Air Temperature Zone1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone1"
    },
    7: {
        "name": "Fixed Flow Temp Zone 2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Heating Zone2, Fixed Outgoing water set point in Heating"
    },
    8: {
        "name": "Max Flow Temp Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Heating mode (Tm1) Zone2"
    },
    9: {
        "name": "Min Flow Temp Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Heating mode (Tm2) Zone2"
    },
    10: {
        "name": "Min. Outdoor Air Temperature Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone2"
    },
    11: {
        "name": "Max. Outdoor Air Temperature Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone2"
    },
    12: {
        "name": "Cooling Fixed Flow Temp Zone 1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Cooling Zone1, Fixed Outgoing water set point in Cooling"
    },
    13: {
        "name": "Max. Flow Temperature In Cooling Mode",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Cooling mode (Tm1) Zone1"
    },
    14: {
        "name": "Min. Flow Water Temperature In Cooling Mode",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Cooling mode (Tm2) Zone1"
    },
    15: {
        "name": "Min. Outdoor Air Temperature Cooling Zone1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to min. Outgoing water temperature Cooling (Te1) Zone1"
    },
    16: {
        "name": "Max. Outdoor Air Temperature Corresponding To max. Outgoing water temperature Cooling (Te2) Zone1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature Cooling (Te2) Zone1"
    },
    17: {
        "name": "Cooling Fixed Flow Temp Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Cooling Zone2, Fixed Outgoing water set point in Cooling"
    },
    18: {
        "name": "Max Flow Temperature In Cooling Mode 2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Cooling mode (Tm1) Zone2"
    },
    19: {
        "name": "Min Flow Temperature In Cooling Mode 2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Cooling mode (Tm2) Zone2"
    },
    20: {
        "name": "Min Outdoor Air Temperature Cooling Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone2"
    },
    21: {
        "name": "Max. Outdoor Air Temperature Cooling Zone2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone2"
    },
    22: {
        "name": "Hysteresis Of Water Set Point In Heating And DHW",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of water set point in Heating and DHW"
    },
    23: {
        "name": "Hysteresis Of Water Set Point In Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of water set point in Cooling"
    },
    24: {
        "name": "Low Tariff Deferential Water Set Point For Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Low tariff deferential water set point for Heating"
    },
    25: {
        "name": "Low Tariff Deferential Water Set Point For Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Low tariff deferential water set point for Cooling"
    },
    26: {
        "name": "DHW Production Priority Setting",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "DHW production priority setting (0=DHW is unavailable, 1=DHW is available and priority DHW over space Heating, 2=DHW is available and priority space Heating over DHW)"
    },
    27: {
        "name": "Type Of Configuration To Heat The DHW",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Type of configuration to heat the DHW (0=Heat pump + Heater, 1=Heat pump only, 2=Heater only)"
    },
    28: {
        "name": "DHW Comfort Set Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW Comfort set temperature"
    },
    29: {
        "name": "DHW Economy Set Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW Economy set temperature"
    },
    30: {
        "name": "DHW Set Point Hysteresis",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW set point hysteresis"
    },
    31: {
        "name": "DHW Over Boost Mode Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW Over boost mode set point"
    },
    32: {
        "name": "Max. Time For DHW Request",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Max. time for DHW request"
    },
    33: {
        "name": "Delay Time On DHW Heater From Off Compressor",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time on DHW heater from OFF compressor"
    },
    34: {
        "name": "Outdoor Air Temperature To Enable DHW Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable DHW heaters"
    },
    35: {
        "name": "Outdoor Air Temperature Hysteresis To Disable DHW Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable DHW heaters"
    },
    36: {
        "name": "Anti-legionella Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Anti-legionella set point"
    },
    37: {
        "name": "Max. Frequency Of Night Mode",
        "unit": None,
        "device_class": SensorDeviceClass.FREQUENCY,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Max. frequency of Night mode"
    },
    38: {
        "name": "Min. Time Compressor On/off Time",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Min. time compressor ON/OFF time"
    },
    39: {
        "name": "Delay Time Pump Off From Compressor Off",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time pump OFF from compressor OFF"
    },
    40: {
        "name": "Delay Time Compressor On From Pump On",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time compressor ON from pump ON"
    },
    41: {
        "name": "Type Of Configuration Of Main Water Pump",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Type of configuration of Main water pump (0=always ON, 1=ON/OFF based on Buffertank temperature, 2=ON/OFF based on Sniffing cycles"
    },
    42: {
        "name": "Time On Main Water Pump For Sniffing Cycle",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Time ON Main water pump for Sniffing cycle"
    },
    43: {
        "name": "Time Off Main Water Pump",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Time OFF Main water pump"
    },
    44: {
        "name": "Delay Time Off Main Water Pump From Off Compressor",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time OFF Main water pump from OFF compressor"
    },
    45: {
        "name": "Off Time For Unlock Pump Function Start",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "OFF time for Unlock pump function start"
    },
    46: {
        "name": "Time On Main Water Pump For Unlock Pump Function",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Time ON Main water pump for Unlock pump function"
    },
    47: {
        "name": "Time On Water Pump1 For Unlock Pump Function",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Time ON water pump1 for Unlock pump function"
    },
    48: {
        "name": "Time On Water Pump2 For Unlock Pump Function",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Time ON water pump2 for Unlock pump function"
    },
    49: {
        "name": "Type Of Operation Of Additional Water Pump",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Type of operation of additional water pump (0=disable, 1=depending on Main water pump setting, 2=depending on Main water pump setting but always OFF when the DHW mode is activated, 3=always ON apart if any alarms are activated or if the HP unit is in OFF mode, 4=ON/OFF based on Room air temperature)"
    },
    50: {
        "name": "Start Temperature Of Frost Protection On Room Air Temp",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Start temperature of Frost protection on Room air temperature"
    },
    51: {
        "name": "Hysteresis Of Room Air Temperature Of Frost Protection",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of Room air temperature of Frost protection"
    },
    52: {
        "name": "Water Temperature Of Frost Protection",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Water temperature of Frost protection"
    },
    53: {
        "name": "Delay Time Off Main Water Pump From Off",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time OFF Main water pump from OFF Frost protection operation function"
    },
    54: {
        "name": "Start Temperature Of Frost Protection On Outdoor Air Temp",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Start temperature of Frost protection on Outdoor air temperature"
    },
    55: {
        "name": "Hysteresis Of Outdoor Air Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of Outdoor air temperature"
    },
    56: {
        "name": "Backup Heater Set Point During Frost Protection",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Backup heater set point during Frost protection"
    },
    57: {
        "name": "Hysteresis Of Outgoing Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of Outgoing water temperature"
    },
    58: {
        "name": "Start Temperature Of Frost Protection On DHW Tank Temp",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Start temperature of Frost protection on DHW tank temperature"
    },
    59: {
        "name": "Hysteresis Of DHW Tank Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of DHW tank temperature"
    },
    60: {
        "name": "Room Relative Humidity Value",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Room relative humidity value"
    },
    61: {
        "name": "Room Relative Humidity Value To Start Increasing Flow Temp",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Room relative humidity value to start increasing Outgoing water temperature set"
    },
    62: {
        "name": "Max Flow Temp Hysteresis relative to Humidity",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing temperature hysteresis corresponding to 100% relative humidity"
    },
    63: {
        "name": "Mixing Valve Runtime",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Mixing valve runtime (from the fully closed to the fully open position)"
    },
    64: {
        "name": "Mixing Valve Integral Factor",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Mixing valve integral factor"
    },
    65: {
        "name": "Max Water Temperature In Mixing Circuit",
        "unit": None,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Max Water temperature in mixing circuit"
    },
    66: {
        "name": "3way Valve Change Over Time",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "3way valve change over time"
    },
    67: {
        "name": "Flow Switch Alarm Delay Time At. Pump Start Up",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Flow switch alarm delay time at. Pump start up"
    },
    68: {
        "name": "Flow Switch Alarm Delay Time",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Flow switch alarm delay time in steady operation of the water pump"
    },
    69: {
        "name": "The Number Of Retry Until Displaying Alarm",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "The number of retry until displaying alarm"
    },
    70: {
        "name": "The Time Of Repeating Retry Until Displaying Alarm",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "The time of repeating retry until displaying alarm"
    },
    71: {
        "name": "Backup Heater Type Of Function",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Backup heater type of function (0=disable, 1=Replacement mode, 2=Emergency mode, 3=Supplementary mode)"
    },
    72: {
        "name": "Manual Water Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Manual water set point"
    },
    73: {
        "name": "Manual Water Temperature Hysteresis",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Manual water temperature hysteresis"
    },
    74: {
        "name": "Delay Time Of The Heater Off That Avoid Flow Switch Alarm",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time of the heater OFF that avoid flow switch alarm"
    },
    75: {
        "name": "Heater Activation Delay Time",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Heater activation delay time"
    },
    76: {
        "name": "Integration Time For Starting Heaters",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Integration time for starting heaters"
    },
    77: {
        "name": "Outdoor Air Temperature To Enable Backup Heater",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable Backup heaters and disable compressor"
    },
    78: {
        "name": "Outdoor Air Temperature Hysteresis To Disable Backup Heaters and Enable Compressor",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable Backup heaters and enable compressor"
    },
    79: {
        "name": "Outdoor Air Temperature To Enable Backup Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable Backup heaters (Supplementary mode)"
    },
    80: {
        "name": "Outdoor Air Temperature Hysteresis To Disable Backup Heaters (Supplementary Mode)",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable Backup heaters (Supplementary mode)"
    },
    81: {
        "name": "Freeze Protection Functions",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Freeze protection functions (0=disable, 1=enabled during Start-up, 2=enabled during Defrost, 3=enabled during Start-up and Defrost)"
    },
    82: {
        "name": "Outgoing Water Temperature Set Point During Start-up",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outgoing water temperature set point during Start-up"
    },
    83: {
        "name": "Hysteresis Water Temperature Set Point During Start-up",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis water temperature set point during Start-up"
    },
    84: {
        "name": "EHS Type Of Function",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "EHS type of function (0=disable, 1=Replacement mode, 2=Supplementary mode)"
    },
    85: {
        "name": "Outdoor Air Temperature To Enable EHS And Disable Compressor",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable EHS and disable compressor"
    },
    86: {
        "name": "Outdoor Air Temperature Hysteresis To Disable Enable Compressor",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable EHS and enable compressor"
    },
    87: {
        "name": "Outdoor Air Temperature To Enable EHS",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable EHS (Supplementary mode)"
    },
    88: {
        "name": "Outdoor Air Temperature Hysteresis To Disable EHS",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable EHS (Supplementary mode)"
    },
    89: {
        "name": "EHS Activation Delay Time",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "EHS activation delay time"
    },
    90: {
        "name": "Integration Time For Starting EHS",
        "unit": None,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Integration time for starting EHS"
    },
    91: {
        "name": "Terminal 20-21 : On/off Remote Contact Or EHS Alarm",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 20-21 : ON/OFF remote contact or EHS Alarm input (0=disable (Remote controller only), 1=ON/OFF remote contact, 2=EHS Alarm input)"
    },
    92: {
        "name": "Terminal 24-25 : Heating/cooling Mode Remote Contact",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 24-25 : Heating/Cooling mode remote contact (0=disable (Remote controller only), 1=Cooling is CLOSE contact Heating is OPEN contact, 2=Cooling is OPEN contact Heating is CLOSE contact)"
    },
    93: {
        "name": "Terminal 47 : Alarm",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 47 : Alarm (Configurable output) (0=disable, 1=Alarm, 2=Ambient temperature reached)"
    },
    94: {
        "name": "Terminal 48 : Pump1",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 48 : Pump1 (0=disable, 1=1st Additional water pump1 for Zone1)"
    },
    95: {
        "name": "Terminal 49 : Pump2",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 49 : Pump2 (0=disable, 1=2nd Additional water pump2 for Zone2)"
    },
    96: {
        "name": "Terminal 50-51-52 : DHW 3way Valve",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 50-51-52 : DHW 3way valve (1=enable)"
    },
    99: {
        "name": "Buffer Tank Set Point For Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Buffer tank set point for Heating"
    },
    100: {
        "name": "Buffer Tank Set Point For Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": None,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Buffer tank set point for Cooling"
    },
}

# Coil Registers (Read/Write boolean controls)
COIL_REGISTER_MAP = {
    1: {
        "name": "Operation At The Time Of Reboot After Blackout 0",
        "device_class": None,
        "description": "Operation at the time of reboot after blackout 0 = disable 1 = enable"
    },
    2: {
        "name": "Heating Weather Compensation Zone 1",
        "device_class": None,
        "description": "Heating Zone1, enable Outgoing water set point (0=Fixed set point, 1=Climatic curve)"
    },
    3: {
        "name": "Heating Weather Compensation Zone 2",
        "device_class": None,
        "description": "Heating Zone2, enable Outgoing water set point (0=Fixed set point, 1=Climatic curve)"
    },
    4: {
        "name": "Cooling Weather Compensation Zone 1",
        "device_class": None,
        "description": "Cooling Zone1, enable Outgoing water set point (0=Fixed set point, 1=Climatic curve)"
    },
    5: {
        "name": "Cooling Weather Compensation Zone 2",
        "device_class": None,
        "description": "Cooling Zone2, enable Outgoing water set point (0=Fixed set point, 1=Climatic Curve)"
    },
    6: {
        "name": "Anti-legionella Function",
        "device_class": None,
        "description": "Anti-legionella function (0=disable, 1=enable)"
    },
    7: {
        "name": "The HP Unit Turns On/off Based On",
        "device_class": None,
        "description": "The HP unit turns ON/OFF based on (0=Room set point, 1=Water set point)"
    },
    8: {
        "name": "Frost Protection Based On Room Temperature",
        "device_class": None,
        "description": "Frost Protection based on Room Temperature"
    },
    9: {
        "name": "Frost Protection Based On Outdoor Temperature",
        "device_class": None,
        "description": "Frost protection by outdoor temperature 0=disable 1 = enable"
    },
    10: {
        "name": "Frost Protection Based On Flow Temp",
        "device_class": None,
        "description": "Frost protection based on Outgoing water temperature 0=disable 1 = enable"
    },
    11: {
        "name": "DHW Storage Frost Protection",
        "device_class": None,
        "description": "DHW storage frost protection 0=disable 1 = enable"
    },
    12: {
        "name": "Secondary System Circuit Frost Protection",
        "device_class": None,
        "description": "Secondary system circuit frost protection 0=disable 1 = enable"
    },
    13: {
        "name": "Compensation For Room Humidity",
        "device_class": None,
        "description": "Compensation for room humidity (0=disable, 1=enable)"
    },
    14: {
        "name": "Conditions To Be Available Backup Heaters",
        "device_class": None,
        "description": "Conditions to be available Backup heaters (0=always enabled, 1=depends on Outdoor Air temperature)"
    },
    15: {
        "name": "Terminal 41-42 : EHS (External heat source for space heating)",
        "device_class": None,
        "description": "Terminal 41-42 : EHS (0=disable, 1=enable)"
    },
    16: {
        "name": "Terminal 1-2-3 : Remote Controller",
        "device_class": None,
        "description": "Terminal 1-2-3 : Remote Controller (0=disable, 1=enable)"
    },
    17: {
        "name": "Terminal 4-5-6 : 3way Mixing Valve",
        "device_class": None,
        "description": "Terminal 4-5-6 : 3way mixing valve (0=disable, 1=enable)"
    },
    18: {
        "name": "Terminal 7-8 : DHW Tank Temperature Probe",
        "device_class": None,
        "description": "Terminal 7-8 : DHW tank temperature probe (0=disable, 1=enable)"
    },
    19: {
        "name": "Terminal 9-10 : Outdoor Air Temperature Probe",
        "device_class": None,
        "description": "Terminal 9-10 : Outdoor air temperature probe (additional) (0=disable, 1=enable)"
    },
    20: {
        "name": "Terminal 11-12 : Buffer Tank Temperature Probe",
        "device_class": None,
        "description": "Terminal 11-12 : Buffer tank temperature probe (0=disable, 1=enable)"
    },
    21: {
        "name": "Terminal 13-14 : Mix Water Temperature Probe",
        "device_class": None,
        "description": "Terminal 13-14 : Mix Water temperature probe (0=disable, 1=enable)"
    },
    22: {
        "name": "Terminal 15-16-32 : Rs485 Mod Bus",
        "device_class": None,
        "description": "Terminal 15-16-32 : RS485 Mod Bus (0=disable, 1=enable)"
    },
    23: {
        "name": "Terminal 17-18 : Humidity Sensor",
        "device_class": None,
        "description": "Terminal 17-18 : Humidity sensor (0=disable, 1=enable)"
    },
    24: {
        "name": "Terminal 19-18 : DHW Remote Contact",
        "device_class": None,
        "description": "Terminal 19-18 : DHW remote contact (0=disable (Remote controller only), 1=enable)"
    },
    25: {
        "name": "Terminal 22-23 : Dual Set Point Control",
        "device_class": None,
        "description": "Terminal 22-23 : Dual set point control (0=disable, 1=enable)"
    },
    26: {
        "name": "Terminal 26-27 : Flow Switch",
        "device_class": None,
        "description": "Terminal 26-27 : Flow switch (0=disable, 1=enable)"
    },
    27: {
        "name": "Terminal 28-29 : Night Mode",
        "device_class": None,
        "description": "Terminal 28-29 : Night mode (0=disable (Remote controller only), 1=enable)"
    },
    28: {
        "name": "Terminal 30-31 : Low Tariff",
        "device_class": None,
        "description": "Terminal 30-31 : Low tariff (0=disable (Remote controller only), 1=enable)"
    },
    29: {
        "name": "Terminal 41-42 : EHS",
        "device_class": None,
        "description": "Terminal 41-42 : EHS (External heat source for space heating) (0=disable, 1=enable)"
    },
    30: {
        "name": "Terminal 43-44 : Heating/cooling Mode Output",
        "device_class": None,
        "description": "Terminal 43-44 : Heating/Cooling mode output (0=disable, 1=Indication of Cooling mode (CLOSE=Cooling), 2=indication of Heating mode (CLOSE=Heating))"
    },
    31: {
        "name": "Terminal 45 : Dehumidifier",
        "device_class": None,
        "description": "Terminal 45 : Dehumidifier (0=disable, 1=enable)"
    },
    32: {
        "name": "Terminal 46 : DHW Electric Heater Or Backup Heater",
        "device_class": None,
        "description": "Terminal 46 : DHW Electric heater or Backup heater (0=DHW Electric heater, 1=Backup heater)"
    },
}

# Installation Templates
INSTALLATION_TEMPLATES = {
    "single_zone": {
        "name": "Single Zone Heating",
        "description": "Most common setup with one heating zone",
        "percentage": "65%",
        "enabled_registers": {
            "input": list(range(0, 21)) + [32], 
            "holding": list(range(2, 97)) + [99, 100], 
            "coil": list(range(1, 33))
        }
    },
    "dual_zone": {
        "name": "Dual Zone Heating",
        "description": "Upstairs/downstairs or separate zones",
        "percentage": "20%",
        "enabled_registers": {
            "input": list(range(0, 21)) + [32], 
            "holding": list(range(2, 97)) + [99, 100], 
            "coil": list(range(1, 33))
        }
    },
    "dhw_only": {
        "name": "Hot Water Only",
        "description": "Cylinder heating only",
        "percentage": "8%",
        "enabled_registers": {
            "input": [0, 1, 2, 3, 6, 11, 21, 22, 26],
            "holding": [],
            "coil": [1, 6]
        }
    },
    "replacement": {
        "name": "Boiler Replacement",
        "description": "Full system replacement",
        "percentage": "5%",
        "enabled_registers": {
            "input": list(range(0, 33)),
            "holding": list(range(2, 100)),
            "coil": list(range(1, 34))
        }
    },
    "custom": {
        "name": "Custom Configuration",
        "description": "Advanced users - all registers",
        "percentage": "2%",
        "enabled_registers": {
            "input": list(range(0, 21)) + [32], 
            "holding": list(range(2, 97)) + [99, 100], 
            "coil": list(range(1, 33))
        }
    }
}
