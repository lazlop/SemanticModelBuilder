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

UNIT_CONVERSIONS = {
    UNIT["DEG_F"]: UNIT["DEG_C"],
    UNIT["FT"]: UNIT["M"],
    UNIT["FT2"]: UNIT["M2"],
    UNIT["FT3"]: UNIT["M3"],
    UNIT["PSI"]: UNIT["PA"],
}

# TODO: Still in vibe coded state - should clean up and generalize a little
class Value:
    def __init__(self, value, unit, name=None):
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
    
    def __repr__(self):
        return f"Value(value={self.value}, unit='{self.unit}')"


class BuildingMetadataLoader:
    # Could do all alignment through templates by redefining mapping brick and s223 to hpf namespace, but this seems onerous
    def __init__(self, source: Union[str, Graph], ontology: str):
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

        # Only one query so far requires loading the ontology to use subClassOf in 223:
        if ontology == "s223":
            self.g.parse("https://open223.info/223p.ttl", format="ttl")
            
        # Initialize BuildingMOTIF components
        self.bm = BuildingMOTIF("sqlite://")
        self.model = Model.create(self.HPF)
        self.library = Library.load(directory=brick_templates)

    def get_var_name(self, graph, node):
        """Generate variable names for SPARQL queries from RDF nodes."""
        if isinstance(node, Literal):
            return node
        pre, ns, local = graph.compute_qname(node)
        if PARAM == ns:
            q_n = f"?{local}".replace('-','_')
        else:
            q_n = convert_to_prefixed(node, graph).replace('-','_')
        return q_n

    def make_where(self, graph):
        """Generate WHERE clause for SPARQL query from RDF graph."""
        where = []
        for s, p, o in graph.triples((None, None, None)):
            qs = self.get_var_name(graph, s)
            qo = self.get_var_name(graph, o)
            qp = convert_to_prefixed(p, graph).replace('-','_')
            where.append(f"{qs} {qp} {qo} .")
        return "\n".join(where)

    def get_query(self, graph):
        """Generate complete SPARQL query from RDF graph."""
        where = self.make_where(graph)
        prefixes = get_prefixes(graph)
        query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {where} }}"""
        return query

    def extract_attributes_from_template(self, template_name: str) -> Dict[str, str]:
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

    def create_dynamic_class(self, class_name: str, attributes: Dict[str, str]) -> Type:
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

    def extract_value_columns(self, df: pd.DataFrame, base_name: str) -> Value:
        """
        Extract value, unit, and name columns for a given base name and create a Value object.
        """
        value_col = f"{base_name}_value"
        unit_col = f"{base_name}_unit" 
        name_col = f"{base_name}_name"
        
        # Get the first row's values (assuming all rows have same structure for this entity)
        if not df.empty:
            # Prefer _name column data as the primary value when available
            name_data = df[name_col].iloc[0] if name_col in df.columns and pd.notna(df[name_col].iloc[0]) else None
            value_data = df[value_col].iloc[0] if value_col in df.columns and pd.notna(df[value_col].iloc[0]) else None
            unit_data = df[unit_col].iloc[0] if unit_col in df.columns and pd.notna(df[unit_col].iloc[0]) else None
            
            # Use name_data as the primary value if available, otherwise use value_data
            primary_value = name_data if name_data is not None else value_data
            
            return Value(value=primary_value, unit=unit_data, name=name_data)
        
        return None

    def identify_entity_attributes(self, df: pd.DataFrame, entity_name: str) -> Dict[str, Any]:
        """
        Identify attributes for an entity based on column patterns in the dataframe.
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
            name_col = f"{entity_name}_{attr_base}_name"
            value_col = f"{entity_name}_{attr_base}_value"
            unit_col = f"{entity_name}_{attr_base}_unit"
            
            # Check if we have meaningful data in the _name column (prefer this)
            if name_col in df.columns and not df.empty and pd.notna(df[name_col].iloc[0]):
                name_data = df[name_col].iloc[0]
                # Only create attribute if the _name column contains actual numeric/meaningful data
                # Skip if it contains URI strings
                if not str(name_data).startswith('urn:') and not '-name' in str(name_data):
                    try:
                        # Try to convert to number to verify it's meaningful data
                        float(name_data)
                        unit_data = df[unit_col].iloc[0] if unit_col in df.columns and pd.notna(df[unit_col].iloc[0]) else None
                        value_obj = Value(value=name_data, unit=unit_data, name=name_data)
                        # Use clean attribute name (remove redundant prefixes and suffixes)
                        clean_attr_name = attr_base.replace('name_', '').replace('_name', '')
                        attributes[clean_attr_name] = value_obj
                    except (ValueError, TypeError):
                        # Skip non-numeric data in _name columns
                        pass
            
            # If no meaningful _name data, check _value column
            elif value_col in df.columns and not df.empty and pd.notna(df[value_col].iloc[0]):
                value_data = df[value_col].iloc[0]
                # Only create attribute if the _value column contains actual numeric/meaningful data
                if not str(value_data).startswith('urn:') and not '-name' in str(value_data):
                    try:
                        # Try to convert to number to verify it's meaningful data
                        float(value_data)
                        unit_data = df[unit_col].iloc[0] if unit_col in df.columns and pd.notna(df[unit_col].iloc[0]) else None
                        value_obj = Value(value=value_data, unit=unit_data, name=None)
                        # Use clean attribute name (remove redundant prefixes and suffixes)
                        clean_attr_name = attr_base.replace('name_', '').replace('_name', '')
                        attributes[clean_attr_name] = value_obj
                    except (ValueError, TypeError):
                        # Skip non-numeric data in _value columns
                        pass
        
        # Also look for simple string attributes (columns that end with the entity name)
        for col in df.columns:
            if col == entity_name and col not in attributes:
                if not df.empty:
                    attributes[col] = df[col].iloc[0]
        
        return attributes

    def create_container_class(self, container_name: str, contained_types: List[str]) -> Type:
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

    def dataframe_to_objects_generalized(self, df: pd.DataFrame, template_name: str):
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
            sample_attributes = self.identify_entity_attributes(df, entity_type)
            attr_types = {attr: 'Value' if isinstance(val, Value) else 'str' 
                         for attr, val in sample_attributes.items()}
            
            entity_classes[entity_type] = self.create_dynamic_class(
                entity_type.capitalize(), attr_types
            )
        
        # Create container class
        container_class = self.create_container_class(
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
                    entity_attributes = self.identify_entity_attributes(pd.DataFrame([row]), entity_type)
                    
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

    def get_objects_generalized(self, template_name: str = 'hvac-zone'):
        """
        Generalized function to get objects from any template.
        """
        template = self.library.get_template_by_name(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        template_inlined = template.inline_dependencies()
        query = self.get_query(template_inlined.body)
        df = query_to_df(query, self.g)
        objects = self.dataframe_to_objects_generalized(df, template_name)
        return objects

    def get_site_objects(self):
        """
        Get site objects using the site template.
        """
        return self.get_objects_generalized('site')

    def get_all_building_objects(self):
        """
        Get all building objects including site and hvac zones.
        Returns a dictionary with object types as keys.
        """
        results = {}
        
        # Get site objects
        try:
            site_objects = self.get_site_objects()
            results['sites'] = site_objects
        except Exception as e:
            print(f"Warning: Could not retrieve site objects: {e}")
            results['sites'] = []
        
        # Get hvac zone objects
        try:
            hvac_zone_objects = self.get_objects_generalized('hvac-zone')
            results['hvac_zones'] = hvac_zone_objects
        except Exception as e:
            print(f"Warning: Could not retrieve hvac zone objects: {e}")
            results['hvac_zones'] = []
        
        # Try to get other common building objects
        common_templates = ['space', 'equipment', 'sensor', 'actuator', 'point']
        for template_name in common_templates:
            try:
                objects = self.get_objects_generalized(template_name)
                if objects:  # Only add if we got results
                    results[template_name + 's'] = objects
            except Exception as e:
                # Silently skip templates that don't exist or fail
                pass
        
        return results

    def list_available_templates(self):
        """
        List all available templates in the library.
        """
        return [template.name for template in self.library.get_templates()]

    def convert_model_to_si(self):
        """
        Convert all quantities in a Brick model to SI units

        Args:
            g: The RDF graph containing the Brick model

        Returns:
            Graph: The modified graph with SI units
        """
        query = sparql_queries["convert_to_si"][self.ontology]

        for row_dict in self.g.query(query).bindings:
            # will throw error if not all things are present
            subject, value, unit = row_dict["s"], row_dict["v"], row_dict["u"]
            isDelta = row_dict.get("isDelta", False)

            if unit in UNIT_CONVERSIONS:
                print(
                    "changing value of ",
                    subject,
                    "from",
                    unit,
                    "to",
                    UNIT_CONVERSIONS[unit],
                )
                new_unit = UNIT_CONVERSIONS[unit]
                new_value = convert_units(value, unit, new_unit, isDelta)

                if self.ontology == "brick":
                    self.g.set((subject, BRICK.value, Literal(new_value)))
                    self.g.set((subject, QUDT.hasUnit, new_unit))
                else:
                    self.g.set((subject, S223.hasValue, Literal(new_value)))
                    self.g.set((subject, QUDT.hasUnit, new_unit))

    def _get_value(self, subject, predicate) -> Any:
        """Helper method to get a value from the RDF graph."""
        value = self.g.value(subject, predicate)
        return value.toPython() if value else None
