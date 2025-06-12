"""Constants for Grant Aerona3 Heat Pump integration with ASHP prefixes."""
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
    UnitOfFrequency,
    UnitOfPressure,
    UnitOfTime,
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
    7: "Communication Error",
    8: "Outdoor Sensor Error",
    9: "Indoor Sensor Error",
    10: "Flow Sensor Error",
    11: "Return Sensor Error",
    12: "DHW Sensor Error",
    13: "Buffer Tank Sensor Error",
    14: "Mix Water Sensor Error",
    15: "Defrost Sensor Error"
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

# INPUT REGISTERS - Temperature and sensor readings (Read-only) - Based on actual register document
INPUT_REGISTER_MAP = {
    0: {
        "name": "Return Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale as per document
        "offset": 0,
        "description": "Return water temperature (monitor display No.d0)"
    },
    1: {
        "name": "Compressor Operating Frequency",
        "unit": UnitOfFrequency.HERTZ,
        "device_class": SensorDeviceClass.FREQUENCY,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1Hz scale as per document
        "offset": 0,
        "description": "Compressor operating frequency (monitor display No.d1)"
    },
    2: {
        "name": "Discharge Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale
        "offset": 0,
        "description": "Discharge temperature (monitor display No.d2)"
    },
    3: {
        "name": "Current Consumption Value",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 100,  # 100W scale as per document
        "offset": 0,
        "description": "Current consumption value (monitor display No.d3)"
    },
    4: {
        "name": "Fan Control Rotation",
        "unit": "rpm",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 10,  # 10rpm scale as per document
        "offset": 0,
        "description": "Fan control number of rotation"
    },
    5: {
        "name": "Defrost Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale
        "offset": 0,
        "description": "Defrost temperature (monitor display No.d5)"
    },
    6: {
        "name": "Outdoor Air Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale as per document
        "offset": 0,
        "description": "Outdoor air temperature (monitor display No.d6)"
    },
    7: {
        "name": "Water Pump Control Rotation",
        "unit": "rpm",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 100,  # 100rpm scale as per document
        "offset": 0,
        "description": "Water pump control number of rotation (monitor display No.d7)"
    },
    8: {
        "name": "Suction Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale
        "offset": 0,
        "description": "Suction temperature (monitor display No.d8)"
    },
    9: {
        "name": "Outgoing Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale
        "offset": 0,
        "description": "Outgoing water temperature (monitor display No.d9)"
    },
    10: {
        "name": "Selected Operating Mode",
        "unit": None,
        "device_class": None,
        "state_class": None,
        "scale": 1,
        "offset": 0,
        "description": "Selected operating mode (0=Heating/Cooling OFF, 1=Heating, 2=Cooling)"
    },
    11: {
        "name": "Room Air Set Temperature Zone1 Master",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  
        "offset": 0,
        "description": "Room air set temperature of Zone1(Master) - Set by Master Remote controller"
    },
    12: {
        "name": "Room Air Set Temperature Zone2 Slave",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  
        "offset": 0,
        "description": "Room air set temperature of Zone2(Slave) - Set by Slave Remote controller"
    },
    13: {
        "name": "Selected DHW Operating Mode",
        "unit": None,
        "device_class": None,
        "state_class": None,
        "scale": 1,
        "offset": 0,
        "description": "Selected DHW operating mode (0=disable, 1=Comfort, 2=Economy, 3=Force)"
    },
    14: {
        "name": "Day of Week",
        "unit": None,
        "device_class": None,
        "state_class": None,
        "scale": 1,
        "offset": 0,
        "description": "Day (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday)"
    },
    15: {
        "name": "Legionella Cycle Set Time",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": None,
        "scale": 1,  # 1min scale
        "offset": 0,
        "description": "Legionella Cycle Set Time (default 12:00)"
    },
    16: {
        "name": "DHW Tank Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1, 
        "offset": 0,
        "description": "DHW tank temperature (Terminal 7-8)"
    },
    17: {
        "name": "Outdoor Air Temperature Additional",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  
        "offset": 0,
        "description": "Outdoor air temperature (Terminal 9-10) - Additional sensor"
    },
    18: {
        "name": "Buffer Tank Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  
        "offset": 0,
        "description": "Buffer tank temperature (Terminal 11-12)"
    },
    19: {
        "name": "Mix Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 0.1,  
        "offset": 0,
        "description": "Mix water temperature (Terminal 13-14)"
    },
    20: {
        "name": "Humidity Sensor",
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  
        "offset": 0,
        "description": "Humidity sensor (Terminal 17-18)"
    },
    32: {
        "name": "Plate Heat Exchanger Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "scale": 1,  # 1°C scale
        "offset": 0,
        "description": "Plate heat exchanger temperature (monitor display No.d4)"
    }
}

