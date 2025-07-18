"""
Unit conversion utilities for semantic building models.

This module provides functions for converting between different
unit systems and handling unit-aware calculations.
"""

import math
from typing import Dict, Optional, Union

# Conversion factors from SI to IP units
SI_TO_IP_FACTORS = {
    "temperature": lambda c: c * 9 / 5 + 32,  # Celsius to Fahrenheit
    "area": 10.764,  # m² to ft²
    "power": 3412.14,  # kW to BTU/hr
    "pressure": 0.000145038,  # Pa to PSI
    "flow_rate": 2118.88,  # m³/s to CFM
    "length": 3.28084,  # m to ft
    "volume": 35.3147,  # m³ to ft³
}

# Conversion factors from IP to SI units
IP_TO_SI_FACTORS = {
    "temperature": lambda f: (f - 32) * 5 / 9,  # Fahrenheit to Celsius
    "area": 1 / 10.764,  # ft² to m²
    "power": 1 / 3412.14,  # BTU/hr to kW
    "pressure": 1 / 0.000145038,  # PSI to Pa
    "flow_rate": 1 / 2118.88,  # CFM to m³/s
    "length": 1 / 3.28084,  # ft to m
    "volume": 1 / 35.3147,  # ft³ to m³
}


def convert_value(
    value: float, quantity_type: str, from_system: str, to_system: str
) -> float:
    """
    Convert a value between unit systems.

    Args:
        value: Value to convert
        quantity_type: Type of quantity (temperature, area, power, etc.)
        from_system: Source unit system ('SI' or 'IP')
        to_system: Target unit system ('SI' or 'IP')

    Returns:
        Converted value

    Raises:
        ValueError: If conversion is not supported
    """
    if from_system == to_system:
        return value

    if quantity_type not in SI_TO_IP_FACTORS:
        raise ValueError(f"Conversion not supported for quantity type: {quantity_type}")

    if from_system == "SI" and to_system == "IP":
        factor = SI_TO_IP_FACTORS[quantity_type]
        if callable(factor):
            return factor(value)
        else:
            return value * factor

    elif from_system == "IP" and to_system == "SI":
        factor = IP_TO_SI_FACTORS[quantity_type]
        if callable(factor):
            return factor(value)
        else:
            return value * factor

    else:
        raise ValueError(f"Invalid unit systems: {from_system} to {to_system}")


def get_unit_string(quantity_type: str, system: str) -> str:
    """
    Get the unit string for a quantity type and system.

    Args:
        quantity_type: Type of quantity
        system: Unit system ('SI' or 'IP')

    Returns:
        Unit string for use with QUDT
    """
    unit_mappings = {
        "SI": {
            "temperature": "DEG_C",
            "area": "M2",
            "power": "KiloW",
            "pressure": "PA",
            "flow_rate": "M3-PER-SEC",
            "length": "M",
            "volume": "M3",
        },
        "IP": {
            "temperature": "DEG_F",
            "area": "FT2",
            "power": "BTU_IT-PER-HR",
            "pressure": "PSI",
            "flow_rate": "FT3-PER-MIN",
            "length": "FT",
            "volume": "FT3",
        },
    }

    if system not in unit_mappings:
        raise ValueError(f"Unknown unit system: {system}")

    if quantity_type not in unit_mappings[system]:
        raise ValueError(f"Unknown quantity type: {quantity_type}")

    return unit_mappings[system][quantity_type]


class UnitConverter:
    """Class for handling unit conversions in building models."""

    def __init__(self, default_system: str = "SI"):
        """
        Initialize the unit converter.

        Args:
            default_system: Default unit system to use
        """
        self.default_system = default_system

    def convert_building_data(
        self, data: Dict[str, Union[float, Dict]], target_system: str
    ) -> Dict[str, Union[float, Dict]]:
        """
        Convert building data between unit systems.

        Args:
            data: Building data dictionary
            target_system: Target unit system

        Returns:
            Converted data dictionary
        """
        converted_data = {}

        for key, value in data.items():
            if isinstance(value, dict) and "value" in value and "type" in value:
                # Handle structured data with type information
                converted_value = convert_value(
                    value["value"], value["type"], self.default_system, target_system
                )
                converted_data[key] = {
                    "value": converted_value,
                    "type": value["type"],
                    "unit": get_unit_string(value["type"], target_system),
                }
            else:
                # Pass through non-convertible data
                converted_data[key] = value

        return converted_data
