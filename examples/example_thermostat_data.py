#%%
"""
Example script demonstrating the use of LoadModel.get_thermostat_data()

This script shows how to extract thermostat metadata from building models
using the object-oriented approach provided by LoadModel.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from semantic_mpc_interface import LoadModel, get_thermostat_data
import json

def main():
    # Load a building model
    model_path = '../tutorial/test_site/test_build/test_build.ttl'
    
    print("Loading building model...")
    loader = LoadModel(model_path, 'brick')
    
    # Get thermostat data for all zones
    print("\n=== Getting thermostat data for all zones ===")
    thermostat_data = get_thermostat_data(loader)
    
    print(f"Found {len(thermostat_data['zone_ids'])} thermostats")
    print(f"Zone IDs: {thermostat_data['zone_ids']}")
    
    # Display key thermostat properties
    for i, zone_id in enumerate(thermostat_data['zone_ids']):
        print(f"\nThermostat {i+1} (Zone: {zone_id}):")
        print(f"  Heat tolerance: {thermostat_data['heat_tolerance'][i]}°")
        print(f"  Cool tolerance: {thermostat_data['cool_tolerance'][i]}°")
        print(f"  Setpoint deadband: {thermostat_data['setpoint_deadband'][i]}°")
        print(f"  Control type: {thermostat_data['control_type_list'][i]}")
        print(f"  Floor area: {thermostat_data['floor_area_list'][i]} {thermostat_data['floor_area_unit'][i]}")
        print(f"  Window area: {thermostat_data['window_area_list'][i]} {thermostat_data['window_area_unit'][i]}")
        print(f"  HVAC unit: {thermostat_data['hvacs'][i]}")
        print(f"  Cooling capacity: {thermostat_data['cooling_capacity'][i]} {thermostat_data['cooling_capacity_unit'][i]}")
        print(f"  Heating capacity: {thermostat_data['heating_capacity'][i]} {thermostat_data['heating_capacity_unit'][i]}")
        print(f"  Fuel type (heat/cool): {thermostat_data['fuel_heat_list'][i]}/{thermostat_data['fuel_cool_list'][i]}")
    
    # Filter by specific zones
    print("\n=== Filtering by specific zones ===")
    filtered_data = get_thermostat_data(loader, for_zone_list=['zone_2', 'zone_3'])
    print(f"Filtered to zones: {filtered_data['zone_ids']}")
    print(f"Floor areas: {filtered_data['floor_area_list']}")
    
    # Export to JSON for further processing
    print("\n=== Exporting to JSON ===")
    output_file = 'thermostat_metadata.json'
    with open(output_file, 'w') as f:
        json.dump(thermostat_data, f, indent=2)
    print(f"Thermostat data exported to {output_file}")

    return loader, thermostat_data

if __name__ == "__main__":
    loader, thermostat_data = main()

# %%
