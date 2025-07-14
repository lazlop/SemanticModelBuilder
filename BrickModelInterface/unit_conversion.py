# TODO: want to consider how we use ontologies
# May want to cache the conversion factors we actually use, then reach out to qudt if we need to
# So many qudt units, querying is pretty slow.
from rdflib import Graph, Namespace, Literal, URIRef
from importlib.resources import files
from.namespaces import * 
import csv

qudt_dir = files('BrickModelInterface').joinpath('qudt')


def _get_known_conversion_factor(unit):
    if isinstance(unit, URIRef):
        from_unit_uri = unit
    else:
        from_unit_uri = UNIT[unit]

    with open(qudt_dir / 'known_units.csv', mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['unit'] == str(from_unit_uri):
                return float(row['conversionFactor']), float(row['offset'])
        raise ValueError(f"Unknown unit: {from_unit_uri}")

def _get_conversion_factor(unit, save_to_known_units = True):
    """
    Fetch the conversion factor from `from_unit` to `to_unit` using QUDT ontology in rdflib.
    If the unit is not a uri, make it one in the unit namespace
    """
    if isinstance(unit, URIRef):
        from_unit_uri = unit
    else:
        from_unit_uri = UNIT[unit]
    
    try:
        return _get_known_conversion_factor(unit)
    except ValueError as e:    
        # just parsing qudt is kind of slow
        print("Checking QUDT for unit conversion. This may take a second...")
    g = Graph()
    # Comment out for querying online qudt
    # g.parse("https://qudt.org/2.1/vocab/unit.ttl", format="turtle")
    g.parse(qudt_dir / 'qudt_units.ttl', format='turtle')
    
    query = f"""
    PREFIX qudt: <http://qudt.org/schema/qudt/>
    PREFIX unit: <http://qudt.org/vocab/unit/>
    
    SELECT ?conversionFactor ?offset WHERE {{
    <{from_unit_uri}> qudt:conversionMultiplier ?conversionFactor ;
    OPTIONAL {{ <{from_unit_uri}> qudt:conversionOffset ?offset }}. 
    }}
    """
    
    results = g.query(query)
    if len(results) == 0:
        raise ValueError(f"No conversion factor found for {unit}")
    if len(results) > 1:
        raise ValueError(f"Multiple conversion factors found for {unit}")
    conversion_factor = float(results.bindings[0]['conversionFactor'])
    offset = float(results.bindings[0].get('offset', 0))
    conversion_factor = float(conversion_factor)
    offset = 0 if offset is None else offset  # Handle None offset

    if save_to_known_units:
        print(f"Saving conversion factor for {unit} to known units file")
        with open(qudt_dir / 'known_units.csv', mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([str(from_unit_uri), conversion_factor, offset])
    return conversion_factor, offset


def convert_units(value, from_unit, to_unit, is_delta_quantity=False):
    """
    Convert a numerical value from one unit to another using QUDT.
    TODO: Could add quantitykind check to make sure units are compatible
    """
    from_conversion_factor, from_offset = _get_conversion_factor(from_unit)
    to_conversion_factor, to_offset = _get_conversion_factor(to_unit)
    if is_delta_quantity:
        unit_value = from_conversion_factor / to_conversion_factor * float(value)
    else:
        unit_value = from_conversion_factor / to_conversion_factor * (float(value) + from_offset) - to_offset
    return unit_value