# TODO: Provide SI or IP Units when survey is generated to set defaults for units
import csv
import pandas as pd
import json
import os
from pathlib import Path
from importlib.resources import files
from typing import Literal as PyLiteral

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from rdflib import Graph, Literal, Namespace, URIRef
from .namespaces import * 


def validate_dict(input_dict):
    """
    Validates that the input is a dictionary with string keys and list values.

    Args:
        input_dict (any): The object to validate.

    Returns:
        bool: True if the input is a valid dictionary with string keys and list values, False otherwise.
    """
    # Check if the input is a dictionary
    if not isinstance(input_dict, dict):
        assert TypeError("input must be dictionary")
        return False

    # Check that all keys are strings and all values are lists
    for key, value in input_dict.items():
        if not isinstance(key, str) or not isinstance(value, list):
            assert ValueError(
                "Input dictionary incorrect shape. Must have string keys and list values"
            )
            return False

    return True


class SurveyGenerator:
    """
    General survey generator for creating CSV files from templates.
    This class handles the basic template loading and CSV generation functionality.
    """
    def __init__(self, site_id, building_id, output_dir, ontology='brick', template_dict=None, overwrite=False):
        """
        Initialize the general survey generator.
        
        Args:
            site_id (str): Site identifier
            building_id (str): Building identifier
            output_dir (str): Output directory path
            ontology (str): Ontology type ('brick' or 's223')
            template_dict (list): List of template names to generate CSVs for
            overwrite (bool): Whether to overwrite existing directories
        """
        self.bm = BuildingMOTIF("sqlite://")
        self.site_id = site_id
        self.building_id = building_id
        self.base_dir = None
        self.ontology = ontology
        self.template_dict = template_dict or {}
        self._load_templates()
        self.base_dir = Path(output_dir) / self.site_id / self.building_id
        self._create_directory_structure(output_dir, overwrite)
        self.template_csvs = {}
        for file_name, template_name in self.template_dict.items():
            template = self.templates.get_template_by_name(template_name)
            file = self._create_csv(file_name, template)
            self.template_csvs[file_name] = file

    def _load_templates(self) -> None:
        """Load ontology-specific templates."""
        template_dir = str(
            files("semantic_mpc_interface")
            .joinpath("templates")
            .joinpath(f"{self.ontology}-templates")
        )
        try:
            self.templates = Library.load(directory=template_dir)
            if self.ontology == "brick":
                self.ontology_ns = BRICK
            elif self.ontology == "s223":
                self.ontology_ns = S223
            else:
                raise ValueError("Invalid ontology. Must be 'brick' or 's223'")
        except Exception as e:
            print(f"Failed to load templates from {template_dir}: {e}")
            raise

    def _create_directory_structure(self, base_path, overwrite=False):
        """Create the directory structure for the survey"""
        self.base_dir = Path(base_path) / self.site_id / self.building_id

        # Check if main directory exists and is not empty
        if overwrite == False and (self.base_dir.exists() and any(self.base_dir.iterdir())):
            raise FileExistsError(
                f"Directory '{self.base_dir}' already exists and is not empty. Please use a different path or clear the directory."
            )

        # Create main directory and parent directories if they don't exist
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _create_csv(self, file_name, template):
        """Create CSV file from template"""
        params = template.all_parameters
        template = template.inline_dependencies()
        mapping = {}
        for param in params:
            if '_name' in param:
                template = template.evaluate({param: Literal('na')})
            if '_value' in param:
                mapping[param] = param.split('_')[:-1]
        file = str(self.base_dir / file_name) + ".csv"
        template.generate_csv(file)
        self._edit_cols(file, mapping)
        return file 

    def _edit_cols(self, file, mapping, first_col='name'):
        """Edit column names in CSV file"""
        df = pd.read_csv(file)
        new_cols = [mapping.get(first_col, first_col)] + [mapping.get(col, col) for col in df.columns if col != first_col]
        print(new_cols)
        df = df[new_cols]
        df.to_csv(file, index=False)

    def _create_point_list(self):
        """Create csv-file to which point list should be added"""
        headers = ["point_of", "point_type", "point_name", "quantitykind", "unit"]
        with open(self.base_dir / f"point_list.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)


class BuildingStructureGenerator(SurveyGenerator):
    """
    Specialized generator for building structures with HVAC, zones, spaces, and windows.
    This class extends SurveyGenerator with specific functionality for building systems.
    """
    # TODO: update to use template_dict
    def __init__(self, site_id, building_id, output_dir, system_of_units="IP", ontology='brick', 
                 template_dict={"space":"space", "hvac":"hp-rtu", "tstat":"tstat", "window":"window"}, overwrite=False):
        """
        Initialize the building structure generator.
        
        Args:
            site_id (str): Site identifier
            building_id (str): Building identifier
            output_dir (str): Output directory path
            system_of_units (str): Unit system ('IP' or 'SI')
            ontology (str): Ontology type ('brick' or 's223')
            hvac_type (str): HVAC system type
            template_dict (list): List of template names (defaults to building-specific templates)
            overwrite (bool): Whether to overwrite existing directories
        """
        self.hvac_type = template_dict['hvac']
        self.system_of_units = system_of_units
        
        # Set default units based on system
        if system_of_units == "IP":
            self.default_area_unit = "FT2"
            self.default_temperature_unit = "DEG_F"
        else:
            self.default_area_unit = "M2"
            self.default_temperature_unit = "DEG_C"
        
        # Initialize parent class
        super().__init__(site_id, building_id, output_dir, ontology, template_dict, overwrite)

    def easy_config(self, zone_space_window_list):
        """Creates generic building configuration with one HVAC unit per zone
        
        Args:
            zone_space_window_list: list
                List with an entry per zone, in each entry is a tuple with the amount of spaces and windows
                e.g. 1 zone, with 2 spaces and 3 windows is [(2,3)]
        """
        self.hvacs_feed_hvacs = {}
        self.hvacs_feed_zones = {}
        self.zones_contain_spaces = {}
        self.zones_contain_windows = {}
        
        for zone_num, zone_contents in enumerate(zone_space_window_list):
            zone_name = f"zone_{zone_num + 1}"
            self.hvacs_feed_zones[f"hvac_{zone_num + 1}"] = [zone_name]
            self.zones_contain_spaces[zone_name] = []
            self.zones_contain_windows[zone_name] = []
            (amt_spaces, amt_windows) = zone_contents
            
            for space_num in range(amt_spaces):
                space_name = f"space_{zone_num + 1}_{space_num + 1}"
                self.zones_contain_spaces[zone_name].append(space_name)
            
            for window_num in range(amt_windows):
                window_name = f"window_{zone_num + 1}_{window_num + 1}"
                self.zones_contain_windows[zone_name].append(window_name)

        self._building_structure(
            self.hvacs_feed_hvacs,
            self.hvacs_feed_zones,
            self.zones_contain_spaces,
            self.zones_contain_windows,
        )

    def _building_structure(self, hvacs_feed_hvacs, hvacs_feed_zones, zones_contain_spaces, zones_contain_windows):
        """Generate the complete building structure and prefill CSVs
        
        Args:
            hvacs_feed_hvacs: dict
                Dictionary that describes which HVAC systems feed which HVAC systems.
                e.g. {ahu_1: [vav_1, vav_2, vav_3]}
            hvacs_feed_zones: dict
                Dictionary that describes which HVAC systems feed which zones.
                e.g. {vav_1: [zone_1], vav_2: [zone_2, zone_3]}
            zones_contain_spaces: dict
                Dictionary describing which zones contain which spaces.
                e.g. {zone_1: [space_1, space_2, space_3]}
            zones_contain_windows: dict
                Dictionary describing which zones contain which windows.
                e.g. {zone_1: [window1, window2]}
        """
        # Data validation
        validate_dict(hvacs_feed_hvacs)
        validate_dict(hvacs_feed_zones)
        validate_dict(zones_contain_spaces)
        validate_dict(zones_contain_windows)

        self._create_point_list()

        # Save configuration
        config = {
            "site_id": self.site_id,
            "hvac_type": self.hvac_type,
            "hvacs_feed_hvacs": hvacs_feed_hvacs,
            "hvacs_feed_zones": hvacs_feed_zones,
            "zones_contain_spaces": zones_contain_spaces,
            "zones_contain_windows": zones_contain_windows,
        }
        print(config)
        with open(self.base_dir / "config.json", "w") as f:
            json.dump(config, f, indent=4)
        
        # Prefill CSV files with data from config
        self._prefill_csv_defaults(config)

    def _prefill_csv_defaults(self, config):
        """
        Prefill CSV files with data based on the configuration.
        
        Args:
            config (dict): Configuration dictionary containing building structure information
        """
        # Prefill space CSV
        if 'space' in self.template_csvs and 'zones_contain_spaces' in config:
            self._prefill_space_csv(config['zones_contain_spaces'])
        
        # Prefill window CSV
        if 'window' in self.template_csvs and 'zones_contain_windows' in config:
            self._prefill_window_csv(config['zones_contain_windows'])
        
        # Prefill HVAC CSV
        if 'hvac' in self.template_csvs and 'hvacs_feed_zones' in config:
            self._prefill_hvac_csv(config['hvacs_feed_zones'])
        
        # Prefill thermostat CSV (one per zone)
        if 'tstat' in self.template_csvs and 'hvacs_feed_zones' in config:
            self._prefill_tstat_csv(config['hvacs_feed_zones'])

    def _prefill_space_csv(self, zones_contain_spaces):
        """Prefill space CSV with space names and default values"""
        space_file = self.template_csvs['space']
        
        # Clear existing data and create new rows
        new_rows = []
        for zone_name, spaces in zones_contain_spaces.items():
            for space_name in spaces:
                new_rows.append({
                    'name': space_name,
                    'area_unit': self.default_area_unit,
                    'area_value': ''  # Leave empty for user to fill
                })
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows)
        new_df.to_csv(space_file, index=False)

    def _prefill_window_csv(self, zones_contain_windows):
        """Prefill window CSV with window names and default values"""
        window_file = self.template_csvs['window']
        
        # Clear existing data and create new rows
        new_rows = []
        for zone_name, windows in zones_contain_windows.items():
            for window_name in windows:
                new_rows.append({
                    'name': window_name,
                    'tilt_value': '',  # Leave empty for user to fill
                    'area_unit': self.default_area_unit,
                    'area_value': '',  # Leave empty for user to fill
                    'azimuth_value': ''  # Leave empty for user to fill
                })
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows)
        new_df.to_csv(window_file, index=False)

    def _prefill_hvac_csv(self, hvacs_feed_zones):
        """Prefill HVAC CSV with HVAC unit names and default values"""
        hvac_file = self.template_csvs['hvac']
        
        # Clear existing data and create new rows
        new_rows = []
        for hvac_name in hvacs_feed_zones.keys():
            new_rows.append({
                'name': hvac_name,
                'heating_COP_value': '',  # Leave empty for user to fill
                'heating_capacity_value': '',  # Leave empty for user to fill
                'cooling_COP_value': '',  # Leave empty for user to fill
                'cooling_capacity_value': ''  # Leave empty for user to fill
            })
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows)
        new_df.to_csv(hvac_file, index=False)

    def _prefill_tstat_csv(self, hvacs_feed_zones):
        """Prefill thermostat CSV with thermostat names (one per zone) and default values"""
        tstat_file = self.template_csvs['tstat']
        
        # Clear existing data and create new rows
        new_rows = []
        for hvac_name, zones in hvacs_feed_zones.items():
            for zone_name in zones:
                tstat_name = f"tstat_{zone_name}"
                new_rows.append({
                    'name': tstat_name,
                    'setpoint_deadband-unit': self.default_temperature_unit,
                    'resolution-value': '',
                    'tolerance': '',
                    'tolerance-value': '',
                    'setpoint_deadband': '',
                    'tolerance-unit': self.default_temperature_unit,
                    'active': '',
                    'stage_count-value': '',
                    'resolution-unit': self.default_temperature_unit,
                    'active-value': '',
                    'stage_count': '',
                    'setpoint_deadband-value': '',
                    'resolution': ''
                })
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows)
        new_df.to_csv(tstat_file, index=False)

    def prefill_from_config(self, config_path=None):
        """
        Prefill CSV files from an existing configuration file or the current config.
        
        Args:
            config_path (str, optional): Path to config.json file. If None, uses the config 
                                       from the current base directory.
        """
        if config_path is None:
            config_path = self.base_dir / "config.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            print(f"Loading config from: {config_path}")
            self._prefill_csv_defaults(config)
            print("CSV files have been prefilled successfully!")
            
        except FileNotFoundError:
            print(f"Config file not found: {config_path}")
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
        except Exception as e:
            print(f"Error prefilling CSVs: {e}")
