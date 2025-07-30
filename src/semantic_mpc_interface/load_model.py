import os
import re
import pandas as pd
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass, field

from rdflib import Graph, Literal, Namespace, URIRef
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model

from .namespaces import *
from .unit_conversion import convert_units
from .utils import *

# Unit, to unit, and if delta quantity
UNIT_CONVERSIONS = {
    UNIT["DEG_F"]: UNIT["DEG_C"],
    UNIT["FT"]: UNIT["M"],
    UNIT["FT2"]: UNIT["M2"],
    UNIT["FT3"]: UNIT["M3"],
    UNIT["PSI"]: UNIT["PA"],
}

# TODO: Still in vibe coded state - should clean up and generalize a little
class Value:
    def __init__(self, value, unit, is_delta = False, name=None):
        # Try to convert to float, but keep as string if it fails
        if value is not None:
            try:
                self.value = float(value)
            except (ValueError, TypeError):
                self.value = str(value)
        else:
            self.value = None
            
        self.unit = str(unit).replace('unit:', '') if unit is not None else None
        self.name = name
        self.is_delta = is_delta
    def __repr__(self):
        return f"Value(value={self.value}, unit='{self.unit}')"

    def convert_to_si(self):
        if URIRef(self.unit) in UNIT_CONVERSIONS.keys():
            new_units = UNIT_CONVERSIONS[URIRef(self.unit)]
            self.value = convert_units((self.value), URIRef(self.unit), URIRef(new_units), self.is_delta)
            self.unit = new_units

