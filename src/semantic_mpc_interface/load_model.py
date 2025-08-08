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
    UNIT['BTU_IT-PER-HR']:UNIT['KiloW'],
}

def build_tree(graph):
    def dfs(node, visited):
        if node in visited:
            return {}  # Prevent cycles
        visited.add(node)
        children = graph.get(node, [])
        return {child: dfs(child, visited.copy()) for child in children}

    # Determine root nodes (not referenced as values)
    all_nodes = set(graph.keys())
    referenced = {child for children in graph.values() for child in children}
    roots = all_nodes - referenced

    tree = {}
    for root in roots:
        tree[root] = dfs(root, set())
    return tree

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
        #TODO: Consider changing to just template list. Renaming of templates is not important nor consistent
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
        if ontology == 'brick':
            self.library = Library.load(directory=brick_templates)
        elif ontology == 's223':
            self.library = Library.load(directory=s223_templates)
        else:
            raise ValueError('invalid ontology')

    def _get_var_name(self, graph, node, force_as_variable = False):
        """Generate variable names for SPARQL queries from RDF nodes."""
        if isinstance(node, Literal):
            return node
        pre, ns, local = graph.compute_qname(node)
        if (PARAM == ns) or force_as_variable:
            q_n = f"?{local}".replace('-','_')
        else:
            q_n = convert_to_prefixed(node, graph) #.replace('-','_')
        return q_n
    
    # TODO: Doing some unnecessary querying that I then re-query. can optimize and reduce query size, also make less brittle
    # TODO: May be good to use additional results from templates to make sure I'm returning all entities
    # TODO: SPARQL has issue with enumeration kinds. Either reimplement logic to get correct SPARQL results or use information inferred from SHACL. 
    # TODO: Going to implement a temporary patch for this - maybe just by adding HPFS classes from templates
    def _make_where(self, graph):
        """Generate WHERE clause for SPARQL query from RDF graph."""
        where = []
        filters = {}
        for s, p, o in graph.triples((None, None, None)):
            qs = self._get_var_name(graph, s)
            qo = self._get_var_name(graph, o)
            qp = convert_to_prefixed(p, graph) #.replace('-','_')
            if p == S223['hasAspect'] and (s not in filters.keys()):
                aspects = list(graph.objects(s,p))
                aspects = [self._get_var_name(graph,a) for a in aspects]
                aspect_var = qs + '_aspects_in'
                where.append(f"{qs} {qp} {aspect_var} .")
                filters[s] = f"FILTER({aspect_var} IN ({','.join(aspects)}) ) "
            where.append(f"{qs} {qp} {qo} .")
        where += list(filters.values())
        return "\n".join(where)

    def _get_query(self, graph):
        """Generate complete SPARQL query from RDF graph."""
        where = self._make_where(graph)
        prefixes = get_prefixes(graph)
        query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {where} }}"""
        return query

    def _create_dynamic_class(self, class_name: str, contained_types: List[str], attributes: Dict[str, str]) -> Type:
        """
        Dynamically create a class with the specified attributes.
        """
        def __init__(self, name: str, **kwargs):
            self.name = name
            for attr_name, attr_type in attributes.items():
                # Skip 'name' attribute to avoid conflict with the positional name parameter
                if attr_name != 'name':
                    setattr(self, attr_name, kwargs.get(attr_name))
            for entity_type in contained_types:
                setattr(self, f"{entity_type}s", [])
        
        def __repr__(self):
            attr_strs = [f"{attr}={getattr(self, attr, None)}" for attr in attributes.keys() if attr != 'name']
            counts = []
            for entity_type in contained_types:
                attr_name = f"{entity_type}s"
                count = len(getattr(self, attr_name, []))
                counts.append(f"{entity_type}s={count}")

            return f"{class_name}(name='{self.name}', {', '.join(attr_strs)}, {', '.join(counts)})"
        
        def create_add_method(entity_type):
            def add_method(self, entity):
                attr_name = f"{entity_type}s"
                getattr(self, attr_name).append(entity)
            return add_method
        
        methods = {
            '__init__': __init__,
            '__repr__': __repr__,
            '_attributes': attributes
        }

        for entity_type in contained_types:
            methods[f"add_{entity_type}"] = create_add_method(entity_type)
        
        # Create the class dynamically
        cls = type(class_name, (), methods)
        
        return cls

    def _is_delta_quantity(self, uri):
        is_delta = self.g.value(URIRef(uri), QUDT["isDeltaQuantity"])
        return bool(is_delta)
        # return True if is_delta == URIRef('true') else False

    def _get_unit(self, uri):
        unit = self.g.value(URIRef(uri), QUDT["hasUnit"])
        return unit
    
    # TODO: use has-value template
    def _get_value(self, uri):
        if self.ontology == 's223': 
            return self.g.value(URIRef(uri), S223['hasValue'])
        else:
            raise ValueError('Ontology not implemented')

    def _dataframe_to_objects_generalized(self, df: pd.DataFrame, template_name: str, main_entity_col = 'name'):
        """
        Convert dataframe results into objects based on template structure.
        This is a generalized version that works with any template.
        """
        if df.empty:
            return []
  
        entity_types = {}
        value_types = {}
        attr_types = {}
        entity_class_relation = {}
        # entity column to attribute columns
        entity_attr_cols = {}
        entity_entity_cols = {}
        row = df.iloc[0]
        # NOTE: Tried using rdflib instead of SPARQL, still got a little complicated
        # TODO: Have a more structured/queryiable categorization of entities/value templates. Maybe add superclasses for hpfs:entity and hpfs:value

        value_templates,entity_templates = get_template_types(ontology=self.ontology)

        # get all the entity types
        for col, value in row.items():
            for p, entity_class in self.g.predicate_objects(value):
                if p == A and (self.g.compute_qname(entity_class)[1]) == URIRef(HPFS):
                    entity_type = get_uri_name(self.g,entity_class)
                    if entity_type in entity_templates:
                        entity_types[col] = entity_type
                    if entity_type in value_templates:
                        value_types[col] = entity_type
            
        # get values of entity types 
        for col, entity_type in entity_types.items():
            for entity in self.g.subjects(A, HPFS[entity_type]):
                for has_point, point in self.g.predicate_objects(entity):
                    if has_point == HPFS['has-point']:
                        for p, point_class in self.g.predicate_objects(point):
                            if p == A and (self.g.compute_qname(point_class)[1]) == URIRef(HPFS):
                                attr_type = get_uri_name(self.g,point_class)
                                if attr_type not in value_templates:
                                    print(f'attribute {attr_type} not an expected value')
                                    continue
                                if entity_type not in attr_types.keys():
                                    attr_types[entity_type] = []
                                if attr_type not in attr_types[entity_type]:
                                    attr_types[entity_type].append(attr_type)
        
        # Get entity relations of entity types
        # TODO: Check if there is a pythonic way to do this without looping. Maybe just switch to SPARQL
        for col, entity_type in entity_types.items():
            other_types = [HPFS[ec] for ec in entity_types.values() if ec != entity_type]
            for entity_s in self.g.subjects(A, HPFS[entity_type]):
                for p, other_entity in self.g.predicate_objects(entity_s):
                    for other_entity_type in self.g.objects(other_entity, A):
                        if other_entity_type in other_types:
                            if entity_type not in entity_class_relation.keys():
                                entity_class_relation[entity_type] = []
                            if get_uri_name(self.g,other_entity_type) not in entity_class_relation[entity_type]:
                                entity_class_relation[entity_type].append(get_uri_name(self.g,other_entity_type))
        # get entity_col to value_cols and entity_col to entity_col
        for col, entity_type in entity_types.items():
            entity_attr_cols[col] = []
            entity_entity_cols[col] = []
            attrs = attr_types.get(entity_type,[])
            other_entities = entity_class_relation.get(entity_type, [])
            for attr_col, attr_type in value_types.items():
                if attr_type in attrs:
                    entity_attr_cols[col].append(attr_col)
            for other_entity_col, other_entity_type in entity_types.items():
                if other_entity_type in other_entities:
                    entity_entity_cols[col].append(other_entity_col)

        # will have to reshape entity_entity_cols since that follows triple in graph, and I don't care about direction of relations
        # Should probably do for types too
        reverse_related_to = []
        reverse_related_to_types = []
        for entity, entities in entity_entity_cols.items():
            if main_entity_col in entities:
                reverse_related_to.append(entity)
                entities.remove(main_entity_col)
                reverse_related_to_types.append(entity_templates)
        entity_entity_cols[main_entity_col] += reverse_related_to

        # Should probably do for types too
        # TODO: Use less dictionaries - decide which are necessary
        reverse_related_to = []
        for entity, entities in entity_class_relation.items():
            if entity_types[main_entity_col] in entities:
                reverse_related_to.append(entity)
                entities.remove(entity_types[main_entity_col])
        if len(entity_class_relation) > 0:
            entity_class_relation[entity_types[main_entity_col]] += reverse_related_to
        # TODO: deal with underscores vs. dashes more consistently
        entity_classes = {}
        for entity_type, attrs in attr_types.items():
            contained_types = entity_class_relation[entity_type] if entity_type in entity_class_relation.keys() else []
            entity_classes[entity_type] = self._create_dynamic_class(
                entity_type.replace('-','_'), contained_types=contained_types,attributes = {attr.replace('-','_'): 'Value' for attr in attrs}
            )
        for entity_type, contained_types in entity_class_relation.items():
            if entity_type in entity_classes.keys():
                continue
            contained_types = entity_class_relation[entity_type] if entity_type in entity_class_relation.keys() else []
            contained_types = [c.replace('-','_') for c in contained_types]
            entity_classes[entity_type] = self._create_dynamic_class(
                entity_type.replace('-','_'), contained_types=contained_types, attributes = {}
            )            
        
        container_class = entity_classes[entity_types[main_entity_col]]
        completed_attributes = []
        entity_dict = {}
        containers = {}
        for _, row in df.iterrows():
            row_entities = {}
            for col, val in row.items():
                if col in entity_types.keys():
                    # class name
                    class_name = entity_types[col]
                    # col_name 
                    entity_name = val
                    # related_entity_cols
                    entity_cols = entity_entity_cols[col]
                    # related attr_cols
                    attr_cols = entity_attr_cols[col]
                    attrs = {}
                    # TODO: Relying on naming convention in template, use hasUnit and hasValue/value instead. 
                    for attr_col in attr_cols:
                        attr_class_name = value_types[attr_col]
                        attr_value = self._get_value(row[attr_col])
                        attr_unit = self._get_unit(row[attr_col])
                        attr_name = row[attr_col]
                        is_delta = self._is_delta_quantity(attr_name)
                        attr = Value(value=attr_value, unit=attr_unit, is_delta = is_delta, name=attr_name)
                        if self.as_si_units:
                            attr.convert_to_si()
                        # TODO: Will cause issue if there are multiple identical properties on a class. May need to change
                        if attr_name in completed_attributes:
                            continue
                        attrs[attr_class_name.replace('-','_')] = attr
                        completed_attributes.append(attr_name)
                    entity_class = entity_classes[class_name]
                    if entity_name not in entity_dict.keys():
                        entity = entity_class(name=entity_name, **attrs)
                        entity_dict[entity_name] = entity
                    else:
                        entity = entity_dict[entity_name]
                    row_entities[col] = entity
            
            # TODO: Consider how generalizable this approach is, creating the classes above and relating here
            container_name = row[main_entity_col]
            
            # Create container if it doesn't exist
            if container_name not in containers:
                containers[container_name] = entity_dict[container_name] 

            container_skeleton = build_tree(entity_entity_cols)
            def assemble_objects(tree):
                for entity_col, related_entities_cols in tree.items():
                    assemble_objects(related_entities_cols)
                    entity = row_entities[entity_col]
                    for related_entity_col in related_entities_cols:
                        related_entity = row_entities[related_entity_col]
                        existing_entities = vars(entity).get(entity_types[related_entity_col].replace('-','_') + 's', [])
                        if related_entity in existing_entities:
                            continue
                        else:
                            add_method_name = f"add_{entity_types[related_entity_col].replace('-','_')}"
                            add_method = getattr(entity, add_method_name)
                            add_method(related_entity)
        
            assemble_objects(container_skeleton)
        return list(containers.values())

    def _get_objects(self, template_name: str = 'hvac-zone'):
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
                objects = self._get_objects(template_name)
                results[result_key] = objects
            except Exception as e:
                print(f"Warning: Could not retrieve objects for template '{template_name}': {e}")
                results[result_key] = []
        
        return results

    def get_all_building_objects(self):
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

# To be migrated to MPC repo
def get_thermostat_data(model_loader: LoadModel, for_zone_list: Optional[List[str]] = None) -> Dict:
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
    all_objects = model_loader.get_all_building_objects()
    
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
                        tolerance_val = tstat.tolerance.value
                        thermostat_data["heat_tolerance"].append(-1.0 * tolerance_val)
                        thermostat_data["cool_tolerance"].append(1.0 * tolerance_val)

                    if hasattr(tstat, 'setpoint_deadband') and tstat.setpoint_deadband:
                        deadband_val = tstat.setpoint_deadband.value 
                        thermostat_data["setpoint_deadband"].append(deadband_val)
                    
                    if hasattr(tstat, 'active') and tstat.active:
                        active_val = tstat.active.value 
                        thermostat_data["active"].append(bool(active_val))
                    
                    if hasattr(tstat, 'stage_count') and tstat.stage_count:
                        stage_count = tstat.stage_count.value
                        thermostat_data["control_type_list"].append("binary" if stage_count == 1 else "stage")
                    
                    if hasattr(tstat, 'resolution') and tstat.resolution:
                        resolution_val = tstat.resolution.value
                        thermostat_data["resolution"].append(resolution_val)
                    
                    # Determine temperature unit from resolution unit
                    if hasattr(tstat.resolution, 'unit') and tstat.resolution.unit:
                        unit_str = str(tstat.resolution.unit)
                        thermostat_data["temperature_unit"].append('unit_str')

                    # Default values for control group and setpoint type
                    thermostat_data["control_group"].append("DEPRECATED")
                    # TODO: Double check what setpoint_type should be and how it is determined
                    thermostat_data["setpoint_type"].append("double")  # Default assumption
                    
                    # Process HVAC data
                    if hasattr(zone, 'hvacs') and zone.hvacs:
                        hvac = zone.hvacs[0] 
                        # hvac_id = hvac.name.split('#')[-1] if '#' in hvac.name else hvac.name
                        hvac_id = hvac.name
                        thermostat_data["hvacs"].append(hvac_id)
                        
                        # Cooling capacity
                        if hasattr(hvac, 'cooling_capacity') and hvac.cooling_capacity:
                            cooling_cap = hvac.cooling_capacity.value 
                            thermostat_data["cooling_capacity"].append(cooling_cap)
                        else:
                            thermostat_data["cooling_capacity"].append('Unkown')
                            
                        if hasattr(hvac.cooling_capacity, 'unit') and hvac.cooling_capacity.unit:
                            unit_str = str(hvac.cooling_capacity.unit)
                            thermostat_data["cooling_capacity_unit"].append(unit_str)
                        else:
                            thermostat_data["cooling_capacity_unit"].append('Unkown')
                        
                        # Heating capacity
                        if hasattr(hvac, 'heating_capacity') and hvac.heating_capacity:
                            heating_cap = hvac.heating_capacity.value
                            thermostat_data["heating_capacity"].append(heating_cap)
                        else:
                            thermostat_data["heating_capacity"].append('Unkown')
                            
                        if hasattr(hvac.heating_capacity, 'unit') and hvac.heating_capacity.unit:
                            unit_str = str(hvac.heating_capacity.unit)
                            thermostat_data["heating_capacity_unit"].append(unit_str)
                        else:
                            thermostat_data["heating_capacity_unit"].append('Unkown')
                        
                        # COP values
                        if hasattr(hvac, 'cooling_COP') and hvac.cooling_COP:
                            cooling_cop = hvac.cooling_COP.value 
                            thermostat_data["cooling_cop"].append(cooling_cop)
                        
                        if hasattr(hvac, 'heating_COP') and hvac.heating_COP:
                            heating_cop = hvac.heating_COP.value 
                            thermostat_data["heating_cop"].append(heating_cop)
                    else:
                        # Default HVAC values
                        thermostat_data["hvacs"].append("unknown")
                    # Process space data (floor area)
                    total_floor_area = 0.0

                    if hasattr(zone, 'spaces') and zone.spaces:
                        for space in zone.spaces:
                            if hasattr(space, 'area') and space.area:
                                area_val = space.area.value
                                total_floor_area += area_val
                                
                                if hasattr(space.area, 'unit') and space.area.unit:
                                    unit_str = str(space.area.unit)
                                    floor_area_unit = unit_str
                    
                    thermostat_data["floor_area_list"].append(total_floor_area)
                    thermostat_data["floor_area_unit"].append(floor_area_unit)
                    
                    # Process window data (take largest window by area)
                    largest_window_area = 0.0
                    
                    if hasattr(zone, 'windows') and zone.windows:
                        for window in zone.windows:
                            if hasattr(window, 'area') and window.area:
                                area_val = window.area.value 
                                if area_val > largest_window_area:
                                    largest_window_area = area_val
                                    
                                    if hasattr(window.area, 'unit') and window.area.unit:
                                        unit_str = str(window.area.unit)
                                        window_area_unit = unit_str
                                    
                                    if hasattr(window, 'azimuth') and window.azimuth:
                                        window_azimuth = window.azimuth.value
                                    
                                    if hasattr(window.azimuth, 'unit') and window.azimuth.unit:
                                        unit_str = str(window.azimuth.unit)
                                        window_azimuth_unit = unit_str
                                    else:
                                            window_azimuth_unit = 'Unkown'

                                    if hasattr(window, 'tilt') and window.tilt:
                                        window_tilt = window.tilt.value 
                                    
                                    if hasattr(window.tilt, 'unit') and window.tilt.unit:
                                        unit_str = str(window.tilt.unit) if hasattr(window.azimuth, 'unit') else 'Unkown'
                                        window_tilt_unit = unit_str
                                    else:
                                        window_tilt_unit = 'Unkown'
                                        
                    
                    thermostat_data["window_area_list"].append(largest_window_area)
                    thermostat_data["window_area_unit"].append(window_area_unit)
                    thermostat_data["azimuth_list"].append(window_azimuth)
                    thermostat_data["azimuth_unit"].append(window_azimuth_unit)
                    thermostat_data["tilt_list"].append(window_tilt)
                    thermostat_data["tilt_unit"].append(window_tilt_unit)
                    
                    # Default fuel and availability assumptions (electric heat pump)
                    # TODO: Fix this part based on old results
                    thermostat_data["fuel_heat_list"].append("electricity")
                    thermostat_data["fuel_cool_list"].append("electricity")
                    # TODO: Are these needed or a part of the metadata
                    thermostat_data["heat_availability"].append(True)
                    thermostat_data["cool_availability"].append(True)
                    thermostat_data["cooling_electricity"].append(True)
                    thermostat_data["heating_electricity"].append(True)
    
    return thermostat_data
