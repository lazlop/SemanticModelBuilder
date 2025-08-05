# TODO: Provide SI or IP Units when survey is generated to set defaults for units
# TODO: Distinction and roles of building and site ids still not super well defined. 
import csv
import pandas as pd
import json
import os
import re 
from io import StringIO
from pathlib import Path
from importlib.resources import files
from typing import Literal as PyLiteral

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from buildingmotif.ingresses import CSVIngress, TemplateIngress
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


class Survey:
    """
    General survey generator for creating CSV files from templates.
    This class handles the basic template loading and CSV generation functionality.
    """
    def __init__(self, site_id, building_id, output_dir, ontology='brick', template_map=None, overwrite=False):
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
        self.building_ns = Namespace(f"urn:hpflex/{self.site_id}#")
        self.model = Model.create(self.building_ns)
        self.graph = self.model.graph
        bind_prefixes(self.graph)
        self.graph.bind("bldg", self.building_ns)
        self.building_id = building_id
        self.base_dir = None
        self.ontology = ontology
        self.template_map = template_map or {}
        self._load_templates()
        self.base_dir = Path(output_dir) / self.site_id / self.building_id
        self._create_directory_structure(output_dir, overwrite)
        self._create_survey(template_map)
        # TODO: Still have to update point list
        self._create_point_list()

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
    
    # TODO: alter this so the init makes sense even if you are just reading the survey
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

    # TODO: Should maybe change the template dict and iterate through dependencies recursively.
    # TODO: look into how to prefill the template to better generalize and connect with the survey reader.
    # can create binidngs based on building structure and if _name maps a value or _name maps to a relation
    # TODO: consider if inlining dependencies is right. Might be better to go through dependencies and create separate surveys for optional depedencies
    # alternatively, could use dict to make sure csvs aren't redundent. Could remove dependencies if for all dependencies in the dictionary
    # Will go with removing dependencies
    # TODO: Make a bug report, when there are optional dependencies, the csv puts the optionals into the csv as columns
    # Removing columns for now
    def _create_survey(self, template_map):
        self.template_csvs = {}
        self.template_dict = {}
        for file_name, template_name in template_map.items():
            template = self.templates.get_template_by_name(template_name)
            for dependency in template.get_dependencies():
                if dependency.template.name in self.template_map.values():
                    print('removing dependency: ', dependency.template.name)
                    template.remove_dependency(dependency.template)
            self.template_dict[file_name] = template.inline_dependencies()
        self.param_mapping, self.variatic_params = self._simplify_parameters(self.template_dict)
        for file_name, template in self.template_dict.items():
            file = self._create_csv(file_name, template)
            self.template_csvs[file_name] = file

    def _simplify_parameters(self, template_dict):
        # describe changes to template parameters made before generating the csv
        param_mapping = {}
        variatic_params = {}
        # Temporary bug fix
        remove_optionals = {}
        for name, template in template_dict.items():
            template = template
            params = template.all_parameters
            # Getting the stuff before -name-value (could change to 1 if I just want to get rid of -value)
            values = {param.rsplit('-',2)[0]:param for param in params if '-value' in param}
            print('values:', values.values())
            # have to change since value just appended to name now
            value_names = {param: f"<name>-{param}" for param in params if (param.endswith('-name')) and (param + '-value' in values.values())}
            print('values names:', value_names)
            # entities = [param for param in params if ('-name' in param) and (param not in value_names)]
            # variatic_params[template.name] = entities + value_names
            variatic_params[template.name] = value_names
            param_mapping[template.name] = values
        return param_mapping, variatic_params
    # TODO: buildingmotif feature improvement - mapper for columns to namespaces/literals
    def read_csv(self, serialize = True):
        for filename, template in self.template_dict.items():
            def fill_variatic_params(filename, variatic_params):
                df = pd.read_csv(filename)
                
                # For each variatic parameter key, create a new column
                for param_key, param_template in variatic_params.items():
                    # The param_key becomes the column name
                    column_name = param_key
                    
                    # Initialize the new column with empty values
                    new_column_values = []
                    
                    # For each row in the dataframe
                    for idx, row in df.iterrows():
                        # Find all placeholders in angle brackets in the template
                        placeholders = re.findall(r'<([^>]+)>', param_template)
                        
                        # Replace placeholders with actual values from the row
                        expanded_value = param_template
                        all_placeholders_filled = True
                        
                        for placeholder in placeholders:
                            if placeholder in df.columns:
                                # Get the value from the current row for this placeholder
                                placeholder_value = row[placeholder]
                                if pd.notna(placeholder_value) and str(placeholder_value).strip():
                                    expanded_value = expanded_value.replace(f'<{placeholder}>', str(placeholder_value))
                                else:
                                    # If the value is NaN or empty, we can't fill this template
                                    all_placeholders_filled = False
                                    break
                            else:
                                # Placeholder column doesn't exist
                                all_placeholders_filled = False
                                break
                        
                        # Only set the value if all placeholders were successfully filled
                        if all_placeholders_filled and expanded_value != param_template:
                            new_column_values.append(expanded_value)
                        else:
                            new_column_values.append("")
                    
                    # Add the new column to the dataframe
                    df[column_name] = new_column_values
                
                print(f"Expanded CSV shape: {df.shape}")
                print(f"New columns added: {list(variatic_params.keys())}")
                
                csv_string = df.to_csv(index=False)
                return csv_string

            def mapper(col, map = self.param_mapping[template.name]):
                return map.get(col,col)
            
            # NOTE: patch for missing bmotif feature, should be able to ingest these as values
            def change_ns(graph):
                add = []
                remove = []
                for s,o in graph.subject_objects(QUDT.hasUnit):
                    if str(o).startswith(str(self.building_ns)):
                        remove.append((s, QUDT.hasUnit, o))
                        add.append((s, QUDT.hasUnit, URIRef(str(o).replace(str(self.building_ns),str(UNIT)))))
                for s,o in graph.subject_objects(BRICK.value):
                    if str(o).startswith(str(self.building_ns)):
                        remove.append((s, BRICK.value, o))
                        add.append((s, BRICK.value, Literal(str(o).replace(str(self.building_ns),""))))
                for s,o in graph.subject_objects(S223.hasValue):
                    if str(o).startswith(str(self.building_ns)):
                        remove.append((s, S223.hasValue, o))
                        add.append((s, S223.hasValue, Literal(str(o).replace(str(self.building_ns),""))))
                for triple in add:
                    graph.add(triple)
                for triple in remove:
                    graph.remove(triple)

            file = str(self.base_dir / filename) + ".csv"
            csv_string = fill_variatic_params(file, self.variatic_params[template.name])
            csv_in = CSVIngress(data = csv_string)
            ingress = TemplateIngress(template, mapper, csv_in)
            #NOTE: Ingress puts everything into the given namespace, will have to change unit namespaces manually 
            graph = ingress.graph(self.building_ns)
            change_ns(graph)
            self.graph += graph
        if serialize:
            self.graph.serialize(self.base_dir / f'{self.building_id}.ttl')


    def _create_csv(self, file_name, template):
        """Create CSV file from template"""
        template = template
        file = str(self.base_dir / file_name) + ".csv"
        template.generate_csv(file)
        mapping = self.param_mapping[template.name]
        remove_params = self.variatic_params[template.name]
        self._edit_cols(file, mapping, remove_params)
        return file 

    def _edit_cols(self, file, mapping, remove_params, first_col='name'):
        """Edit column names in CSV file"""
        df = pd.read_csv(file)
        param_to_new_name = {v:k for k,v in mapping.items()}
        new_cols = [param_to_new_name.get(first_col, first_col)] + [param_to_new_name.get(col, col) for col in df.columns if col != first_col]
        new_cols = [col for col in new_cols if col not in remove_params]
        df = pd.DataFrame(columns = new_cols)
        df.to_csv(file, index=False)

    def _create_point_list(self):
        """Create csv-file to which point list should be added"""
        headers = ["point_of", "point_type", "point_name", "quantitykind", "unit"]
        with open(self.base_dir / f"point_list.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

class HPFlexSurvey(Survey):
    """
    Specialized generator for building structures with HVAC, zones, spaces, and windows.
    This class extends Survey with specific functionality for building systems.
    """
    # TODO: update to use template_dict
    def __init__(self, site_id, building_id, output_dir, system_of_units="IP", ontology='brick', 
                 template_dict={'zone':'hvac-zone',"space":"space", "hvac":"hp-rtu", "tstat":"tstat", "window":"window", "site":"site"}, overwrite=False):
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
            self.default_angle_unit = "Degree"  # degrees for tilt and azimuth
            self.default_cop_unit = "UNITLESS"  # COP is dimensionless
            self.default_power_unit = "BTU_IT-PER-HR"  # BTU/hr for IP system
        else:
            self.default_area_unit = "M2"
            self.default_temperature_unit = "DEG_C"
            self.default_angle_unit = "Degree"  # degrees for tilt and azimuth
            self.default_cop_unit = "UNITLESS"  # COP is dimensionless
            self.default_power_unit = "KiloW"  # kW for SI system
        
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

        config = self._building_structure(
            self.hvacs_feed_hvacs,
            self.hvacs_feed_zones,
            self.zones_contain_spaces,
            self.zones_contain_windows,
        )
        
        # Prefill CSV files with data from config
        self._prefill_csv_defaults(config)

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

        # Save configuration
        config = {
            "site_id": self.site_id,
            "hvac_type": self.hvac_type,
            "variatic_params": self.variatic_params,
            "param_mapping": self.param_mapping,
            "hvacs_feed_hvacs": hvacs_feed_hvacs,
            "hvacs_feed_zones": hvacs_feed_zones,
            "zones_contain_spaces": zones_contain_spaces,
            "zones_contain_windows": zones_contain_windows,
        }
        print(config)
        with open(self.base_dir / "config.json", "w") as f:
            json.dump(config, f, indent=4)
        return config

    # TODO: prefill should use mapper to generalize better
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
        
        if 'site' in self.template_csvs:
            self._prefill_site_csv(self.site_id)

        # TODO: can lead with this. May not need to do the whole hvacs_feed_hvacs, hvacs_feed_zones config, since this info covers that
        if 'zone' in self.template_csvs and 'zones_contain_windows' in config and 'zones_contain_spaces' in config and 'hvacs_feed_zones' in config:
            self._prefill_zone_csv(config)
    
    # tstat should be handled more like other things
    # Everything highly customized in this function
    # Adding and filling this in is redundant with the rest of the config, but the information makes less sence as a table
    def _prefill_zone_csv(self,config):
        space_file = self.template_csvs['zone']
        
        # Read existing CSV to get column structure
        existing_df = pd.read_csv(space_file)
        columns = existing_df.columns.tolist()
        new_rows = []
        extra_rows = []
        for zone_name, spaces in config["zones_contain_spaces"].items():
            # Start with empty row
            row = {col: '' for col in columns}

            if 'tstat-name' in columns:
                row['tstat-name'] = f"tstat_{zone_name}"

            hvacs = config['hvacs_feed_zones']
            for hvac_name, hvac_zone_names in hvacs.items():
                if not isinstance(hvac_zone_names, list):
                    raise TypeError(f"Expected hvac_zone_names {hvac_zone_names} to be a list, instead {type(hvac_zone_names)}")
                if zone_name in hvac_zone_names:
                    if 'hvac-name' in columns:
                        row['hvac-name'] = hvac_name
            if 'name' in columns:
                row['name'] = zone_name

            for i, space_name in enumerate(spaces):
                if i>0:
                    extra_row = {col: '' for col in columns}
                    extra_row['name'] = zone_name
                    if 'space-name' in columns:
                        extra_row['space-name'] = space_name
                    extra_rows.append(extra_row)
                else:
                    if 'space-name' in columns:
                        row['space-name'] = space_name

            windows = config['zones_contain_windows'][zone_name]
            for window_name in windows:
                if i>0:
                    extra_row = {col: '' for col in columns}
                    extra_row['name'] = zone_name
                    if 'window-name' in columns:
                        extra_row['window-name'] = window_name
                    extra_rows.append(extra_row)
                else:
                    if 'window-name' in columns:
                        row['window-name'] = window_name

            new_rows.append(row)
        new_rows = new_rows + extra_rows
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows, columns=columns)
        new_df.to_csv(space_file, index=False)
    def _prefill_space_csv(self, zones_contain_spaces):
        """Prefill space CSV with space names and default values"""
        space_file = self.template_csvs['space']
        
        # Read existing CSV to get column structure
        existing_df = pd.read_csv(space_file)
        columns = existing_df.columns.tolist()
        
        # Create new rows with only the values we want to prefill
        new_rows = []
        for zone_name, spaces in zones_contain_spaces.items():
            for space_name in spaces:
                # Start with empty row
                row = {col: '' for col in columns}
                # Only set the values we want to prefill
                row['name'] = space_name
                if 'area-name-unit' in columns:
                    row['area-name-unit'] = self.default_area_unit
                new_rows.append(row)
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows, columns=columns)
        new_df.to_csv(space_file, index=False)

    def _prefill_window_csv(self, zones_contain_windows):
        """Prefill window CSV with window names and default values"""
        window_file = self.template_csvs['window']
        
        # Read existing CSV to get column structure
        existing_df = pd.read_csv(window_file)
        columns = existing_df.columns.tolist()
        
        # Create new rows with only the values we want to prefill
        new_rows = []
        for zone_name, windows in zones_contain_windows.items():
            for window_name in windows:
                # Start with empty row
                row = {col: '' for col in columns}
                # Only set the values we want to prefill
                row['name'] = window_name
                if 'area-name-unit' in columns:
                    row['area-name-unit'] = self.default_area_unit
                if 'tilt-name-unit' in columns:
                    row['tilt-name-unit'] = self.default_angle_unit
                if 'azimuth-name-unit' in columns:
                    row['azimuth-name-unit'] = self.default_angle_unit
                new_rows.append(row)
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows, columns=columns)
        new_df.to_csv(window_file, index=False)

    def _prefill_hvac_csv(self, hvacs_feed_zones):
        """Prefill HVAC CSV with HVAC unit names and default values"""
        hvac_file = self.template_csvs['hvac']
        
        # Read existing CSV to get column structure
        existing_df = pd.read_csv(hvac_file)
        columns = existing_df.columns.tolist()
        
        # Create new rows with only the values we want to prefill
        new_rows = []
        for hvac_name in hvacs_feed_zones.keys():
            # Start with empty row
            row = {col: '' for col in columns}
            # Only set the values we want to prefill
            row['name'] = hvac_name
            
            # Set default units for the newly parameterized units
            if 'cooling_COP-name-unit' in columns:
                row['cooling_COP-name-unit'] = self.default_cop_unit
            if 'heating_COP-name-unit' in columns:
                row['heating_COP-name-unit'] = self.default_cop_unit
            if 'cooling_capacity-name-unit' in columns:
                row['cooling_capacity-name-unit'] = self.default_power_unit
            if 'heating_capacity-name-unit' in columns:
                row['heating_capacity-name-unit'] = self.default_power_unit
                
            new_rows.append(row)
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows, columns=columns)
        new_df.to_csv(hvac_file, index=False)

    def _prefill_tstat_csv(self, hvacs_feed_zones):
        """Prefill thermostat CSV with thermostat names (one per zone) and default values"""
        tstat_file = self.template_csvs['tstat']
        
        # Read existing CSV to get column structure
        existing_df = pd.read_csv(tstat_file)
        columns = existing_df.columns.tolist()
        
        # Create new rows with only the values we want to prefill
        new_rows = []
        for hvac_name, zones in hvacs_feed_zones.items():
            for zone_name in zones:
                # Start with empty row
                row = {col: '' for col in columns}
                # Only set the values we want to prefill
                row['name'] = f"tstat_{zone_name}"
                # Set temperature unit columns if they exist
                if 'setpoint_deadband-name-unit' in columns:
                    row['setpoint_deadband-name-unit'] = self.default_temperature_unit
                if 'tolerance-name-unit' in columns:
                    row['tolerance-name-unit'] = self.default_temperature_unit
                if 'resolution-name-unit' in columns:
                    row['resolution-name-unit'] = self.default_temperature_unit
                new_rows.append(row)
        
        # Create new dataframe with prefilled data
        new_df = pd.DataFrame(new_rows, columns=columns)
        new_df.to_csv(tstat_file, index=False)
    
    def _prefill_site_csv(self, site_id):
        """Prefill thermostat CSV with thermostat names (one per zone) and default values"""
        site_file = self.template_csvs['site']
        
        # Read existing CSV to get column structure
        existing_df = pd.read_csv(site_file)
        columns = existing_df.columns.tolist()
        
        # Create new rows with only the values we want to prefill
        new_rows = []
        row = {col: '' for col in columns}
        row['name'] = site_id
        new_rows.append(row)
        new_df = pd.DataFrame(new_rows, columns=columns)
        new_df.to_csv(site_file, index=False)

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