# HOLDING REGISTERS - Configuration parameters (Read/Write) - Based on actual register document
HOLDING_REGISTER_MAP = {
    # Zone 1 Heating Parameters
    2: {
        "name": "Zone 1 Heating Fixed Outgoing Water Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Heating Zone1, Fixed Outgoing water set point in Heating (Default: 45°C)"
    },
    3: {
        "name": "Zone 1 Max Outgoing Water Temperature Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Heating mode (Tm1) Zone1 (Default: 45°C)"
    },
    4: {
        "name": "Zone 1 Min Outgoing Water Temperature Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Heating mode (Tm2) Zone1 (Default: 30°C)"
    },
    5: {
        "name": "Zone 1 Min Outdoor Temperature for Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone1 (Default: 0°C)"
    },
    6: {
        "name": "Zone 1 Max Outdoor Temperature for Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone1 (Default: 20°C)"
    },
    
    # Zone 2 Heating Parameters
    7: {
        "name": "Zone 2 Heating Fixed Outgoing Water Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Heating Zone2, Fixed Outgoing water set point in Heating (Default: 45°C)"
    },
    8: {
        "name": "Zone 2 Max Outgoing Water Temperature Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Heating mode (Tm1) Zone2 (Default: 45°C)"
    },
    9: {
        "name": "Zone 2 Min Outgoing Water Temperature Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Heating mode (Tm2) Zone2 (Default: 30°C)"
    },
    10: {
        "name": "Zone 2 Min Outdoor Temperature for Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone2 (Default: 0°C)"
    },
    11: {
        "name": "Zone 2 Max Outdoor Temperature for Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone2 (Default: 20°C)"
    },
    
    # Zone 1 Cooling Parameters
    12: {
        "name": "Zone 1 Cooling Fixed Outgoing Water Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Cooling Zone1, Fixed Outgoing water set point in Cooling (Default: 7°C)"
    },
    13: {
        "name": "Zone 1 Max Outgoing Water Temperature Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Cooling mode (Tm1) Zone1 (Default: 20°C)"
    },
    14: {
        "name": "Zone 1 Min Outgoing Water Temperature Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Cooling mode (Tm2) Zone1 (Default: 18°C)"
    },
    15: {
        "name": "Zone 1 Min Outdoor Temperature for Cooling Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone1 Cooling (Default: 25°C)"
    },
    16: {
        "name": "Zone 1 Max Outdoor Temperature for Cooling Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone1 Cooling (Default: 35°C)"
    },
    
    # Zone 2 Cooling Parameters
    17: {
        "name": "Zone 2 Cooling Fixed Outgoing Water Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Cooling Zone2, Fixed Outgoing water set point in Cooling (Default: 7°C)"
    },
    18: {
        "name": "Zone 2 Max Outgoing Water Temperature Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outgoing water temperature in Cooling mode (Tm1) Zone2 (Default: 20°C)"
    },
    19: {
        "name": "Zone 2 Min Outgoing Water Temperature Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outgoing water temperature in Cooling mode (Tm2) Zone2 (Default: 18°C)"
    },
    20: {
        "name": "Zone 2 Min Outdoor Temperature for Cooling Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Min. Outdoor air temperature corresponding to max. Outgoing water temperature (Te1) Zone2 Cooling (Default: 25°C)"
    },
    21: {
        "name": "Zone 2 Max Outdoor Temperature for Cooling Max Water Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Max. Outdoor air temperature corresponding to max. Outgoing water temperature (Te2) Zone2 Cooling (Default: 35°C)"
    },
    
    # Hysteresis Settings
    22: {
        "name": "Water Set Point Hysteresis Heating and DHW",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of water set point in Heating and DHW (Default: 8°C)"
    },
    23: {
        "name": "Water Set Point Hysteresis Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Hysteresis of water set point in Cooling (Default: 8°C)"
    },
    
    # Low Tariff Settings
    24: {
        "name": "Low Tariff Differential Water Set Point Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Low tariff differential water set point for Heating (Default: 5°C)"
    },
    25: {
        "name": "Low Tariff Differential Water Set Point Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Low tariff differential water set point for Cooling (Default: 5°C)"
    },
    
    # DHW Settings
    26: {
        "name": "DHW Production Priority Setting",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "DHW production priority setting (0=unavailable, 1=priority over heating, 2=heating priority) (Default: 0)"
    },
    27: {
        "name": "DHW Configuration Type",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Type of configuration to heat the DHW (0=HP+Heater, 1=HP only, 2=Heater only) (Default: 1)"
    },
    28: {
        "name": "DHW Comfort Set Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW Comfort set temperature (Default: 50°C)"
    },
    29: {
        "name": "DHW Economy Set Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW Economy set temperature (Default: 40°C)"
    },
    30: {
        "name": "DHW Set Point Hysteresis",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW set point hysteresis (Default: 3°C)"
    },
    31: {
        "name": "DHW Over Boost Mode Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "DHW Over boost mode set point (Default: 60°C)"
    },
    32: {
        "name": "Max Time for DHW Request",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Max. time for DHW request (Default: 60 minutes)"
    },
    33: {
        "name": "DHW Heater Delay Time from OFF Compressor",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time on DHW heater from OFF compressor (Default: 30 minutes)"
    },
    34: {
        "name": "Outdoor Temperature to Enable DHW Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable DHW heaters (Default: -5°C)"
    },
    35: {
        "name": "Outdoor Temperature Hysteresis to Disable DHW Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable DHW heaters (Default: 5°C)"
    },
    36: {
        "name": "Anti-Legionella Set Point",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Anti-legionella set point"
    },
    
    # Night Mode and Compressor Settings
    37: {
        "name": "Max Frequency of Night Mode",
        "unit": PERCENTAGE,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Max. frequency of Night mode (Default: 80%, scale: 5%)"
    },
    38: {
        "name": "Min Time Compressor ON/OFF",
        "unit": UnitOfTime.SECONDS,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Min. time compressor ON/OFF time (Default: 0 seconds)"
    },
    39: {
        "name": "Delay Time Pump OFF from Compressor OFF",
        "unit": UnitOfTime.SECONDS,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time pump OFF from compressor OFF (Default: 30 seconds)"
    },
    40: {
        "name": "Delay Time Compressor ON from Pump ON",
        "unit": UnitOfTime.SECONDS,
        "device_class": SensorDeviceClass.DURATION,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Delay time compressor ON from pump ON (Default: 30 seconds)"
    },
    
    # Water Pump Configuration
    41: {
        "name": "Main Water Pump Configuration Type",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Type of configuration of Main water pump (0=always ON, 1=ON/OFF based on Buffer tank temp, 2=ON/OFF based on Sniffing cycles) (Default: 0)"
    },
    
    # Continue with more registers from the document...
    # Backup Heater Settings
    71: {
        "name": "Backup Heater Type of Function",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Backup heater type of function (0=disable, 1=Replacement mode, 2=Emergency mode, 3=Supplementary mode) (Default: 0)"
    },
    77: {
        "name": "Outdoor Temperature to Enable Backup Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature to enable Backup heaters and disable compressor (Default: -5°C)"
    },
    78: {
        "name": "Outdoor Temperature Hysteresis to Disable Backup Heaters",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Outdoor air temperature hysteresis to disable Backup heaters and enable compressor (Default: 5°C)"
    },
    81: {
        "name": "Freeze Protection Functions",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Freeze protection functions (0=disable, 1=enabled during Start-up, 2=enabled during Defrost, 3=enabled during Start-up and Defrost) (Default: 0)"
    },
    84: {
        "name": "EHS Type Of Function",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "EHS type of function (0=disable, 1=Replacement mode, 2=Supplementary mode) (Default: 0)"
    },
    
    # Terminal Configuration
    91: {
        "name": "Terminal 20-21 ON/OFF Remote Contact",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 20-21 : ON/OFF remote contact or EHS Alarm input (0=disable, 1=ON/OFF remote contact, 2=EHS Alarm input) (Default: 0)"
    },
    92: {
        "name": "Terminal 24-25 Heating/Cooling Mode Remote Contact",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 24-25 : Heating/Cooling mode remote contact (0=disable, 1=Cooling is CLOSE/Heating is OPEN, 2=Cooling is OPEN/Heating is CLOSE) (Default: 0)"
    },
    93: {
        "name": "Terminal 47 Alarm Configurable Output",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 47 : Alarm (Configurable output) (0=disable, 1=Alarm, 2=Ambient temperature reached) (Default: 0)"
    },
    94: {
        "name": "Terminal 48 Pump1",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 48 : Pump1 (0=disable, 1=1st Additional water pump1 for Zone1) (Default: 0)"
    },
    95: {
        "name": "Terminal 49 Pump2",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 49 : Pump2 (0=disable, 1=2nd Additional water pump2 for Zone2) (Default: 0)"
    },
    96: {
        "name": "Terminal 50-51-52 DHW 3way Valve",
        "unit": None,
        "device_class": None,
        "scale": 1,
        "offset": 0,
        "writable": True,
        "description": "Terminal 50-51-52 : DHW 3way valve (1=enable) (Default: 1)"
    },
    
    # Buffer Tank Settings
    99: {
        "name": "Buffer Tank Set Point for Heating",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Buffer tank set point for Heating (Default: 45°C)"
    },
    100: {
        "name": "Buffer Tank Set Point for Cooling",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "scale": 0.1,
        "offset": 0,
        "writable": True,
        "description": "Buffer tank set point for Cooling (Default: 7°C)"
    }
}
        "description": "Buffer tank temperature setpoint"
    }
}

