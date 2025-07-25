# %%
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from rdflib import Graph, Literal, Namespace, URIRef
from semantic_mpc_interface.namespaces import * 
from semantic_mpc_interface.utils import * 
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import pandas as pd
import json

# %%
bm = BuildingMOTIF("sqlite://")
model = Model.create(HPF)

# %%
tmp = Library.load(directory='dataclasses/templates/brick-templates')

# %%
zone = tmp.get_template_by_name('hvac-zone')

# %%
zone_in = zone.inline_dependencies()

# %%
print(zone_in.all_parameters)

# %%
print(zone_in.body.serialize(format = 'ttl'))

# %%
def get_var_name(graph, node):
    pre, ns, local = graph.compute_qname(node)
    if PARAM == ns:
        q_n = f"?{local}".replace('-','_')
    else:
        q_n = convert_to_prefixed(node, graph).replace('-','_')
    return q_n

# %%
def make_where(graph):
    where = []
    for s,p,o in graph.triples((None,None,None)):
        # print(s,p,o)
        qs = get_var_name(graph, s)
        qo = get_var_name(graph, o)
        qp = convert_to_prefixed(p, graph).replace('-','_')
        where.append(f"{qs} {qp} {qo} .")
    return "\n".join(where)

# %%
def get_query(graph):
     where = make_where(graph)
     prefixes = get_prefixes(graph)
     query = f"""{prefixes}\nSELECT DISTINCT * WHERE {{ {where} }}"""
     return query

# %%
query = get_query(zone_in.body)

# %%
print(query)

# %%
g = Graph()
g.parse('tutorial/bldg2.ttl')

# %%
df = query_to_df(query, g)

# %%
@dataclass
class Value:
    """Represents a measured or calculated value with its unit"""
    value: float
    unit: str
    timestamp: Optional[str] = None
    quality: Optional[str] = None
    
    def __str__(self):
        return f"{self.value} {self.unit}"

@dataclass
class Window:
    """Represents a window in a space"""
    name: str
    uri: str
    area: Optional[Value] = None
    orientation: Optional[str] = None
    glazing_type: Optional[str] = None
    u_value: Optional[Value] = None
    shgc: Optional[Value] = None  # Solar Heat Gain Coefficient
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        return f"Window({self.name})"

@dataclass
class Space:
    """Represents a space within a zone"""
    name: str
    uri: str
    area: Optional[Value] = None
    volume: Optional[Value] = None
    space_type: Optional[str] = None
    windows: List[Window] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def add_window(self, window: Window):
        """Add a window to this space"""
        self.windows.append(window)
    
    def get_total_window_area(self) -> Optional[Value]:
        """Calculate total window area for this space"""
        if not self.windows:
            return None
        
        total_area = 0
        unit = None
        for window in self.windows:
            if window.area:
                if unit is None:
                    unit = window.area.unit
                total_area += window.area.value
        
        return Value(total_area, unit) if unit else None
    
    def __str__(self):
        return f"Space({self.name}, {len(self.windows)} windows)"

@dataclass
class Zone:
    """Represents an HVAC zone containing spaces"""
    name: str
    uri: str
    spaces: List[Space] = field(default_factory=list)
    zone_type: Optional[str] = None
    setpoint_heating: Optional[Value] = None
    setpoint_cooling: Optional[Value] = None
    temperature: Optional[Value] = None
    humidity: Optional[Value] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def add_space(self, space: Space):
        """Add a space to this zone"""
        self.spaces.append(space)
    
    def get_total_area(self) -> Optional[Value]:
        """Calculate total area for all spaces in this zone"""
        if not self.spaces:
            return None
        
        total_area = 0
        unit = None
        for space in self.spaces:
            if space.area:
                if unit is None:
                    unit = space.area.unit
                total_area += space.area.value
        
        return Value(total_area, unit) if unit else None
    
    def get_all_windows(self) -> List[Window]:
        """Get all windows from all spaces in this zone"""
        windows = []
        for space in self.spaces:
            windows.extend(space.windows)
        return windows
    
    def get_total_window_area(self) -> Optional[Value]:
        """Calculate total window area for all spaces in this zone"""
        windows = self.get_all_windows()
        if not windows:
            return None
        
        total_area = 0
        unit = None
        for window in windows:
            if window.area:
                if unit is None:
                    unit = window.area.unit
                total_area += window.area.value
        
        return Value(total_area, unit) if unit else None
    
    def __str__(self):
        return f"Zone({self.name}, {len(self.spaces)} spaces, {len(self.get_all_windows())} windows)"

