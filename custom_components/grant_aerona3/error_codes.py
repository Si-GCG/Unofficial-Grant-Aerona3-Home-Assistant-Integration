"""Decoding of the heat pump's error history (input registers 21-31).

Register 21 holds the active error and registers 22-31 the previous ten,
newest first. The manufacturer doesn't document how a code is stored, so this
was worked out from captured values and the installer manuals:

* 0x7E7D marks an empty slot (the "--" shown on the Terminal PCB display).
* Otherwise bit 15 is set and the low 12 bits are (letter index * 16 + digit),
  where the second character is read as a hex digit (LC -> 0xC) and the
  letters are numbered from 10 in the order A C E F L P U (the only letters
  the manuals use).

Letter L is confirmed against a real LC alarm and the L1-L5 history of a real
unit. The other letters follow the same pattern but have not been seen, so
they are flagged as inferred.
"""
from __future__ import annotations

from typing import NamedTuple

# Input registers: 21 = active error, 22-31 = previous ten (newest first)
ERROR_REGISTER_IDS = tuple(range(21, 32))

NO_ERROR_STATE = "No error"

EMPTY_SLOT = 0x7E7D
VALID_FLAG = 0x8000
LETTERS = "ACEFLPU"
LETTER_BASE = 10
CONFIRMED_LETTERS = frozenset("L")

# Names from the Grant Aerona R32 installer manual and the Chofu installation manual
ERROR_DESCRIPTIONS = {
    "A0": "DC voltage error",
    "A1": "Discharge temperature error",
    "A2": "Protective action against excess DC current",
    "A3": "CT disconnection",
    "A4": "Protective action against excess AC current",
    "A5": "Abnormal compressor revolution",
    "A6": "Suction temperature sensor error",
    "A7": "Defrost temperature sensor error",
    "A8": "Discharge temperature sensor error",
    "C1": "Upper fan motor error",
    "C2": "Outdoor temperature sensor error",
    "C3": "Lower fan motor error",
    "C4": "Main PCB temperature rise (above 110 degC)",
    "C5": "Main PCB sensor error",
    "C6": "Main PCB error",
    "C7": "Controller PCB serial error",
    "C8": "Main PCB error",
    "E4": "Outgoing water temperature sensor error",
    "E5": "Return water temperature sensor error",
    "E8": "Remote controller communication error",
    "F5": "Main PCB communication error",
    "L0": "EEPROM error",
    "L1": "DHW temperature sensor error",
    "L2": "Outdoor temperature sensor error (terminal PCB)",
    "L3": "Thermal store temperature sensor error",
    "L4": "Mix water temperature sensor error",
    "L5": "Humidity sensor error",
    "L7": "Mixing valve error",
    "L8": "Master remote controller room temperature sensor error",
    "L9": "Slave remote controller room temperature sensor error",
    "LC": "Anti-legionella function not completed",
    "P1": "Pump error",
    "P3": "High pressure switch error",
    "U1": "Compressor overheat protection relay",
}


class ErrorCode(NamedTuple):
    """A decoded error history slot."""

    code: str | None  # e.g. "LC"; None if the value isn't a recognised code
    description: str
    confirmed: bool  # False when decoded by inference rather than a seen value
    raw: int  # unsigned 16-bit register value


def decode_error(register_value: int) -> ErrorCode | None:
    """Decode one error history register; None means the slot is empty."""
    raw = register_value & 0xFFFF
    if raw in (EMPTY_SLOT, 0):
        return None
    if not raw & VALID_FLAG:
        return ErrorCode(None, f"Unrecognised value 0x{raw:04X}", False, raw)

    body = raw & 0x7FFF
    letter_index = (body >> 4) - LETTER_BASE
    if not 0 <= letter_index < len(LETTERS):
        return ErrorCode(None, f"Unrecognised value 0x{raw:04X}", False, raw)

    letter = LETTERS[letter_index]
    code = f"{letter}{body & 0xF:X}"
    return ErrorCode(
        code,
        ERROR_DESCRIPTIONS.get(code, "Error code not listed in the manuals"),
        letter in CONFIRMED_LETTERS,
        raw,
    )


def encode_error(code: str) -> int:
    """Register value for a code such as "LC" (for documentation and tests)."""
    return VALID_FLAG | ((LETTER_BASE + LETTERS.index(code[0])) << 4) | int(code[1], 16)