class LoadModel:
    # Could do all alignment through templates by redefining mapping brick and s223 to hpf namespace, but this seems onerous
    def __init__(self, source: Union[str, Graph], ontology: str, template_dict = {
            'sites': 'site',
            'zones': 'hvac-zone',}, as_si_units = False):
        if os.path.isfile(source):
            self.g = Graph(store = 'Oxigraph')
            self.g.parse(source)
        elif isinstance(source, Graph):
            self.g = source
        else:
            raise ValueError("Source must be a file path or an RDF graph.")
        bind_prefixes(self.g)
        BRICK = Namespace("https://brickschema.org/schema/Brick#")
        self.HPF = Namespace("urn:hpflex#")
        self.site = self.g.value(None, RDF.type, BRICK.Site)
        self.ontology = ontology
        self.template_dict = template_dict
        self.as_si_units = as_si_units
        # Only one query so far requires loading the ontology to use subClassOf in 223:
        if ontology == "s223":
            self.g.parse("https://open223.info/223p.ttl", format="ttl")
            
        # Initialize BuildingMOTIF components
        self.bm = BuildingMOTIF("sqlite://")
        self.model = Model.create(self.HPF)
        self.library = Library.load(directory=brick_templates)

    def _get_var_name(self, graph, node):
        """Generate variable names for SPARQL queries from RDF nodes."""
        if isinstance(node, Literal):
            return node
        pre, ns, local = graph.compute_qname(node)
        if PARAM == ns:
            q_n = f"?{local}".replace('-','_')
        else:
            q_n = convert_to_prefixed(node, graph).replace('-','_')
        return q_n

    def _make_where(self, graph):
        """Generate WHERE clause for SPARQL query from RDF graph."""
        where = []
        for s, p, o in graph.triples((None, None, None)):
            qs = self._get_var_name(graph, s)
            qo = self._get_var_name(graph, o)
            qp = convert_to_prefixed(p, graph).replace('-','_')
            where.append(f"{qs} {qp} {qo} .")
        return "\n".join(where)

    def _get_query(self, graph):
        """Generate complete SPARQL query from RDF graph."""
        where = self._make_where(graph)
        prefixes = get_prefixes(graph)
        query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {where} }}"""
        return query

    def _extract_attributes_from_template(self, template_name: str) -> Dict[str, str]:
        """
        Extract attribute information from a template by analyzing its dependencies.
        Returns a dictionary mapping attribute names to their types.
        """
        template = self.library.get_template_by_name(template_name)
        if not template:
            return {}
        
        attributes = {}
        
        # Get the template with inlined dependencies to see all attributes
        inlined = template.inline_dependencies()
        
        # Parse the RDF graph to find properties
        for s, p, o in inlined.body.triples((None, None, None)):
            # Look for properties that connect the main entity to values
            predicate_str = str(p)
            object_str = str(o)
            
            # Skip namespace declarations and type assertions
            if 'type' in predicate_str.lower() or predicate_str.endswith('#type'):
                continue
                
            # Look for brick properties that indicate attributes
            if 'brick' in predicate_str and ('area' in predicate_str.lower() or 
                                            'azimuth' in predicate_str.lower() or 
                                            'tilt' in predicate_str.lower() or
                                            'capacity' in predicate_str.lower() or
                                            'coefficient' in predicate_str.lower() or
                                            'point' in predicate_str.lower() or
                                            'location' in predicate_str.lower() or
                                            'part' in predicate_str.lower()):
                
                # Extract attribute name from the object (parameter name)
                if 'param' in object_str:
                    attr_name = object_str.split('#')[-1] if '#' in object_str else object_str.split('/')[-1]
                    attr_name = attr_name.replace('-', '_')
                    
                    # Determine if this is a Value type or simple type
                    if any(val_type in predicate_str.lower() for val_type in ['area', 'azimuth', 'tilt', 'capacity', 'coefficient']):
                        attributes[attr_name] = 'Value'
                    else:
                        attributes[attr_name] = 'str'
        
        return attributes

    def _create_dynamic_class(self, class_name: str, attributes: Dict[str, str]) -> Type:
        """
        Dynamically create a class with the specified attributes.
        """
        def __init__(self, name: str, **kwargs):
            self.name = name
            for attr_name, attr_type in attributes.items():
                # Skip 'name' attribute to avoid conflict with the positional name parameter
                if attr_name != 'name':
                    setattr(self, attr_name, kwargs.get(attr_name))
        
        def __repr__(self):
            attr_strs = [f"{attr}={getattr(self, attr, None)}" for attr in attributes.keys() if attr != 'name']
            return f"{class_name}(name='{self.name}', {', '.join(attr_strs)})"
        
        # Create the class dynamically
        cls = type(class_name, (), {
            '__init__': __init__,
            '__repr__': __repr__,
            '_attributes': attributes
        })
        
        return cls

    def _identify_entity_attributes(self, df: pd.DataFrame, entity_name: str) -> Dict[str, Any]:
        """
        Identify attributes for an entity based on column patterns in the dataframe.
        Added delta quantity after the fact - fairly disconnected
        """
        attributes = {}
        
        # Look for columns that match the pattern: {entity_name}_{attribute}_{type}
        pattern = rf"{re.escape(entity_name)}_(.+?)_(value|unit|name)$"
        
        attribute_bases = set()
        for col in df.columns:
            match = re.match(pattern, col)
            if match:
                attr_base = match.group(1)
                attribute_bases.add(attr_base)
        
        # For each attribute base, try to create a Value object
        for attr_base in attribute_bases:
            name_col = f"{entity_name}_{attr_base}"
            value_col = f"{entity_name}_{attr_base}_value"
            unit_col = f"{entity_name}_{attr_base}_unit"
            
            # Check if we have meaningful data in the _name column (prefer this)
            # TODO: This code never seems to be run, only backup code is. Should double check why. 
            if name_col in df.columns and not df.empty and pd.notna(df[name_col].iloc[0]):
                name_data = df[name_col].iloc[0]
                value_data = df[value_col].iloc[0]
                # Only create attribute if the _name column contains actual numeric/meaningful data
                # Skip if it contains URI strings
                if not str(value_data).startswith('urn:') and not '-name' in str(value_data):
                    try:
                        # Try to convert to number to verify it's meaningful data
                        float(value_data)
                        unit_data = df[unit_col].iloc[0] if unit_col in df.columns and pd.notna(df[unit_col].iloc[0]) else None
                        # get is delta
                        is_delta = self._is_delta_quantity(name_data)
                        value_obj = Value(value=value_data, unit=unit_data, is_delta = is_delta, name=name_data)
                        if self.as_si_units:
                            value_obj.convert_to_si()
                        # Use clean attribute name (remove redundant prefixes and suffixes)
                        clean_attr_name = attr_base.replace('name_', '').replace('_name', '')
                        attributes[clean_attr_name] = value_obj
                    except (ValueError, TypeError):
                        # Skip non-numeric data in _name columns
                        pass
            
        # Also look for simple string attributes (columns that end with the entity name)
        for col in df.columns:
            if col == entity_name and col not in attributes:
                if not df.empty:
                    attributes[col] = df[col].iloc[0]
        
        return attributes

    def _create_container_class(self, container_name: str, contained_types: List[str]) -> Type:
        """
        Create a container class (like Zone) that can hold multiple types of entities.
        """
        def __init__(self, name: str):
            self.name = name
            for entity_type in contained_types:
                setattr(self, f"{entity_type.lower()}s", [])
        
        def __repr__(self):
            counts = []
            for entity_type in contained_types:
                attr_name = f"{entity_type.lower()}s"
                count = len(getattr(self, attr_name, []))
                counts.append(f"{entity_type.lower()}s={count}")
            return f"{container_name}(name='{self.name}', {', '.join(counts)})"
        
        # Add methods to add entities
        def create_add_method(entity_type):
            def add_method(self, entity):
                attr_name = f"{entity_type.lower()}s"
                getattr(self, attr_name).append(entity)
            return add_method
        
        methods = {'__init__': __init__, '__repr__': __repr__}
        for entity_type in contained_types:
            methods[f"add_{entity_type.lower()}"] = create_add_method(entity_type)
        
        cls = type(container_name, (), methods)
        return cls

    def _is_delta_quantity(self, uri):
        is_delta = self.g.value(URIRef(uri), QUDT["isDeltaQuantity"])
        return bool(is_delta)
        # return True if is_delta == URIRef('true') else False

    def _dataframe_to_objects_generalized(self, df: pd.DataFrame, template_name: str):
        """
        Convert dataframe results into objects based on template structure.
        This is a generalized version that works with any template.
        """
        if df.empty:
            return []
        
        # Get the main entity name (usually the first column or 'name')
        main_entity_col = 'name' if 'name' in df.columns else df.columns[0]
        
        # Identify all entity types in the dataframe by looking at column patterns
        entity_types = set()
        for col in df.columns:
            # Look for patterns like "entity_name" or "entity_name_attribute_type"
            if '_' in col:
                parts = col.split('_')
                if len(parts) >= 2 and parts[-1] in ['name', 'value', 'unit']:
                    # This might be an entity attribute
                    if len(parts) == 2:  # entity_name
                        entity_types.add(parts[0])
                    elif len(parts) >= 3:  # entity_attribute_type
                        entity_types.add(parts[0])
            else:
                # Simple column name might be an entity
                if col != main_entity_col:
                    entity_types.add(col)
        
        # Remove the main entity from the list if it's there
        main_entity_name = template_name.replace('-', '_')
        entity_types.discard(main_entity_name)
        entity_types.discard('name')
        
        # Create classes for each entity type
        entity_classes = {}
        for entity_type in entity_types:
            # Get attributes for this entity type from the dataframe
            sample_attributes = self._identify_entity_attributes(df, entity_type)
            attr_types = {attr: 'Value' if isinstance(val, Value) else 'str' 
                         for attr, val in sample_attributes.items()}
            
            entity_classes[entity_type] = self._create_dynamic_class(
                entity_type.capitalize(), attr_types
            )
        
        # Create container class
        container_class = self._create_container_class(
            main_entity_name.replace('_', '').capitalize(), 
            [et.capitalize() for et in entity_types]
        )
        
        # Process the dataframe
        containers = {}
        
        for _, row in df.iterrows():
            container_name = row[main_entity_col]
            
            # Create container if it doesn't exist
            if container_name not in containers:
                containers[container_name] = container_class(container_name)
            
            container = containers[container_name]
            
            # Create entities for each type
            for entity_type in entity_types:
                entity_name_col = f"{entity_type}_name" if f"{entity_type}_name" in df.columns else entity_type
                
                if entity_name_col in row and pd.notna(row[entity_name_col]):
                    entity_name = row[entity_name_col]
                    
                    # Get attributes for this entity
                    entity_attributes = self._identify_entity_attributes(pd.DataFrame([row]), entity_type)
                    
                    # Remove 'name' from entity_attributes to avoid conflict with positional name parameter
                    filtered_attributes = {k: v for k, v in entity_attributes.items() if k != 'name'}
                    
                    # Create entity instance
                    entity_class = entity_classes[entity_type]
                    entity = entity_class(name=entity_name, **filtered_attributes)
                    
                    # Add to container (check for duplicates)
                    entities_list = getattr(container, f"{entity_type}s")
                    if not any(e.name == entity.name for e in entities_list):
                        add_method = getattr(container, f"add_{entity_type}")
                        add_method(entity)
        
        return list(containers.values())

    def _get_objects_generalized(self, template_name: str = 'hvac-zone'):
        """
        Generalized function to get objects from any template.
        """
        template = self.library.get_template_by_name(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        template_inlined = template.inline_dependencies()
        query = self._get_query(template_inlined.body)
        df = query_to_df(query, self.g, prefixed=False)
        objects = self._dataframe_to_objects_generalized(df, template_name)
        return objects

    def get_objects_from_templates(self, template_dict) -> Dict[str, List]:
        """
        Get objects from specified templates.
        
        Args:
            template_dict: Dictionary mapping result keys to template names
                          e.g., {'zone': 'hvac-zone', 'site': 'site'}
        
        Returns:
            Dictionary with keys from template_dict and lists of objects as values
        """
        results = {}
        
        for result_key, template_name in template_dict.items():
            try:
                objects = self._get_objects_generalized(template_name)
                results[result_key] = objects
            except Exception as e:
                print(f"Warning: Could not retrieve objects for template '{template_name}': {e}")
                results[result_key] = []
        
        return results

    def get_all_building_objects(self, convert_to_si_units = True):
        """
        Get all building objects including site and hvac zones.
        Returns a dictionary with object types as keys.
        """
        # Get objects from all templates
        all_objects = self.get_objects_from_templates(self.template_dict)

        # Filter out empty results to maintain backward compatibility
        results = {}
        for key, objects in all_objects.items():
            if objects:  # Only include if we got results
                results[key] = objects
        
        # Convert all objects to SI units if requested
        return results

    def list_available_templates(self):
        """
        List all available templates in the library.
        """
        return [template.name for template in self.library.get_templates()]

    def get_thermostat_data(self, for_zone_list: Optional[List[str]] = None) -> Dict:
        """
        Generate thermostat metadata similar to BuildingMetadataLoader.get_thermostat_data()
        but using the object-oriented approach from LoadModel.
        
        Args:
            for_zone_list: Optional list of zone IDs to filter by
            
        Returns:
            Dictionary with thermostat metadata organized in lists
        """
        # Initialize the output dictionary with empty lists
        thermostat_data = {
            "heat_availability": [],
            "cool_availability": [],
            "heat_tolerance": [],
            "cool_tolerance": [],
            "setpoint_deadband": [],
            "active": [],
            "control_group": [],
            "control_type_list": [],
            "floor_area_list": [],
            "floor_area_unit": [],
            "window_area_list": [],
            "window_area_unit": [],
            "azimuth_list": [],
            "azimuth_unit": [],
            "tilt_list": [],
            "tilt_unit": [],
            "zone_ids": [],
            "hvacs": [],
            "setpoint_type": [],
            "fuel_heat_list": [],
            "fuel_cool_list": [],
            "cooling_capacity": [],
            "cooling_capacity_unit": [],
            "heating_capacity": [],
            "heating_capacity_unit": [],
            "cooling_cop": [],
            "heating_cop": [],
            "cooling_electricity": [],
            "heating_electricity": [],
            "resolution": [],
            "temperature_unit": [],
        }
        
        # Get all building objects
        all_objects = self.get_all_building_objects()
        
        # Process zones if they exist
        if 'zones' in all_objects:
            for zone in all_objects['zones']:
                # Filter by zone list if provided
                if for_zone_list is not None:
                    zone_id = zone.name.split('#')[-1] if '#' in zone.name else zone.name
                    if zone_id not in for_zone_list:
                        continue
                
                # Process each thermostat in the zone
                if hasattr(zone, 'tstats') and zone.tstats:
                    for tstat in zone.tstats:
                        # Extract zone ID
                        zone_id = zone.name.split('#')[-1] if '#' in zone.name else zone.name
                        thermostat_data["zone_ids"].append(zone_id)
                        
                        # Process thermostat properties
                        if hasattr(tstat, 'tolerance') and tstat.tolerance:
                            tolerance_val = tstat.tolerance.value if hasattr(tstat.tolerance, 'value') else 0.0
                            thermostat_data["heat_tolerance"].append(-1.0 * tolerance_val)
                            thermostat_data["cool_tolerance"].append(1.0 * tolerance_val)
                        else:
                            thermostat_data["heat_tolerance"].append(0.0)
                            thermostat_data["cool_tolerance"].append(0.0)
                        
                        if hasattr(tstat, 'setpoint_deadband') and tstat.setpoint_deadband:
                            deadband_val = tstat.setpoint_deadband.value if hasattr(tstat.setpoint_deadband, 'value') else 0.0
                            thermostat_data["setpoint_deadband"].append(deadband_val)
                        else:
                            thermostat_data["setpoint_deadband"].append(0.0)
                        
                        if hasattr(tstat, 'active') and tstat.active:
                            active_val = tstat.active.value if hasattr(tstat.active, 'value') else True
                            thermostat_data["active"].append(bool(active_val))
                        else:
                            thermostat_data["active"].append(True)
                        
                        if hasattr(tstat, 'stage_count') and tstat.stage_count:
                            stage_count = tstat.stage_count.value if hasattr(tstat.stage_count, 'value') else 1
                            thermostat_data["control_type_list"].append("binary" if stage_count == 1 else "stage")
                        else:
                            thermostat_data["control_type_list"].append("binary")
                        
                        if hasattr(tstat, 'resolution') and tstat.resolution:
                            resolution_val = tstat.resolution.value if hasattr(tstat.resolution, 'value') else 1.0
                            thermostat_data["resolution"].append(resolution_val)
                            
                            # Determine temperature unit from resolution unit
                            if hasattr(tstat.resolution, 'unit') and tstat.resolution.unit:
                                unit_str = str(tstat.resolution.unit).upper()
                                if 'DEG_F' in unit_str or 'FAHRENHEIT' in unit_str:
                                    thermostat_data["temperature_unit"].append('IP')
                                else:
                                    thermostat_data["temperature_unit"].append('SI')
                            else:
                                thermostat_data["temperature_unit"].append('SI')
                        else:
                            thermostat_data["resolution"].append(1.0)
                            thermostat_data["temperature_unit"].append('SI')
                        
                        # Default values for control group and setpoint type
                        thermostat_data["control_group"].append("DEPRECATED")
                        thermostat_data["setpoint_type"].append("double")  # Default assumption
                        
                        # Process HVAC data
                        if hasattr(zone, 'hvacs') and zone.hvacs:
                            hvac = zone.hvacs[0]  # Take first HVAC unit
                            hvac_id = hvac.name.split('#')[-1] if '#' in hvac.name else hvac.name
                            thermostat_data["hvacs"].append(hvac_id)
                            
                            # Cooling capacity
                            if hasattr(hvac, 'cooling_capacity') and hvac.cooling_capacity:
                                cooling_cap = hvac.cooling_capacity.value if hasattr(hvac.cooling_capacity, 'value') else 0.0
                                thermostat_data["cooling_capacity"].append(cooling_cap)
                                
                                if hasattr(hvac.cooling_capacity, 'unit') and hvac.cooling_capacity.unit:
                                    unit_str = str(hvac.cooling_capacity.unit).split('/')[-1]
                                    thermostat_data["cooling_capacity_unit"].append(unit_str)
                                else:
                                    thermostat_data["cooling_capacity_unit"].append("W")
                            else:
                                thermostat_data["cooling_capacity"].append(0.0)
                                thermostat_data["cooling_capacity_unit"].append("W")
                            
                            # Heating capacity
                            if hasattr(hvac, 'heating_capacity') and hvac.heating_capacity:
                                heating_cap = hvac.heating_capacity.value if hasattr(hvac.heating_capacity, 'value') else 0.0
                                thermostat_data["heating_capacity"].append(heating_cap)
                                
                                if hasattr(hvac.heating_capacity, 'unit') and hvac.heating_capacity.unit:
                                    unit_str = str(hvac.heating_capacity.unit).split('/')[-1]
                                    thermostat_data["heating_capacity_unit"].append(unit_str)
                                else:
                                    thermostat_data["heating_capacity_unit"].append("W")
                            else:
                                thermostat_data["heating_capacity"].append(0.0)
                                thermostat_data["heating_capacity_unit"].append("W")
                            
                            # COP values
                            if hasattr(hvac, 'cooling_COP') and hvac.cooling_COP:
                                cooling_cop = hvac.cooling_COP.value if hasattr(hvac.cooling_COP, 'value') else 3.0
                                thermostat_data["cooling_cop"].append(cooling_cop)
                            else:
                                thermostat_data["cooling_cop"].append(3.0)
                            
                            if hasattr(hvac, 'heating_COP') and hvac.heating_COP:
                                heating_cop = hvac.heating_COP.value if hasattr(hvac.heating_COP, 'value') else 3.0
                                thermostat_data["heating_cop"].append(heating_cop)
                            else:
                                thermostat_data["heating_cop"].append(3.0)
                        else:
                            # Default HVAC values
                            thermostat_data["hvacs"].append("unknown")
                            thermostat_data["cooling_capacity"].append(0.0)
                            thermostat_data["cooling_capacity_unit"].append("W")
                            thermostat_data["heating_capacity"].append(0.0)
                            thermostat_data["heating_capacity_unit"].append("W")
                            thermostat_data["cooling_cop"].append(3.0)
                            thermostat_data["heating_cop"].append(3.0)
                        
                        # Process space data (floor area)
                        total_floor_area = 0.0
                        floor_area_unit = "M2"
                        if hasattr(zone, 'spaces') and zone.spaces:
                            for space in zone.spaces:
                                if hasattr(space, 'area') and space.area:
                                    area_val = space.area.value if hasattr(space.area, 'value') else 0.0
                                    total_floor_area += area_val
                                    
                                    if hasattr(space.area, 'unit') and space.area.unit:
                                        unit_str = str(space.area.unit).split('/')[-1]
                                        floor_area_unit = unit_str
                        
                        thermostat_data["floor_area_list"].append(total_floor_area)
                        thermostat_data["floor_area_unit"].append(floor_area_unit)
                        
                        # Process window data (take largest window by area)
                        largest_window_area = 0.0
                        window_area_unit = "M2"
                        window_azimuth = 0.0
                        window_tilt = 0.0
                        
                        if hasattr(zone, 'windows') and zone.windows:
                            for window in zone.windows:
                                if hasattr(window, 'area') and window.area:
                                    area_val = window.area.value if hasattr(window.area, 'value') else 0.0
                                    if area_val > largest_window_area:
                                        largest_window_area = area_val
                                        
                                        if hasattr(window.area, 'unit') and window.area.unit:
                                            unit_str = str(window.area.unit).split('/')[-1]
                                            window_area_unit = unit_str
                                        
                                        if hasattr(window, 'azimuth') and window.azimuth:
                                            window_azimuth = window.azimuth.value if hasattr(window.azimuth, 'value') else 0.0
                                        
                                        if hasattr(window, 'tilt') and window.tilt:
                                            window_tilt = window.tilt.value if hasattr(window.tilt, 'value') else 0.0
                        
                        thermostat_data["window_area_list"].append(largest_window_area)
                        thermostat_data["window_area_unit"].append(window_area_unit)
                        thermostat_data["azimuth_list"].append(window_azimuth)
                        thermostat_data["azimuth_unit"].append("DEGREE")
                        thermostat_data["tilt_list"].append(window_tilt)
                        thermostat_data["tilt_unit"].append("DEGREE")
                        
                        # Default fuel and availability assumptions (electric heat pump)
                        thermostat_data["fuel_heat_list"].append("electricity")
                        thermostat_data["fuel_cool_list"].append("electricity")
                        thermostat_data["heat_availability"].append(True)
                        thermostat_data["cool_availability"].append(True)
                        thermostat_data["cooling_electricity"].append(True)
                        thermostat_data["heating_electricity"].append(True)
        
        return thermostat_data
