#!/usr/bin/env python3
"""
Example usage of the prefill_csv_survey function

This script demonstrates how to use the simple prefill function to 
populate CSV survey files based on an existing configuration.
"""
import pandas as pd
from semantic_mpc_interface import HPFlexSurvey

# Delete this code or move it to testing..
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
    import json
    from pathlib import Path
    import pandas as pd
    
    survey_path = Path(survey_directory)
    config_path = survey_path / "config.json"
    
    # Check if directory and config exist
    if not survey_path.exists():
        print(f"Directory not found: {survey_directory}")
        return
    
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return
    
    try:
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
        
        # Prefill each CSV file based on config
        if 'space' in template_csvs and 'zones_contain_spaces' in config:
            _prefill_space_csv_simple(template_csvs['space'], config['zones_contain_spaces'], default_area_unit)
        
        if 'window' in template_csvs and 'zones_contain_windows' in config:
            _prefill_window_csv_simple(template_csvs['window'], config['zones_contain_windows'], default_area_unit)
        
        if 'hvac' in template_csvs and 'hvacs_feed_zones' in config:
            _prefill_hvac_csv_simple(template_csvs['hvac'], config['hvacs_feed_zones'])
        
        if 'tstat' in template_csvs and 'hvacs_feed_zones' in config:
            _prefill_tstat_csv_simple(template_csvs['tstat'], config['hvacs_feed_zones'], default_temperature_unit)
        
        if 'zone' in template_csvs and all(key in config for key in ['zones_contain_spaces', 'zones_contain_windows', 'hvacs_feed_zones']):
            _prefill_zone_csv_simple(template_csvs['zone'], config)
        
        # Fill all remaining empty columns in all CSV files
        _fill_all_empty_columns(template_csvs)
        
        print("CSV files have been prefilled successfully!")
        
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
    except Exception as e:
        print(f"Error prefilling CSVs: {e}")


def _prefill_space_csv_simple(space_file, zones_contain_spaces, default_area_unit):
    """Helper function to prefill space CSV"""
    existing_df = pd.read_csv(space_file)
    columns = existing_df.columns.tolist()
    
    new_rows = []
    for zone_name, spaces in zones_contain_spaces.items():
        for space_name in spaces:
            row = {col: '' for col in columns}
            row['name'] = space_name
            if 'area-unit' in columns:
                row['area-unit'] = default_area_unit
            new_rows.append(row)
    
    new_df = pd.DataFrame(new_rows, columns=columns)
    new_df.to_csv(space_file, index=False)
    print(f"Prefilled {space_file} with {len(new_rows)} spaces")


def _prefill_window_csv_simple(window_file, zones_contain_windows, default_area_unit):
    """Helper function to prefill window CSV"""
    existing_df = pd.read_csv(window_file)
    columns = existing_df.columns.tolist()
    
    new_rows = []
    for zone_name, windows in zones_contain_windows.items():
        for window_name in windows:
            row = {col: '' for col in columns}
            row['name'] = window_name
            if 'area-unit' in columns:
                row['area-unit'] = default_area_unit
            new_rows.append(row)
    
    new_df = pd.DataFrame(new_rows, columns=columns)
    new_df.to_csv(window_file, index=False)
    print(f"Prefilled {window_file} with {len(new_rows)} windows")


def _prefill_hvac_csv_simple(hvac_file, hvacs_feed_zones):
    """Helper function to prefill HVAC CSV"""
    existing_df = pd.read_csv(hvac_file)
    columns = existing_df.columns.tolist()
    
    new_rows = []
    for hvac_name in hvacs_feed_zones.keys():
        row = {col: '' for col in columns}
        row['name'] = hvac_name
        new_rows.append(row)
    
    new_df = pd.DataFrame(new_rows, columns=columns)
    new_df.to_csv(hvac_file, index=False)
    print(f"Prefilled {hvac_file} with {len(new_rows)} HVAC units")


