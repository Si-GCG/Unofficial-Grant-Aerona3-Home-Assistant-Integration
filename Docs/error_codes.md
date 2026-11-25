# Error Codes

The heat pump keeps a history of its error codes, shown on the Terminal PCB display as codes like `LC` or `E4`. The integration reads them from input registers 21-31 and shows them as sensors (for example `sensor.ashp_current_error_code` reads `LC`, or `No error`).

| Register | Sensor | Contents |
|---|---|---|
| 21 | Current Error Code | The active error |
| 22 | Previous Error Code 1 | The most recent earlier error |
| 23-31 | Previous Error Code 2-10 | Older errors, newest first |

The **Alarm Status** binary sensor is on whenever register 21 holds an error. Its attributes give the code and a description.

## How the codes are stored

The manufacturer doesn't document the register format, so this was worked out from captured values and the installer manuals:

- `32381` (`0x7E7D`) means an empty slot, which the Terminal PCB shows as `--`.
- Anything else has bit 15 set, and the low 12 bits are the letter number times 16 plus the digit. The second character is read as a hex digit, so `LC` is `0xEC`. Letters are numbered from 10 in the order `A C E F L P U`, which are the only letters the manuals use.

The `L` codes are **confirmed**: a real `LC` alarm reads `0x80EC`, and a unit that had logged `L1` to `L5` read `0x80E1` to `0x80E5`. The other letters follow the same pattern but have not been seen on a real unit, so they are **inferred**. The sensor's `decoding_confirmed` attribute says which applies. If a code shown on your heat pump's display doesn't match what the sensor reports, please open an issue with the register value from the sensor's `raw_value` attribute.

## Code list

Names are from the Grant Aerona R32 installer manual and the Chofu installation manual (section 11, Fault Finding).

| Code | Meaning | Register value | Decoding |
|---|---|---|---|
| A0 | DC voltage error | `0x80A0` (32928) | Inferred |
| A1 | Discharge temperature error | `0x80A1` (32929) | Inferred |
| A2 | Protective action against excess DC current | `0x80A2` (32930) | Inferred |
| A3 | CT disconnection | `0x80A3` (32931) | Inferred |
| A4 | Protective action against excess AC current | `0x80A4` (32932) | Inferred |
| A5 | Abnormal compressor revolution | `0x80A5` (32933) | Inferred |
| A6 | Suction temperature sensor error | `0x80A6` (32934) | Inferred |
| A7 | Defrost temperature sensor error | `0x80A7` (32935) | Inferred |
| A8 | Discharge temperature sensor error | `0x80A8` (32936) | Inferred |
| C1 | Upper fan motor error | `0x80B1` (32945) | Inferred |
| C2 | Outdoor temperature sensor error | `0x80B2` (32946) | Inferred |
| C3 | Lower fan motor error | `0x80B3` (32947) | Inferred |
| C4 | Main PCB temperature rise (above 110 degC) | `0x80B4` (32948) | Inferred |
| C5 | Main PCB sensor error | `0x80B5` (32949) | Inferred |
| C6 | Main PCB error | `0x80B6` (32950) | Inferred |
| C7 | Controller PCB serial error | `0x80B7` (32951) | Inferred |
| C8 | Main PCB error | `0x80B8` (32952) | Inferred |
| E4 | Outgoing water temperature sensor error | `0x80C4` (32964) | Inferred |
| E5 | Return water temperature sensor error | `0x80C5` (32965) | Inferred |
| E8 | Remote controller communication error | `0x80C8` (32968) | Inferred |
| F5 | Main PCB communication error | `0x80D5` (32981) | Inferred |
| L0 | EEPROM error | `0x80E0` (32992) | Confirmed |
| L1 | DHW temperature sensor error | `0x80E1` (32993) | Confirmed |
| L2 | Outdoor temperature sensor error (terminal PCB) | `0x80E2` (32994) | Confirmed |
| L3 | Thermal store temperature sensor error | `0x80E3` (32995) | Confirmed |
| L4 | Mix water temperature sensor error | `0x80E4` (32996) | Confirmed |
| L5 | Humidity sensor error | `0x80E5` (32997) | Confirmed |
| L7 | Mixing valve error | `0x80E7` (32999) | Confirmed |
| L8 | Master remote controller room temperature sensor error | `0x80E8` (33000) | Confirmed |
| L9 | Slave remote controller room temperature sensor error | `0x80E9` (33001) | Confirmed |
| LC | Anti-legionella function not completed | `0x80EC` (33004) | Confirmed |
| P1 | Pump error | `0x80F1` (33009) | Inferred |
| P3 | High pressure switch error | `0x80F3` (33011) | Inferred |
| U1 | Compressor overheat protection relay | `0x8101` (33025) | Inferred |

## LC: anti-legionella function not completed

The anti-legionella cycle ends after 2 hours even if the tank hasn't held the target temperature for 10 minutes. If that happens repeatedly the heat pump raises `LC`. The Chofu manual lists three causes:

- Hot water was used during the anti-legionella cycle. Restart the operation and avoid using much hot water during it.
- A clogged pump or water circuit. Check the pump and circuit, clean the water filter and unblock the pump.
- A heat source setting failure. Check the parameters and the heat source. The DHW electric heater is used to reach the anti-legionella temperature, so it must be available when the function is enabled.

## Clearing an error

Press the `-` and `+` buttons on the remote controller together for 3 seconds, or press Reset SW on the Terminal PCB. To see the stored history on the Terminal PCB, press Pump SW and Reset SW together for 5 seconds. Holding Reset SW for 10 seconds while the error is displayed deletes the history.
