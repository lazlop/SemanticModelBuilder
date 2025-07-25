# %%
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from rdflib import Graph, Literal, Namespace, URIRef
from semantic_mpc_interface.namespaces import * 
from semantic_mpc_interface.utils import * 

# %%
bm = BuildingMOTIF("sqlite://")
model = Model.create(HPF)


# %%
tmp = Library.load(directory='dataclasses/templates/brick-templates')


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

# AI generated from here - would like to generate these classes direct from templates
class Value:
    def __init__(self, value, unit, name=None):
        self.value = float(value)
        self.unit = str(unit).replace('unit:', '')  # Remove unit: prefix if present
        self.name = name
    
    def __repr__(self):
        return f"Value(value={self.value}, unit='{self.unit}')"

class Window:
    def __init__(self, name, area, azimuth, tilt):
        self.name = name
        self.area = area  # Value object
        self.azimuth = azimuth  # Value object
        self.tilt = tilt  # Value object
    
    def __repr__(self):
        return f"Window(name='{self.name}', area={self.area}, azimuth={self.azimuth}, tilt={self.tilt})"

class Space:
    def __init__(self, name, area):
        self.name = name
        self.area = area  # Value object
    
    def __repr__(self):
        return f"Space(name='{self.name}', area={self.area})"

class Zone:
    def __init__(self, name):
        self.name = name
        self.spaces = []
        self.windows = []
    
    def add_space(self, space):
        self.spaces.append(space)
    
    def add_window(self, window):
        self.windows.append(window)
    
    def __repr__(self):
        return f"Zone(name='{self.name}', spaces={len(self.spaces)}, windows={len(self.windows)})"

def dataframe_to_objects(df):
    """Convert the dataframe results into Zone objects with their associated spaces and windows."""
    zones = {}
    
    for _, row in df.iterrows():
        zone_name = row['name']
        
        # Create zone if it doesn't exist
        if zone_name not in zones:
            zones[zone_name] = Zone(zone_name)
        
        zone = zones[zone_name]
        
        # Create space with area value
        space_area = Value(
            value=row['space_name_area_value'],
            unit=row['space_name_area_unit'],
            name=row['space_name_area_name']
        )
        space = Space(name=row['space_name'], area=space_area)
        
        # Create window with area, azimuth, and tilt values
        window_area = Value(
            value=row['window_name_area_value'],
            unit=row['window_name_area_unit'],
            name=row['window_name_area_name']
        )
        window_azimuth = Value(
            value=row['window_name_azimuth_value'],
            unit='Degree',  # From the query, azimuth uses degrees
            name=row['window_name_azimuth_name']
        )
        window_tilt = Value(
            value=row['window_name_tilt_value'],
            unit='Degree',  # From the query, tilt uses degrees
            name=row['window_name_tilt_name']
        )
        window = Window(
            name=row['window_name'],
            area=window_area,
            azimuth=window_azimuth,
            tilt=window_tilt
        )
        
        # Add space and window to zone (check for duplicates)
        if not any(s.name == space.name for s in zone.spaces):
            zone.add_space(space)
        if not any(w.name == window.name for w in zone.windows):
            zone.add_window(window)
    
    return list(zones.values())

def get_objects(graph):
    zone = tmp.get_template_by_name('hvac-zone')
    zone_in = zone.inline_dependencies()
    query = get_query(zone_in.body)
    df = query_to_df(query, graph)
    zones = dataframe_to_objects(df)
    return zones
if __name__ == "__main__":
    g = Graph()
    g.parse('tutorial/bldg2.ttl')
    # Convert dataframe to objects
    zones = get_objects(g)

    # %%
    # Display the created objects
    for zone in zones:
        print(f"\n{zone}")
        for space in zone.spaces:
            print(f"  {space}")
        for window in zone.windows:
            print(f"  {window}")

    # %%
    # Example: Access specific data from the objects
    print("\nExample data access:")
    if zones:
        first_zone = zones[0]
        print(f"First zone name: {first_zone.name}")
        
        if first_zone.spaces:
            first_space = first_zone.spaces[0]
            print(f"First space area: {first_space.area.value} {first_space.area.unit}")
        
        if first_zone.windows:
            first_window = first_zone.windows[0]
            print(f"First window area: {first_window.area.value} {first_window.area.unit}")
            print(f"First window azimuth: {first_window.azimuth.value} {first_window.azimuth.unit}")
            print(f"First window tilt: {first_window.tilt.value} {first_window.tilt.unit}")

    # %%
    # Verification: Check that we have the expected number of objects
    print(f"\nVerification:")
    print(f"Total zones created: {len(zones)}")
    total_spaces = sum(len(zone.spaces) for zone in zones)
    total_windows = sum(len(zone.windows) for zone in zones)
    print(f"Total spaces: {total_spaces}")
    print(f"Total windows: {total_windows}")

    # %%