# %%
def parse_uri_name(uri: str) -> str:
    """Extract a readable name from a URI"""
    if isinstance(uri, str):
        return uri.split('/')[-1].split('#')[-1]
    return str(uri)

def create_value_from_literal(literal_value, unit: str = None) -> Optional[Value]:
    """Create a Value object from a literal value"""
    if literal_value is None or pd.isna(literal_value):
        return None
    
    try:
        # Try to convert to float
        float_val = float(literal_value)
        return Value(float_val, unit or "")
    except (ValueError, TypeError):
        # If conversion fails, store as string in properties
        return None

def dataframe_to_objects(df: pd.DataFrame) -> List[Zone]:
    """Convert dataframe results to Zone objects with nested Space and Window objects"""
    zones = {}
    spaces = {}
    windows = {}
    
    # Process each row in the dataframe
    for _, row in df.iterrows():
        # Extract URIs and names
        zone_uri = row.get('?zone')
        space_uri = row.get('?space')
        window_uri = row.get('?window')
        
        if zone_uri:
            zone_name = parse_uri_name(zone_uri)
            if zone_uri not in zones:
                zones[zone_uri] = Zone(
                    name=zone_name,
                    uri=str(zone_uri)
                )
        
        if space_uri:
            space_name = parse_uri_name(space_uri)
            if space_uri not in spaces:
                spaces[space_uri] = Space(
                    name=space_name,
                    uri=str(space_uri)
                )
                
                # Add space to zone if zone exists
                if zone_uri and zone_uri in zones:
                    zones[zone_uri].add_space(spaces[space_uri])
        
        if window_uri:
            window_name = parse_uri_name(window_uri)
            if window_uri not in windows:
                windows[window_uri] = Window(
                    name=window_name,
                    uri=str(window_uri)
                )
                
                # Add window to space if space exists
                if space_uri and space_uri in spaces:
                    spaces[space_uri].add_window(windows[window_uri])
        
        # Process any additional properties from the dataframe
        for col in df.columns:
            if col.startswith('?') and col not in ['?zone', '?space', '?window']:
                value = row[col]
                if not pd.isna(value):
                    prop_name = col[1:]  # Remove the '?' prefix
                    
                    # Try to identify if this is a measurable value
                    if any(keyword in prop_name.lower() for keyword in ['area', 'volume', 'temperature', 'humidity', 'setpoint']):
                        # This might be a measurable value
                        val_obj = create_value_from_literal(value)
                        if val_obj:
                            # Assign to appropriate object
                            if window_uri and window_uri in windows:
                                if 'area' in prop_name.lower():
                                    windows[window_uri].area = val_obj
                                else:
                                    windows[window_uri].properties[prop_name] = val_obj
                            elif space_uri and space_uri in spaces:
                                if 'area' in prop_name.lower():
                                    spaces[space_uri].area = val_obj
                                elif 'volume' in prop_name.lower():
                                    spaces[space_uri].volume = val_obj
                                else:
                                    spaces[space_uri].properties[prop_name] = val_obj
                            elif zone_uri and zone_uri in zones:
                                if 'temperature' in prop_name.lower():
                                    zones[zone_uri].temperature = val_obj
                                elif 'humidity' in prop_name.lower():
                                    zones[zone_uri].humidity = val_obj
                                elif 'setpoint' in prop_name.lower() and 'heating' in prop_name.lower():
                                    zones[zone_uri].setpoint_heating = val_obj
                                elif 'setpoint' in prop_name.lower() and 'cooling' in prop_name.lower():
                                    zones[zone_uri].setpoint_cooling = val_obj
                                else:
                                    zones[zone_uri].properties[prop_name] = val_obj
                    else:
                        # Store as regular property
                        if window_uri and window_uri in windows:
                            windows[window_uri].properties[prop_name] = value
                        elif space_uri and space_uri in spaces:
                            spaces[space_uri].properties[prop_name] = value
                        elif zone_uri and zone_uri in zones:
                            zones[zone_uri].properties[prop_name] = value
    
    return list(zones.values())

# %%
# Additional utility functions for working with the objects

def find_zone_by_name(zones: List[Zone], name: str) -> Optional[Zone]:
    """Find a zone by its name"""
    for zone in zones:
        if zone.name.lower() == name.lower():
            return zone
    return None

def find_space_by_name(zones: List[Zone], name: str) -> Optional[Space]:
    """Find a space by its name across all zones"""
    for zone in zones:
        for space in zone.spaces:
            if space.name.lower() == name.lower():
                return space
    return None

