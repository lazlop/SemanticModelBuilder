import os
from typing import Any, Dict, List, Optional, Union

from rdflib import Graph, Literal, Namespace

from .namespaces import *
from .unit_conversion import convert_units

UNIT_CONVERSIONS = {
    UNIT["DEG_F"]: UNIT["DEG_C"],
    UNIT["FT"]: UNIT["M"],
    UNIT["FT2"]: UNIT["M2"],
    UNIT["FT3"]: UNIT["M3"],
    UNIT["PSI"]: UNIT["PA"],
}

class BuildingMetadataLoader:
    # Could do all alignment through templates by redefining mapping brick and s223 to hpf namespace, but this seems onerous
    def __init__(self, source: Union[str, Graph], ontology: str):
        if os.path.isfile(source):
            self.g = Graph()
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

    # def convert_model_to_si(self):
    #     """
    #     Convert all quantities in a Brick model to SI units

    #     Args:
    #         g: The RDF graph containing the Brick model

    #     Returns:
    #         Graph: The modified graph with SI units
    #     """
    #     query = sparql_queries["convert_to_si"][self.ontology]

    #     for row_dict in self.g.query(query).bindings:
    #         # will throw error if not all things are present
    #         subject, value, unit = row_dict["s"], row_dict["v"], row_dict["u"]
    #         isDelta = row_dict.get("isDelta", False)

    #         if unit in UNIT_CONVERSIONS:
    #             print(
    #                 "changing value of ",
    #                 subject,
    #                 "from",
    #                 unit,
    #                 "to",
    #                 UNIT_CONVERSIONS[unit],
    #             )
    #             new_unit = UNIT_CONVERSIONS[unit]
    #             new_value = convert_units(value, unit, new_unit, isDelta)

    #             if self.ontology == "brick":
    #                 self.g.set((subject, BRICK.value, Literal(new_value)))
    #                 self.g.set((subject, QUDT.hasUnit, new_unit))
    #             else:
    #                 self.g.set((subject, S223.hasValue, Literal(new_value)))
    #                 self.g.set((subject, QUDT.hasUnit, new_unit))

    # def _get_value(self, subject, predicate) -> Any:
    #     """Helper method to get a value from the RDF graph."""
    #     value = self.g.value(subject, predicate)
    #     return value.toPython() if value else None
