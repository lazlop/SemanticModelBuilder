"""
Tests for the conversion module.
"""

import pytest

from semantic_mpc_interface.conversion import (
    UnitConverter,
    convert_value,
    get_unit_string,
)


class TestConversion:
    """Test cases for unit conversion functions."""

    def test_temperature_conversion_si_to_ip(self):
        """Test temperature conversion from SI to IP."""
        result = convert_value(0, "temperature", "SI", "IP")
        assert result == 32.0  # 0°C = 32°F

        result = convert_value(100, "temperature", "SI", "IP")
        assert result == 212.0  # 100°C = 212°F

    def test_temperature_conversion_ip_to_si(self):
        """Test temperature conversion from IP to SI."""
        result = convert_value(32, "temperature", "IP", "SI")
        assert result == 0.0  # 32°F = 0°C

        result = convert_value(212, "temperature", "IP", "SI")
        assert result == 100.0  # 212°F = 100°C

    def test_area_conversion_si_to_ip(self):
        """Test area conversion from SI to IP."""
        result = convert_value(1, "area", "SI", "IP")
        assert abs(result - 10.764) < 0.001  # 1 m² ≈ 10.764 ft²

    def test_same_system_conversion(self):
        """Test that same system conversion returns original value."""
        result = convert_value(100, "temperature", "SI", "SI")
        assert result == 100

    def test_invalid_quantity_type(self):
        """Test that invalid quantity type raises ValueError."""
        with pytest.raises(ValueError, match="Conversion not supported"):
            convert_value(100, "invalid_type", "SI", "IP")

    def test_invalid_unit_systems(self):
        """Test that invalid unit systems raise ValueError."""
        with pytest.raises(ValueError, match="Invalid unit systems"):
            convert_value(100, "temperature", "INVALID", "SI")

    def test_get_unit_string_si(self):
        """Test getting unit strings for SI system."""
        assert get_unit_string("temperature", "SI") == "DEG_C"
        assert get_unit_string("area", "SI") == "M2"
        assert get_unit_string("power", "SI") == "KiloW"

    def test_get_unit_string_ip(self):
        """Test getting unit strings for IP system."""
        assert get_unit_string("temperature", "IP") == "DEG_F"
        assert get_unit_string("area", "IP") == "FT2"
        assert get_unit_string("power", "IP") == "BTU_IT-PER-HR"

    def test_get_unit_string_invalid_system(self):
        """Test that invalid system raises ValueError."""
        with pytest.raises(ValueError, match="Unknown unit system"):
            get_unit_string("temperature", "INVALID")

    def test_get_unit_string_invalid_quantity(self):
        """Test that invalid quantity type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown quantity type"):
            get_unit_string("invalid", "SI")


class TestUnitConverter:
    """Test cases for UnitConverter class."""

    def test_init_default_system(self):
        """Test initialization with default system."""
        converter = UnitConverter()
        assert converter.default_system == "SI"

    def test_init_custom_system(self):
        """Test initialization with custom system."""
        converter = UnitConverter("IP")
        assert converter.default_system == "IP"

    def test_convert_building_data(self):
        """Test converting building data between systems."""
        converter = UnitConverter("SI")

        data = {
            "temperature": {"value": 20.0, "type": "temperature"},
            "area": {"value": 100.0, "type": "area"},
            "name": "Test Building",  # Non-convertible data
        }

        converted = converter.convert_building_data(data, "IP")

        # Check temperature conversion (20°C = 68°F)
        assert abs(converted["temperature"]["value"] - 68.0) < 0.1
        assert converted["temperature"]["unit"] == "DEG_F"

        # Check area conversion
        assert converted["area"]["unit"] == "FT2"

        # Check non-convertible data is preserved
        assert converted["name"] == "Test Building"
