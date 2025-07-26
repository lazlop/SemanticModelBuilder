#!/usr/bin/env python3
"""
Test script to demonstrate the CSV prefilling functionality
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from semantic_mpc_interface.create_metadata_survey import SurveyGenerator

def test_prefill_functionality():
    """Test the CSV prefilling functionality with the provided config"""
    
    # Configuration from the user's request
    config = {
        'site_id': 'test_site', 
        'hvac_type': 'hp-rtu', 
        'hvacs_feed_hvacs': {}, 
        'hvacs_feed_zones': {
            'hvac_1': ['zone_1'], 
            'hvac_2': ['zone_2'], 
            'hvac_3': ['zone_3']
        }, 
        'zones_contain_spaces': {
            'zone_1': ['space_1_1', 'space_1_2'], 
            'zone_2': ['space_2_1'], 
            'zone_3': ['space_3_1']
        }, 
        'zones_contain_windows': {
            'zone_1': ['window_1_1', 'window_1_2'], 
            'zone_2': ['window_2_1', 'window_2_2'], 
            'zone_3': ['window_3_1', 'window_3_2', 'window_3_3']
        }
    }
    
    # Create output directory
    output_dir = "test_prefill_output"
    
    # Initialize SurveyGenerator
    print("Creating SurveyGenerator...")
    generator = SurveyGenerator(
        site_id=config['site_id'],
        building_id="test_building",
        output_dir=output_dir,
        system_of_units="IP",
        ontology='brick',
        hvac_type=config['hvac_type'],
        template_list=["space", "hp-rtu", "tstat", "window"],
        overwrite=True
    )
    
    # Use the _building_structure method to create and prefill CSVs
    print("Creating building structure and prefilling CSVs...")
    generator._building_structure(
        config['hvacs_feed_hvacs'],
        config['hvacs_feed_zones'],
        config['zones_contain_spaces'],
        config['zones_contain_windows']
    )
    
    print(f"\nCSV files have been created and prefilled in: {generator.base_dir}")
    print("\nGenerated files:")
    for file_path in generator.base_dir.glob("*.csv"):
        print(f"  - {file_path.name}")
    
    # Display contents of generated CSV files
    print("\n" + "="*50)
    print("CONTENTS OF GENERATED CSV FILES:")
    print("="*50)
    
    for csv_name, csv_path in generator.template_csvs.items():
        print(f"\n{csv_name.upper()}.CSV:")
        print("-" * 30)
        try:
            with open(csv_path, 'r') as f:
                print(f.read())
        except Exception as e:
            print(f"Error reading {csv_path}: {e}")

if __name__ == "__main__":
    test_prefill_functionality()
