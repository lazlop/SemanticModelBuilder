import pandas as pd
import json
import re

def expand_hvac_csv_generic(csv_path, config_path, output_path=None):
    """
    Expand HVAC CSV file with new columns based on variatic parameters from config.json
    Replaces any <placeholder> that matches a column name in the CSV with the actual value
    
    Args:
        csv_path (str): Path to the HVAC CSV file
        config_path (str): Path to the config JSON file
        output_path (str): Path for the output CSV file (optional)
    """
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    print(f"Original CSV shape: {df.shape}")
    print(f"Original columns: {list(df.columns)}")
    
    # Read the config file
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get the hvac_type from config
    hvac_type = config.get('hvac_type', 'hp-rtu')
    print(f"HVAC type: {hvac_type}")
    
    # Get variatic parameters for the hvac type
    variatic_params = config.get('variatic_params', {}).get(hvac_type, {})
    print(f"Variatic parameters for {hvac_type}: {variatic_params}")
    
    # Create new columns based on variatic parameters
    new_columns_data = {}
    
    # Process each row in the dataframe
    for idx, row in df.iterrows():
        for param_key, param_template in variatic_params.items():
            # Find all placeholders in angle brackets
            placeholders = re.findall(r'<([^>]+)>', param_template)
            
            # Replace placeholders with actual values from the row
            expanded_template = param_template
            for placeholder in placeholders:
                if placeholder in df.columns:
                    # Get the value from the current row for this placeholder
                    placeholder_value = row[placeholder]
                    if pd.notna(placeholder_value):
                        expanded_template = expanded_template.replace(f'<{placeholder}>', str(placeholder_value))
                    else:
                        # If the value is NaN, skip this row for this template
                        expanded_template = None
                        break
            
            # Only create column if template was successfully expanded
            if expanded_template and expanded_template != param_template:
                # Initialize the column if it doesn't exist
                if expanded_template not in new_columns_data:
                    new_columns_data[expanded_template] = [None] * len(df)
                
                # Set empty string as placeholder value (you can modify this as needed)
                new_columns_data[expanded_template][idx] = ""
    
    # Add new columns to the dataframe
    for col_name, col_values in new_columns_data.items():
        df[col_name] = col_values
    
    print(f"Expanded CSV shape: {df.shape}")
    print(f"New columns added: {list(new_columns_data.keys())}")
    
    # Save the expanded CSV
    if output_path is None:
        output_path = csv_path.replace('.csv', '_expanded.csv')
    
    df.to_csv(output_path, index=False)
    print(f"Expanded CSV saved to: {output_path}")
    
    return df

def expand_hvac_dataframe_generic(df, config_data, hvac_type=None):
    """
    Expand HVAC DataFrame with new columns based on variatic parameters
    Replaces any <placeholder> that matches a column name in the DataFrame
    
    Args:
        df (pd.DataFrame): The HVAC DataFrame to expand
        config_data (dict): The configuration dictionary
        hvac_type (str): Override the hvac_type from config (optional)
    
    Returns:
        pd.DataFrame: Expanded DataFrame with new columns
    """
    
    # Make a copy to avoid modifying the original
    expanded_df = df.copy()
    
    # Get the hvac_type
    if hvac_type is None:
        hvac_type = config_data.get('hvac_type', 'hp-rtu')
    
    # Get variatic parameters for the hvac type
    variatic_params = config_data.get('variatic_params', {}).get(hvac_type, {})
    
    # Track new columns to add
    new_columns_data = {}
    
    # Process each row in the dataframe
    for idx, row in expanded_df.iterrows():
        for param_key, param_template in variatic_params.items():
            # Find all placeholders in angle brackets
            placeholders = re.findall(r'<([^>]+)>', param_template)
            
            # Replace placeholders with actual values from the row
            expanded_template = param_template
            valid_expansion = True
            
            for placeholder in placeholders:
                if placeholder in expanded_df.columns:
                    # Get the value from the current row for this placeholder
                    placeholder_value = row[placeholder]
                    if pd.notna(placeholder_value):
                        expanded_template = expanded_template.replace(f'<{placeholder}>', str(placeholder_value))
                    else:
                        # If the value is NaN, skip this expansion
                        valid_expansion = False
                        break
                else:
                    # Placeholder doesn't match any column, skip this expansion
                    valid_expansion = False
                    break
            
            # Only create column if template was successfully expanded and is different from original
            if valid_expansion and expanded_template != param_template:
                # Initialize the column if it doesn't exist
                if expanded_template not in new_columns_data:
                    new_columns_data[expanded_template] = [""] * len(expanded_df)
                
                # Set empty string as placeholder value
                new_columns_data[expanded_template][idx] = ""
    
    # Add new columns to the dataframe
    for col_name, col_values in new_columns_data.items():
        expanded_df[col_name] = col_values
    
    return expanded_df

if __name__ == "__main__":
    # Define file paths
    csv_path = "test_site/test_build/hvac.csv"
    config_path = "test_site/test_build/config.json"
    output_path = "test_site/test_build/hvac_expanded_generic.csv"
    
    # Expand the CSV
    expanded_df = expand_hvac_csv_generic(csv_path, config_path, output_path)
    
    # Display the result
    print("\nExpanded DataFrame:")
    print(expanded_df.to_string())
    
    # Show which placeholders were found and replaced
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    hvac_type = config.get('hvac_type', 'hp-rtu')
    variatic_params = config.get('variatic_params', {}).get(hvac_type, {})
    
    print(f"\nPlaceholder analysis for {hvac_type}:")
    df = pd.read_csv(csv_path)
    for param_key, param_template in variatic_params.items():
        placeholders = re.findall(r'<([^>]+)>', param_template)
        print(f"  {param_key}: {param_template}")
        print(f"    Placeholders found: {placeholders}")
        for placeholder in placeholders:
            if placeholder in df.columns:
                print(f"    ✓ '{placeholder}' matches CSV column")
            else:
                print(f"    ✗ '{placeholder}' does not match any CSV column")
