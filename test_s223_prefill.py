#!/usr/bin/env python3
"""
Test script to verify s223 prefill logic works correctly and generates 
CSV files that look the same as brick templates.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / "src"))

from semantic_mpc_interface.survey import HPFlexSurvey

def test_s223_prefill():
    """Test that s223 prefill logic creates clean CSV files like brick"""
    
    # Create s223 survey
    print("Creating s223 survey...")
    s223_survey = HPFlexSurvey(
        site_id="test_s223_site",
        building_id="test_build",
        output_dir="tutorial",
        ontology="s223",
        overwrite=True
    )
    
    # Use easy_config to set up the building structure
    zone_space_window_list = [(2, 2), (1, 2), (1, 3)]  # 3 zones with different space/window counts
    s223_survey.easy_config(zone_space_window_list)
    
    print("s223 survey created successfully!")
    
    # Check the generated CSV files
    base_dir = Path("tutorial/test_s223_site/test_build")
    
    print("\nChecking generated CSV files:")
    for csv_file in ["hvac.csv", "space.csv", "window.csv", "zone.csv", "tstat.csv", "site.csv"]:
        file_path = base_dir / csv_file
        if file_path.exists():
            print(f"✓ {csv_file} exists")
            # Read and display first few lines
            with open(file_path, 'r') as f:
                lines = f.readlines()
                print(f"  Headers: {lines[0].strip()}")
                if len(lines) > 1:
                    print(f"  First row: {lines[1].strip()}")
        else:
            print(f"✗ {csv_file} missing")
    
    # Compare with brick version
    print("\nComparing with brick version:")
    brick_base_dir = Path("tutorial/test_site/test_build")
    
    for csv_file in ["zone.csv", "hvac.csv"]:
        s223_file = base_dir / csv_file
        brick_file = brick_base_dir / csv_file
        
        if s223_file.exists() and brick_file.exists():
            with open(s223_file, 'r') as f:
                s223_headers = f.readline().strip()
            with open(brick_file, 'r') as f:
                brick_headers = f.readline().strip()
            
            print(f"\n{csv_file}:")
            print(f"  s223:  {s223_headers}")
            print(f"  brick: {brick_headers}")
            
            # Check if headers are similar (ignoring order)
            s223_cols = set(s223_headers.split(','))
            brick_cols = set(brick_headers.split(','))
            
            if csv_file == "zone.csv":
                # For zone.csv, check if brick columns are subset of s223 columns
                brick_in_s223 = brick_cols.issubset(s223_cols)
                if brick_in_s223:
                    print(f"  ✓ All brick columns present in s223 (s223 has additional connection point columns)")
                    print(f"    s223 connection point columns: {s223_cols - brick_cols}")
                else:
                    print(f"  ⚠ Some brick columns missing in s223:")
                    print(f"    missing: {brick_cols - s223_cols}")
            else:
                if s223_cols == brick_cols:
                    print(f"  ✓ Headers match exactly")
                else:
                    print(f"  ⚠ Headers differ:")
                    print(f"    s223 only: {s223_cols - brick_cols}")
                    print(f"    brick only: {brick_cols - s223_cols}")

if __name__ == "__main__":
    test_s223_prefill()
