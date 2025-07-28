#!/usr/bin/env python3
"""
Example usage of the prefill_csv_survey function

This script demonstrates how to use the simple prefill function to 
populate CSV survey files based on an existing configuration.
"""
import pandas as pd
import json
from pathlib import Path
from semantic_mpc_interface import HPFlexSurvey

def prefill_csv_survey(survey_directory):
    """
    Simple function to prefill all CSV files in a survey directory based on existing config.json
    This function fills every parameter that is not already filled with an appropriate value.
    
    Args:
        survey_directory (str): Path to the directory containing CSV files and config.json
                               (e.g., 'test_site/test_build')
    
    Example:
        prefill_csv_survey('test_site/test_build')
    """    
    survey_path = Path(survey_directory)
    config_path = survey_path / "config.json"
    
    # Check if directory and config exist
    if not survey_path.exists():
        print(f"Directory not found: {survey_directory}")
        return
    
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Loading config from: {config_path}")
    
    # Get site_id from config for unit defaults
    site_id = config.get('site_id', 'default_site')
    
    # Set default units (assuming IP units like in the example)
    default_area_unit = "FT2"
    default_temperature_unit = "DEG_F"
    
    # Create template_csvs mapping by finding CSV files in directory
    template_csvs = {}
    for csv_file in survey_path.glob("*.csv"):
        template_name = csv_file.stem  # filename without extension
        template_csvs[template_name] = str(csv_file)
    
    print(f"Found CSV files: {list(template_csvs.keys())}")

    _fill_all_empty_columns(template_csvs)
        

def _fill_all_empty_columns(template_csvs):
    """
    Fill all empty columns in CSV files with appropriate default values.
    For each empty cell, uses the column name with a number appended as the default value.
    Only fills cells that are truly empty (NaN, empty string, or whitespace only).
    Preserves any existing data.
    
    Args:
        template_csvs (dict): Dictionary mapping template names to CSV file paths
    """
    
    for template_name, csv_file in template_csvs.items():
        # skipping zone
        if template_name == 'zone':
            continue
        try:
            # Read the CSV file
            df = pd.read_csv(csv_file)
            
            # Track how many columns were filled
            filled_columns = 0
            filled_cells = 0
            
            # Iterate through each column
            for col in df.columns:
                # Skip the 'name' column as it should already be filled with meaningful values
                if col == 'name':
                    continue
                
                # Check if column has any empty values
                # More robust empty checking: NaN, empty string, whitespace only, or None
                empty_mask = (
                    df[col].isna() | 
                    (df[col].astype(str).str.strip() == '') |
                    (df[col].astype(str).str.strip() == 'nan') |
                    df[col].isnull()
                )
                
                if empty_mask.any():
                    filled_columns += 1
                    
                    # Generate default values for empty cells only
                    for idx in df[empty_mask].index:
                        # Only fill if the cell is actually empty
                        current_value = df.at[idx, col]
                        if pd.isna(current_value) or str(current_value).strip() == '' or str(current_value).strip().lower() == 'nan':
                            # Create a default value using column name + row number
                            default_value = idx+1
                            # default_value = f"{col}_{idx + 1}"
                            df.at[idx, col] = default_value
                            filled_cells += 1
            
            # Save the updated CSV only if changes were made
            if filled_cells > 0:
                df.to_csv(csv_file, index=False)
                print(f"Filled {filled_cells} empty cells across {filled_columns} columns in {template_name}.csv")
            else:
                print(f"No empty cells found in {template_name}.csv")
                
        except Exception as e:
            print(f"Error processing {template_name}.csv: {e}")
            

def main():
    """
    Example of using the prefill_csv_survey function
    """
    print('GENERATING SURVEY')
    s = HPFlexSurvey('test_site','test_build','.', overwrite=True); s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
    # Example 1: Prefill the test survey
    print("=== Prefilling test_site/test_build survey ===")
    prefill_csv_survey('test_site/test_build')
    print("\n=== Done! Now loading csv===")
    s.read_csv()
    print("\n=== Done! reading csv===")
if __name__ == "__main__":
    main()
