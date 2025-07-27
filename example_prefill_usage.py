#!/usr/bin/env python3
"""
Example usage of the prefill_csv_survey function

This script demonstrates how to use the simple prefill function to 
populate CSV survey files based on an existing configuration.
"""

from src.semantic_mpc_interface.create_metadata_survey import prefill_csv_survey
from semantic_mpc_interface import HPFlexSurvey

def main():
    """
    Example of using the prefill_csv_survey function
    """
    print('GENERATING SURVEY')
    s = HPFlexSurvey('test_site','test_build','.', overwrite=True); s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
    # Example 1: Prefill the test survey
    print("=== Prefilling test_site/test_build survey ===")
    prefill_csv_survey('test_site/test_build')
    
    print("\n=== Done! ===")
    print("Check the CSV files in test_site/test_build/ to see the prefilled data")
    print("\nThe function automatically:")
    print("- Reads the config.json file")
    print("- Finds all CSV files in the directory") 
    print("- Prefills them with names and default values based on the configuration")
    print("- Sets appropriate units (FT2 for areas, DEG_F for temperatures)")

if __name__ == "__main__":
    main()
