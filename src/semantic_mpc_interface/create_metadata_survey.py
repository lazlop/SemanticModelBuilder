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
    def __init__(self, site_id, building_id, output_dir, system_of_units="IP", ontology = 'brick', hvac_type = 'hp-rtu', template_list = ["space", "hp-rtu", "tstat", "window"], overwrite = False):
        # TODO: is there any default for windows added?
        # hvac_type currently unused, but may be used later for creation of the brick model
        # SYSTEM of units can either be IP or SI, and default units will be filled out for all values
        self.bm = BuildingMOTIF("sqlite://")
        self.site_id = site_id
        self.building_id = building_id
        self.base_dir = None
        self.hvac_type = hvac_type
        self.system_of_units = system_of_units
        self.template_list = template_list
        if system_of_units == "IP":
            self.default_area_unit = "FT2"
            self.default_temperature_unit = "DEG_F"
        else:
            self.default_area_unit = "M2"
            self.default_temperature_unit = "DEG_C"
        self.ontology = ontology
        self._load_templates()
        self.base_dir = Path(output_dir) / self.site_id / self.building_id
        self._create_directory_structure(output_dir, overwrite)
        for name in template_list:
            template = self.templates.get_template_by_name(name)
            self._create_csv(template)

    
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

    # def easy_config(self, zone_space_window_list, output_path):
    #     """Creates generic SMCB configuration with one HVAC unit per zone, filling in zone and space names and assuming one tstat per zone and one hvac per zone
    #     zone_space_window_list: list
    #         List with an entry per zone, in each entry is a touple with a list of the amount of spaces and windows
    #         e.g. 1 zone, with 2 spaces and 3 windows is [(2,3)]
    #     """
    #     self.hvacs_feed_hvacs = {}
    #     self.hvacs_feed_zones = {}
    #     self.zones_contain_spaces = {}
    #     self.zones_contain_windows = {}
    #     for zone_num, zone_contents in enumerate(zone_space_window_list):
    #         zone_name = f"zone_{zone_num + 1}"
    #         self.hvacs_feed_zones[f"hvac_{zone_num + 1}"] = [zone_name]
    #         self.zones_contain_spaces[zone_name] = []
    #         self.zones_contain_windows[zone_name] = []
    #         (amt_spaces, amt_windows) = zone_contents
    #         for space_num in range(amt_spaces):
    #             space_name = f"space_{zone_num + 1}_{space_num + 1}"
    #             self.zones_contain_spaces[zone_name].append(space_name)
    #         for window_num in range(amt_windows):
    #             window_name = f"window_{zone_num + 1}_{window_num + 1}"
    #             self.zones_contain_windows[zone_name].append(window_name)

    #     # TODO: fill in the topology of the building and output file
    #     self.generate_template(
    #         self.hvacs_feed_hvacs,
    #         self.hvacs_feed_zones,
    #         self.zones_contain_spaces,
    #         self.zones_contain_windows,
    #         output_path,
    #     )

    def _create_directory_structure(self, base_path, overwrite = False):
        """Create the directory structure for the Brick model"""
        self.base_dir = Path(base_path) / self.site_id / self.building_id

        # Check if main directory exists and is not empty
        if overwrite == False and (self.base_dir.exists() and any(self.base_dir.iterdir())):
            raise FileExistsError(
                f"Directory '{self.base_dir}' already exists and is not empty. Please use a different path or clear the directory."
            )

        # Create main directory and parent directories if they don't exist
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # # Create subdirectories
        # subdirs = self.template_list
        # for subdir in subdirs:
        #     subdir_path = self.base_dir / subdir
        #     if overwrite == False:
        #         if subdir_path.exists() and any(subdir_path.iterdir()):
        #             raise FileExistsError(
        #                 f"Subdirectory '{subdir_path}' already exists and is not empty. Please use a different path or clear the directory."
        #             )
        #     subdir_path.mkdir(parents=True, exist_ok=True)

    def _create_csv(self, template):
        """Create site information CSV file"""
        params = template.all_parameters
        template = template.inline_dependencies()
        mapping = {}
        for param in params:
            if '_name' in param:
                template = template.evaluate({param:Literal('na')})
            if '_value' in param:
                mapping[param:param.split['_'][-1]]
        file = str(self.base_dir / template.name) + ".csv"
        template.generate_csv(file)
        #move name to the front
        df = pd.read_csv(file)
        new_order = ['name'] + [col for col in df.columns if col != 'name']
        df = df[new_order]
        df.to_csv(file, index = False)

        
    #     site_info = {
    #         "headers": ["site_id", "timezone", "latitude", "longitude", "noaa_station"],
    #         "file": "site_info.csv",
    #     }

    #     with open(self.base_dir / site_info["file"], "w", newline="") as f:
    #         writer = csv.writer(f)
    #         writer.writerow(site_info["headers"])
    #         writer.writerow([self.site_id, "", "", "", ""])  # Empty row for user input

    # def _create_space_files(self, zones_contain_spaces):
    #     """Create zone-related CSV files"""
    #     for zone, spaces in zones_contain_spaces.items():
    #         # Create space file for each zone
    #         space_headers = ["space_id", "zone_id", "area_value", "area_unit"]
    #         with open(
    #             self.base_dir / "spaces" / f"{zone}_spaces.csv", "w", newline=""
    #         ) as f:
    #             writer = csv.writer(f)
    #             writer.writerow(space_headers)
    #             for space in spaces:
    #                 writer.writerow([space, zone, "", self.default_area_unit])

    # def _create_point_list(self):
    #     """Create csv-file to which point list should be added"""
    #     # TODO: Note that point_type can be
    #     headers = ["point_of", "point_type", "point_name", "quantitykind", "unit"]
    #     with open(self.base_dir / f"point_list.csv", "w", newline="") as f:
    #         writer = csv.writer(f)
    #         writer.writerow(headers)

    # def _create_hvac_files(self, hvacs_feed_hvacs, hvacs_feed_zones):
    #     """Create HVAC-related CSV files"""
    #     # could potentially delete zone_id from this.
    #     # TODO: Not totally sure how the VRF was handled, should make sure this fits
    #     hvac_headers = [
    #         "hvac_id",
    #         "zone_id",
    #         "cooling_capacity",
    #         "heating_capacity",
    #         "cooling_cop",
    #         "heating_cop",
    #     ]
    #     with open(self.base_dir / "hvac" / f"hvac_units.csv", "w", newline="") as f:
    #         writer = csv.writer(f)
    #         writer.writerow(hvac_headers)
    #         hvac_already_done = set()
    #         for hvac, zones in hvacs_feed_zones.items():
    #             hvac_already_done.add(hvac)
    #             for zone in zones:
    #                 writer.writerow([hvac, zone, "", "", "", ""])
    #         for hvac, hvacs in hvacs_feed_hvacs.items():
    #             if hvac in hvac_already_done:
    #                 continue
    #             writer.writerow([hvac, "", "", "", ""])
    #             hvac_already_done.add(hvac)
    #             # Not adding feeds relationship for hvac to spreadsheet
    #             # for fed_hvac in hvacs:
    #             #     writer.writerow([hvac, fed_hvac, "", "", ""])
    #             #     hvac_already_done.add(hvac)

    # # Thermostats are directly linked to zones. Need to make sure this is correct
    # def _create_zone_files(self, zones_contain_spaces):
    #     """Create zone/thermostat related files. Not sure which definition is preferred since these are 1:1 for this MPC (i think)"""
    #     # TODO: not sure these are the parameters needed at the stage of the metadata survey, should refine this
    #     tstat_headers = [
    #         "tstat_id",
    #         "zone_id",
    #         "stage_count",
    #         "setpoint_deadband",
    #         "tolerance",
    #         "active",
    #         "resolution",
    #         "temperature_unit",
    #     ]

    #     with open(self.base_dir / "zones" / "zones.csv", "w", newline="") as f:
    #         writer = csv.writer(f)
    #         writer.writerow(tstat_headers)
    #         for zone in zones_contain_spaces.keys():
    #             writer.writerow(
    #                 [
    #                     f"tstat_{zone}",
    #                     zone,
    #                     "",
    #                     "",
    #                     "",
    #                     "",
    #                     "",
    #                     self.default_temperature_unit,
    #                 ]
    #             )

    # # Windoes also linked to zones, not spaces. Should make sure that's correct
    # def _create_window_files(self, zones_contain_windows):
    #     """Create window-related CSV files"""
    #     window_headers = [
    #         "window_id",
    #         "zone_id",
    #         "area_value",
    #         "azimuth_value",
    #         "tilt_value",
    #         "area_unit",
    #     ]
    #     for zone, windows in zones_contain_windows.items():
    #         with open(
    #             self.base_dir / "windows" / f"{zone}_windows.csv", "w", newline=""
    #         ) as f:
    #             writer = csv.writer(f)
    #             writer.writerow(window_headers)
    #             for window in windows:
    #                 writer.writerow([window, zone, "", "", "", self.default_area_unit])

    # def generate_template(
    #     self,
    #     hvacs_feed_hvacs,
    #     hvacs_feed_zones,
    #     zones_contain_spaces,
    #     zones_contain_windows,
    #     output_path,
    # ):
    #     """Generate the complete template structure

    #     hvacs_feed_hvacs: dict
    #         Dictionary that describes which HVAC systems feed which HVAC systems.
    #         e.g. {ahu_1: [vav_1, vav_2, vav_3]}

    #     hvacs_feed_zones: dict
    #         Dictionary that describes which HVAC systems feed which zones.
    #         e.g. {vav_1: [zone_1], vav_2: [zone_2, zone_3]}

    #     zones_contain_spaces: dict
    #         Dictonary describing which zones contain which spaces.
    #         e.g. {zone_1: [space_1, space_2, space_3]}

    #     zones_contain_windows: dict
    #         Dictionary describing which zones contain which windows.
    #         e.g. {zone_1: [window1, window2]}

    #     Currently, dictionaries are not handled recursively.
    #     """
    #     # a little data validation
    #     validate_dict(hvacs_feed_hvacs)
    #     validate_dict(hvacs_feed_zones)
    #     validate_dict(zones_contain_spaces)
    #     validate_dict(zones_contain_windows)

    #     self._create_directory_structure(output_path)
    #     self._create_site_info_file()
    #     self._create_space_files(zones_contain_spaces)
    #     self._create_hvac_files(hvacs_feed_hvacs, hvacs_feed_zones)
    #     self._create_zone_files(zones_contain_spaces)
    #     self._create_window_files(zones_contain_windows)
    #     self._create_point_list()

    #     # Save configuration
    #     config = {
    #         "site_id": self.site_id,
    #         "hvac_type": self.hvac_type,
    #         "hvacs_feed_hvacs": hvacs_feed_hvacs,
    #         "hvacs_feed_zones": hvacs_feed_zones,
    #         "zones_contain_spaces": zones_contain_spaces,
    #         "zones_contain_windows": zones_contain_windows,
    #     }

    #     with open(self.base_dir / "config.json", "w") as f:
    #         json.dump(config, f, indent=4)

    # def _defaults(self):
    #     # TODO: Any default informatino to fill?
    #     pass
