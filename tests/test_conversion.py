"""
Tests for the unit conversion functionality.
"""

import pytest

from semantic_mpc_interface import convert_units


class TestUnitConversion:
    """Test cases for unit conversion functions."""

    def test_temperature_conversion_celsius_to_fahrenheit(self):
        """Test temperature conversion from Celsius to Fahrenheit."""
        result = convert_units(0, "DEG_C", "DEG_F")
        assert abs(result - 32.0) < 0.001  # 0°C = 32°F

        result = convert_units(100, "DEG_C", "DEG_F")
        assert abs(result - 212.0) < 0.001  # 100°C = 212°F

    def test_temperature_conversion_fahrenheit_to_celsius(self):
        """Test temperature conversion from Fahrenheit to Celsius."""
        result = convert_units(32, "DEG_F", "DEG_C")
        assert abs(result - 0.0) < 0.001  # 32°F = 0°C

        result = convert_units(212, "DEG_F", "DEG_C")
        assert abs(result - 100.0) < 0.001  # 212°F = 100°C

    def test_temperature_conversion_celsius_to_kelvin(self):
        """Test temperature conversion from Celsius to Kelvin."""
        result = convert_units(0, "DEG_C", "K")
        assert abs(result - 273.15) < 0.01  # 0°C = 273.15K

    def test_length_conversion_feet_to_meters(self):
        """Test length conversion from feet to meters."""
        result = convert_units(10, "FT", "M")
        assert abs(result - 3.048) < 0.001  # 10 ft ≈ 3.048 m

    def test_same_unit_conversion(self):
        """Test that same unit conversion returns original value."""
        result = convert_units(100, "DEG_C", "DEG_C")
        assert result == 100

        result = convert_units(50, "M", "M")
        assert result == 50

    def test_delta_quantity_conversion(self):
        """Test delta quantity conversion (temperature differences)."""
        # Temperature difference should not include offset
        result = convert_units(10, "DEG_C", "DEG_F", is_delta_quantity=True)
        assert abs(result - 18.0) < 0.001  # 10°C difference = 18°F difference

    def test_invalid_unit_conversion(self):
        """Test that invalid unit conversion raises appropriate error."""
        with pytest.raises(ValueError):
            convert_units(100, "INVALID_UNIT", "DEG_C")

    def test_area_conversion(self):
        """Test area conversion."""
        result = convert_units(1, "M2", "FT2")
        # 1 m² ≈ 10.764 ft²
        assert abs(result - 10.764) < 0.1
