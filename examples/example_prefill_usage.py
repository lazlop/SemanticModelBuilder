"""
Example usage of the prefill_csv_survey function

This script demonstrates how to use the simple prefill function to 
populate CSV survey files based on an existing configuration.
"""
import pandas as pd
import json
from pathlib import Path
from semantic_mpc_interface import HPFlexSurvey, SHACLHandler
from pyshacl.rdfutil import clone

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
        # Handle zone template with special logic
        if template_name == 'zone':
            _fill_zone_template(csv_file)
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


def _fill_zone_template(csv_file):
    """
    Fill zone template with special logic for all columns.
    For rows where any columns are empty but other columns are filled,
    and the zone name matches another row with filled values,
    duplicate those values to the empty rows. Ensures no empty columns remain.
    
    Args:
        csv_file (str): Path to the zone CSV file
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Track changes
        filled_cells = 0
        
        # Check if name column exists
        if 'name' not in df.columns:
            print("Zone template missing 'name' column")
            return
        
        # Group by zone name to find reference values
        zone_groups = df.groupby('name')
        
        for zone_name, group in zone_groups:
            # Create a reference dictionary to store the best values for each column
            reference_values = {}
            
            # For each column (except name), find the best reference value
            for col in df.columns:
                if col == 'name':
                    continue
                
                # Find rows with filled values for this column
                filled_mask = (
                    group[col].notna() & 
                    (group[col].astype(str).str.strip() != '') &
                    (group[col].astype(str).str.strip() != 'nan')
                )
                
                filled_values = group[filled_mask][col]
                if len(filled_values) > 0:
                    # Use the first non-empty value as reference
                    reference_values[col] = filled_values.iloc[0]
            
            # Now fill empty cells for this zone using reference values
            for idx in group.index:
                for col in df.columns:
                    if col == 'name':
                        continue
                    
                    # Check if this cell is empty
                    current_value = df.at[idx, col]
                    is_empty = (
                        pd.isna(current_value) or 
                        str(current_value).strip() == '' or 
                        str(current_value).strip().lower() == 'nan'
                    )
                    
                    # If empty and we have a reference value, fill it
                    if is_empty and col in reference_values:
                        df.at[idx, col] = reference_values[col]
                        filled_cells += 1
        
        # Save the updated CSV only if changes were made
        if filled_cells > 0:
            df.to_csv(csv_file, index=False)
            print(f"Filled {filled_cells} empty cells in zone.csv")
        else:
            print("No empty cells found to fill in zone.csv")
            
    except Exception as e:
        print(f"Error processing zone.csv: {e}")
            

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
    print("\n=== Done! Now generating SHACL===")
    og = clone.clone_graph(s.graph)
    handler = SHACLHandler(ontology='brick')
    handler.generate_shapes()
    # Validate a model
    conforms, results_graph, results_text = handler.validate_model(s.graph)
    (s.graph-og).print()
if __name__ == "__main__":
    main()
