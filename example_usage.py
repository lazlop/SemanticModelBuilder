#!/usr/bin/env python3
"""
Example usage of the CSV prefilling functionality
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from semantic_mpc_interface.create_metadata_survey import SurveyGenerator

def example_usage():
    """Example of how to use the CSV prefilling functionality"""
    
    print("=== CSV Prefilling Functionality Example ===\n")
    
    # Example 1: Using the easy_config method (automatically prefills)
    print("1. Using easy_config method (automatically prefills CSVs):")
    print("-" * 50)
    
    generator1 = SurveyGenerator(
        site_id="example_site",
        building_id="building_1",
        output_dir="example_output",
        system_of_units="IP",
        overwrite=True
    )
    
    # Define building structure: 3 zones with different numbers of spaces and windows
    zone_space_window_list = [
        (2, 2),  # zone_1: 2 spaces, 2 windows
        (1, 2),  # zone_2: 1 space, 2 windows  
        (1, 3)   # zone_3: 1 space, 3 windows
    ]
    
    generator1.easy_config(zone_space_window_list)
    print(f"Generated and prefilled CSVs in: {generator1.base_dir}\n")
    
    # Example 2: Manual configuration and prefilling
    print("2. Manual configuration and prefilling:")
    print("-" * 50)
    
    generator2 = SurveyGenerator(
        site_id="manual_site",
        building_id="building_2", 
        output_dir="manual_output",
        system_of_units="SI",  # Using metric units
        overwrite=True
    )
    
    # Manual configuration
    config = {
        'site_id': 'manual_site',
        'hvac_type': 'hp-rtu',
        'hvacs_feed_hvacs': {},
        'hvacs_feed_zones': {
            'main_hvac': ['north_zone', 'south_zone'],
            'aux_hvac': ['east_zone']
        },
        'zones_contain_spaces': {
            'north_zone': ['office_1', 'office_2', 'conference_room'],
            'south_zone': ['lobby', 'reception'],
            'east_zone': ['storage']
        },
        'zones_contain_windows': {
            'north_zone': ['north_window_1', 'north_window_2'],
            'south_zone': ['south_window_1', 'south_window_2', 'south_window_3'],
            'east_zone': ['east_window_1']
        }
    }
    
    generator2._building_structure(
        config['hvacs_feed_hvacs'],
        config['hvacs_feed_zones'],
        config['zones_contain_spaces'],
        config['zones_contain_windows']
    )
    
    print(f"Generated and prefilled CSVs in: {generator2.base_dir}\n")
    
    # Example 3: Prefilling from existing config file
    print("3. Prefilling from existing config file:")
    print("-" * 50)
    
    # Use the config from the first example
    generator3 = SurveyGenerator(
        site_id="example_site",
        building_id="building_1",
        output_dir="example_output",
        system_of_units="IP",
        overwrite=False  # Don't overwrite, just work with existing
    )
    
    # Prefill from the existing config
    generator3.prefill_from_config()
    
    print("\n=== Summary ===")
    print("The CSV prefilling functionality provides:")
    print("• Automatic population of entity names based on building structure")
    print("• Default unit assignments (IP or SI)")
    print("• Empty value fields ready for user input")
    print("• Support for spaces, windows, HVAC units, and thermostats")
    print("• Ability to re-prefill from saved configuration files")

if __name__ == "__main__":
    example_usage()