def get_zones_summary(zones: List[Zone]) -> Dict[str, Any]:
    """Get a summary of all zones"""
    summary = {
        'total_zones': len(zones),
        'total_spaces': sum(len(zone.spaces) for zone in zones),
        'total_windows': sum(len(zone.get_all_windows()) for zone in zones),
        'zones': []
    }
    
    for zone in zones:
        zone_info = {
            'name': zone.name,
            'spaces_count': len(zone.spaces),
            'windows_count': len(zone.get_all_windows()),
            'total_area': zone.get_total_area(),
            'total_window_area': zone.get_total_window_area()
        }
        summary['zones'].append(zone_info)
    
    return summary

def export_to_dict(zones: List[Zone]) -> List[Dict[str, Any]]:
    """Export zones to dictionary format for JSON serialization"""
    result = []
    for zone in zones:
        zone_dict = {
            'name': zone.name,
            'uri': zone.uri,
            'zone_type': zone.zone_type,
            'properties': zone.properties,
            'spaces': []
        }
        
        # Add zone-level values
        if zone.temperature:
            zone_dict['temperature'] = {'value': zone.temperature.value, 'unit': zone.temperature.unit}
        if zone.humidity:
            zone_dict['humidity'] = {'value': zone.humidity.value, 'unit': zone.humidity.unit}
        if zone.setpoint_heating:
            zone_dict['setpoint_heating'] = {'value': zone.setpoint_heating.value, 'unit': zone.setpoint_heating.unit}
        if zone.setpoint_cooling:
            zone_dict['setpoint_cooling'] = {'value': zone.setpoint_cooling.value, 'unit': zone.setpoint_cooling.unit}
        
        for space in zone.spaces:
            space_dict = {
                'name': space.name,
                'uri': space.uri,
                'space_type': space.space_type,
                'properties': space.properties,
                'windows': []
            }
            
            # Add space-level values
            if space.area:
                space_dict['area'] = {'value': space.area.value, 'unit': space.area.unit}
            if space.volume:
                space_dict['volume'] = {'value': space.volume.value, 'unit': space.volume.unit}
            
            for window in space.windows:
                window_dict = {
                    'name': window.name,
                    'uri': window.uri,
                    'orientation': window.orientation,
                    'glazing_type': window.glazing_type,
                    'properties': window.properties
                }
                
                # Add window-level values
                if window.area:
                    window_dict['area'] = {'value': window.area.value, 'unit': window.area.unit}
                if window.u_value:
                    window_dict['u_value'] = {'value': window.u_value.value, 'unit': window.u_value.unit}
                if window.shgc:
                    window_dict['shgc'] = {'value': window.shgc.value, 'unit': window.shgc.unit}
                
                space_dict['windows'].append(window_dict)
            
            zone_dict['spaces'].append(space_dict)
        
        result.append(zone_dict)
    
    return result

# %%
# Convert the dataframe to objects
zone_objects = dataframe_to_objects(df)

# Display the results
print(f"Created {len(zone_objects)} zone objects:")
for zone in zone_objects:
    print(f"\n{zone}")
    for space in zone.spaces:
        print(f"  {space}")
        for window in space.windows:
            print(f"    {window}")
    
    # Show some calculated values
    total_area = zone.get_total_area()
    if total_area:
        print(f"  Total zone area: {total_area}")
    
    total_window_area = zone.get_total_window_area()
    if total_window_area:
        print(f"  Total window area: {total_window_area}")

# Example usage and demonstration
print("\n" + "="*50)
print("ZONE OBJECTS SUMMARY")
print("="*50)

summary = get_zones_summary(zone_objects)
print(f"Total zones: {summary['total_zones']}")
print(f"Total spaces: {summary['total_spaces']}")
print(f"Total windows: {summary['total_windows']}")

print("\n" + "="*50)
print("UTILITY FUNCTIONS DEMONSTRATION")
print("="*50)

# Demonstrate finding objects by name
if zone_objects:
    first_zone = zone_objects[0]
    print(f"Finding zone '{first_zone.name}':")
    found_zone = find_zone_by_name(zone_objects, first_zone.name)
    if found_zone:
        print(f"  Found: {found_zone}")
    
    if first_zone.spaces:
        first_space = first_zone.spaces[0]
        print(f"Finding space '{first_space.name}':")
        found_space = find_space_by_name(zone_objects, first_space.name)
        if found_space:
            print(f"  Found: {found_space}")

print("\n" + "="*50)
print("EXPORT TO DICTIONARY EXAMPLE")
print("="*50)

# Show a sample of the dictionary export
dict_export = export_to_dict(zone_objects)
if dict_export:
    print("Sample zone as dictionary:")
    print(json.dumps(dict_export[0], indent=2, default=str))

# %%