def _prefill_tstat_csv_simple(tstat_file, hvacs_feed_zones, default_temperature_unit):
    """Helper function to prefill thermostat CSV"""
    existing_df = pd.read_csv(tstat_file)
    columns = existing_df.columns.tolist()
    
    new_rows = []
    for hvac_name, zones in hvacs_feed_zones.items():
        for zone_name in zones:
            row = {col: '' for col in columns}
            row['name'] = f"tstat_{zone_name}"
            # Set temperature unit columns if they exist
            if 'setpoint_deadband-unit' in columns:
                row['setpoint_deadband-unit'] = default_temperature_unit
            if 'tolerance-unit' in columns:
                row['tolerance-unit'] = default_temperature_unit
            if 'resolution-unit' in columns:
                row['resolution-unit'] = default_temperature_unit
            new_rows.append(row)
    
    new_df = pd.DataFrame(new_rows, columns=columns)
    new_df.to_csv(tstat_file, index=False)
    print(f"Prefilled {tstat_file} with {len(new_rows)} thermostats")

def _fill_all_empty_columns(template_csvs):
    """
    Fill all empty columns in CSV files with appropriate default values.
    For each empty cell, uses the column name with a number appended as the default value.
    
    Args:
        template_csvs (dict): Dictionary mapping template names to CSV file paths
    """
    import pandas as pd
    
    for template_name, csv_file in template_csvs.items():
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
                empty_mask = df[col].isna() | (df[col] == '') | (df[col] == ' ')
                
                if empty_mask.any():
                    filled_columns += 1
                    
                    # Generate default values for empty cells
                    for idx in df[empty_mask].index:
                        # Create a default value using column name + row number
                        default_value = f"{col}_{idx + 1}"
                        df.at[idx, col] = default_value
                        filled_cells += 1
            
            # Save the updated CSV
            df.to_csv(csv_file, index=False)
            
            if filled_cells > 0:
                print(f"Filled {filled_cells} empty cells across {filled_columns} columns in {template_name}.csv")
            else:
                print(f"No empty cells found in {template_name}.csv")
                
        except Exception as e:
            print(f"Error processing {template_name}.csv: {e}")


# Adding temporarily for testing
def _prefill_zone_csv_simple(zone_file, config):
    """Helper function to prefill zone CSV"""
    existing_df = pd.read_csv(zone_file)
    columns = existing_df.columns.tolist()
    
    new_rows = []
    extra_rows = []
    
    for zone_name, spaces in config["zones_contain_spaces"].items():
        # Start with empty row
        row = {col: '' for col in columns}

        if 'tstat-name' in columns:
            row['tstat-name'] = f"tstat_{zone_name}"

        # Find HVAC for this zone
        hvacs = config['hvacs_feed_zones']
        for hvac_name, hvac_zone_names in hvacs.items():
            if zone_name in hvac_zone_names:
                if 'hvac-name' in columns:
                    row['hvac-name'] = hvac_name

        if 'name' in columns:
            row['name'] = zone_name

        # Add first space to main row, additional spaces as extra rows
        for i, space_name in enumerate(spaces):
            if i > 0:
                extra_row = {col: '' for col in columns}
                extra_row['name'] = zone_name
                if 'space-name' in columns:
                    extra_row['space-name'] = space_name
                extra_rows.append(extra_row)
            else:
                if 'space-name' in columns:
                    row['space-name'] = space_name

        # Add windows
        windows = config['zones_contain_windows'].get(zone_name, [])
        for j, window_name in enumerate(windows):
            if j > 0:  # Additional windows as extra rows
                extra_row = {col: '' for col in columns}
                extra_row['name'] = zone_name
                if 'window-name' in columns:
                    extra_row['window-name'] = window_name
                extra_rows.append(extra_row)
            else:  # First window in main row
                if 'window-name' in columns:
                    row['window-name'] = window_name

        new_rows.append(row)
    
    # Combine main rows and extra rows
    all_rows = new_rows + extra_rows
    
    new_df = pd.DataFrame(all_rows, columns=columns)
    new_df.to_csv(zone_file, index=False)
    print(f"Prefilled {zone_file} with {len(all_rows)} zone entries")


def main():
    """
    Example of using the prefill_csv_survey function
    """
    print('GENERATING SURVEY')
    s = HPFlexSurvey('test_site','test_build','.', overwrite=True); s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
    # Example 1: Prefill the test survey
    return
    print("=== Prefilling test_site/test_build survey ===")
    prefill_csv_survey('test_site/test_build')
    print("\n=== Done! Now loading csv===")
    s._read_csv()
    print("\n=== Done! reading csv===")
if __name__ == "__main__":
    main()