# COIL REGISTERS - Binary status/control (Read/Write)
COIL_REGISTER_MAP = {
    0: {
        "name": "System Enable",
        "description": "Master system enable/disable"
    },
    1: {
        "name": "Heating Enable",
        "description": "Heating function enable/disable"
    },
    2: {
        "name": "Cooling Enable", 
        "description": "Cooling function enable/disable"
    },
    3: {
        "name": "DHW Enable",
        "description": "DHW heating enable/disable"
    },
    4: {
        "name": "Weather Compensation Enable",
        "description": "Weather compensation enable/disable"
    },
    5: {
        "name": "Eco Mode Enable",
        "description": "Eco mode enable/disable"
    },
    6: {
        "name": "Boost Mode Enable",
        "description": "Boost mode enable/disable"
    },
    7: {
        "name": "Holiday Mode Enable",
        "description": "Holiday mode enable/disable"
    },
    8: {
        "name": "Quiet Mode Enable",
        "description": "Quiet mode enable/disable"
    },
    9: {
        "name": "Frost Protection Enable",
        "description": "Frost protection enable/disable"
    }
}

# UK specific constants
UK_ELECTRICITY_RATES = {
    "standard": 0.30,  # £0.30 per kWh typical standard rate
    "economy7_day": 0.32,  # £0.32 per kWh day rate
    "economy7_night": 0.15,  # £0.15 per kWh night rate
    "octopus_agile_avg": 0.25,  # £0.25 per kWh average agile rate
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "cop_excellent": 4.0,
    "cop_good": 3.0,
    "cop_fair": 2.0,
    "cop_poor": 1.0,
    "efficiency_high": 85.0,  # %
    "efficiency_medium": 70.0,  # %
    "efficiency_low": 50.0,  # %
    "power_high_threshold": 6000,  # W
    "temp_differential_normal": 5.0,  # °C
}

# Weather compensation defaults
WEATHER_COMP_DEFAULTS = {
    "base_flow_temp": 35.0,  # °C
    "indoor_target": 21.0,  # °C
    "curve_factor": 1.5,
    "max_flow_temp": 55.0,  # °C
    "min_flow_temp": 25.0,  # °C
}

# System limits
SYSTEM_LIMITS = {
    "min_room_temp": 15.0,  # °C
    "max_room_temp": 25.0,  # °C
    "min_dhw_temp": 40.0,  # °C
    "max_dhw_temp": 65.0,  # °C
    "min_flow_temp": 20.0,  # °C
    "max_flow_temp": 65.0,  # °C
    "max_power": 8000,  # W
    "scan_interval_min": 10,  # seconds
    "scan_interval_max": 300,  # seconds
}