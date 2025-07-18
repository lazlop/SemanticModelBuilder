#!/usr/bin/env python3
"""
Unit Conversion Example

This example demonstrates unit conversion capabilities
between SI and Imperial unit systems.
"""

from semantic_mpc_interface.conversion import (
    convert_value,
    get_unit_string,
    UnitConverter
)


def demonstrate_basic_conversions():
    """Demonstrate basic unit conversions."""
    
    print("=== Basic Unit Conversions ===\n")
    
    # Temperature conversions
    print("Temperature Conversions:")
    temps_c = [0, 20, 25, 100]
    for temp_c in temps_c:
        temp_f = convert_value(temp_c, "temperature", "SI", "IP")
        print(f"  {temp_c}°C = {temp_f:.1f}°F")
    
    print()
    
    # Area conversions
    print("Area Conversions:")
    areas_m2 = [1, 10, 100, 1000]
    for area_m2 in areas_m2:
        area_ft2 = convert_value(area_m2, "area", "SI", "IP")
        print(f"  {area_m2} m² = {area_ft2:.1f} ft²")
    
    print()
    
    # Power conversions
    print("Power Conversions:")
    powers_kw = [1, 5, 10, 50]
    for power_kw in powers_kw:
        power_btu = convert_value(power_kw, "power", "SI", "IP")
        print(f"  {power_kw} kW = {power_btu:.0f} BTU/hr")


def demonstrate_unit_strings():
    """Demonstrate getting unit strings for different systems."""
    
    print("\n=== Unit String Mappings ===\n")
    
    quantities = ["temperature", "area", "power", "pressure", "flow_rate"]
    
    print("SI Units:")
    for qty in quantities:
        unit = get_unit_string(qty, "SI")
        print(f"  {qty}: {unit}")
    
    print("\nIP Units:")
    for qty in quantities:
        unit = get_unit_string(qty, "IP")
        print(f"  {qty}: {unit}")


def demonstrate_building_data_conversion():
    """Demonstrate converting structured building data."""
    
    print("\n=== Building Data Conversion ===\n")
    
    # Sample building data in SI units
    building_data_si = {
        "site_name": "Example Building",
        "floor_area": {
            "value": 1000.0,
            "type": "area"
        },
        "design_temperature": {
            "value": 22.0,
            "type": "temperature"
        },
        "hvac_capacity": {
            "value": 50.0,
            "type": "power"
        },
        "location": {
            "latitude": 40.7128,
            "longitude": -74.0060
        }
    }
    
    print("Original Data (SI):")
    for key, value in building_data_si.items():
        if isinstance(value, dict) and "value" in value:
            print(f"  {key}: {value['value']} ({value['type']})")
        else:
            print(f"  {key}: {value}")
    
    # Convert to IP units
    converter = UnitConverter("SI")
    building_data_ip = converter.convert_building_data(building_data_si, "IP")
    
    print("\nConverted Data (IP):")
    for key, value in building_data_ip.items():
        if isinstance(value, dict) and "value" in value:
            unit = value.get("unit", "")
            print(f"  {key}: {value['value']:.1f} {unit}")
        else:
            print(f"  {key}: {value}")


def demonstrate_reverse_conversion():
    """Demonstrate round-trip conversions."""
    
    print("\n=== Round-trip Conversion Test ===\n")
    
    original_values = {
        "temperature": 25.0,  # °C
        "area": 100.0,       # m²
        "power": 10.0,       # kW
    }
    
    print("Round-trip Conversion Test:")
    for qty_type, original in original_values.items():
        # Convert SI -> IP -> SI
        converted_ip = convert_value(original, qty_type, "SI", "IP")
        back_to_si = convert_value(converted_ip, qty_type, "IP", "SI")
        
        print(f"  {qty_type}:")
        print(f"    Original (SI): {original}")
        print(f"    Converted (IP): {converted_ip:.3f}")
        print(f"    Back to SI: {back_to_si:.3f}")
        print(f"    Difference: {abs(original - back_to_si):.6f}")


if __name__ == "__main__":
    demonstrate_basic_conversions()
    demonstrate_unit_strings()
    demonstrate_building_data_conversion()
    demonstrate_reverse_conversion()