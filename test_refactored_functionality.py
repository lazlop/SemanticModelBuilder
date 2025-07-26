#!/usr/bin/env python3
"""
Test script to demonstrate the refactored CSV prefilling functionality
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from semantic_mpc_interface.create_metadata_survey import SurveyGenerator, BuildingStructureGenerator

def test_general_survey_generator():
    """Test the general SurveyGenerator class"""
    print("=== Testing General SurveyGenerator ===")
    
    # Create a general survey with custom templates
    generator = SurveyGenerator(
        site_id="general_site",
        building_id="test_building",
        output_dir="general_survey_output",
        ontology='brick',
        template_dict={"space":"space", "window":"window"},  # Only specific templates
        overwrite=True
    )
    
    print(f"Generated general survey CSVs in: {generator.base_dir}")
    print(f"Template CSVs created: {list(generator.template_csvs.keys())}")
    
    return generator

def test_building_structure_generator():
    """Test the specialized BuildingStructureGenerator class"""
    print("\n=== Testing BuildingStructureGenerator ===")
    
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
    
    # Create building structure generator
    generator = BuildingStructureGenerator(
        site_id=config['site_id'],
        building_id="test_building",
        output_dir="building_structure_output",
        system_of_units="IP",
        ontology='brick',
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
    
    print(f"Generated building structure CSVs in: {generator.base_dir}")
    print(f"Template CSVs created: {list(generator.template_csvs.keys())}")
    
    return generator

def test_easy_config():
    """Test the easy_config method"""
    print("\n=== Testing Easy Config Method ===")
    
    generator = BuildingStructureGenerator(
        site_id="easy_config_site",
        building_id="test_building",
        output_dir="easy_config_output",
        system_of_units="SI",  # Test with metric units
        ontology='brick',
        overwrite=True
    )
    
    # Define building structure: 3 zones with different numbers of spaces and windows
    zone_space_window_list = [
        (2, 2),  # zone_1: 2 spaces, 2 windows
        (1, 2),  # zone_2: 1 space, 2 windows  
        (1, 3)   # zone_3: 1 space, 3 windows
    ]
    
    generator.easy_config(zone_space_window_list)
    print(f"Generated easy config CSVs in: {generator.base_dir}")
    
    return generator

def display_csv_contents(generator, title):
    """Display contents of generated CSV files"""
    print(f"\n{title}")
    print("="*50)
    
    for csv_name, csv_path in generator.template_csvs.items():
        print(f"\n{csv_name.upper()}.CSV:")
        print("-" * 30)
        try:
            with open(csv_path, 'r') as f:
                print(f.read())
        except Exception as e:
            print(f"Error reading {csv_path}: {e}")

def main():
    """Main test function"""
    print("Testing Refactored CSV Prefilling Functionality")
    print("=" * 60)
    
    # Test 1: General SurveyGenerator
    general_generator = test_general_survey_generator()
    
    # Test 2: BuildingStructureGenerator with manual config
    building_generator = test_building_structure_generator()
    
    # Test 3: Easy config method
    easy_generator = test_easy_config()
    
    # Display results
    display_csv_contents(building_generator, "BUILDING STRUCTURE GENERATOR RESULTS (IP Units)")
    display_csv_contents(easy_generator, "EASY CONFIG GENERATOR RESULTS (SI Units)")
    
    print("\n" + "="*60)
    print("SUMMARY OF REFACTORING:")
    print("• SurveyGenerator: General class for any template-based CSV generation")
    print("• BuildingStructureGenerator: Specialized for building systems (HVAC, zones, spaces, windows)")
    print("• System-specific defaults (units, HVAC types) moved to specialized class")
    print("• Prefilling functionality isolated to building-specific class")
    print("• Both classes maintain clean separation of concerns")

if __name__ == "__main__":
    main()
