"""
Semantic Model Builder

Core functionality for building semantic building models using Brick Schema
and ASHRAE Standard 223P ontologies.
"""

import logging
from importlib.resources import files
from typing import List, Literal, Optional, Union

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from rdflib import Graph
from rdflib import Literal as RDFLiteral
from rdflib import Namespace, URIRef

from .namespaces import BRICK, S223, UNIT, A, bind_prefixes
from .utils import add_brick_inverse_relations

logger = logging.getLogger(__name__)


class SemanticModelBuilder:
    """
    Base class for building semantic building models.

    Supports both Brick Schema and ASHRAE Standard 223P ontologies.
    """

    def __init__(
        self,
        site_id: str,
        ontology: Literal["brick", "s223"] = "brick",
        system_of_units: Literal["SI", "IP"] = "SI",
        hvac_type: str = "hp-rtu",
        tstat_type: str = "tstat-static-properties",
    ):
        """
        Initialize the semantic model builder.

        Args:
            site_id: Unique identifier for the site/building
            ontology: Ontology to use ('brick' or 's223')
            system_of_units: Unit system ('SI' or 'IP')
            hvac_type: Type of HVAC system template
            tstat_type: Type of thermostat template
        """
        self.site_id = site_id
        self.ontology = ontology
        self.system_of_units = system_of_units
        self.hvac_type = hvac_type
        self.tstat_type = tstat_type

        # Initialize BuildingMOTIF
        self.bm = BuildingMOTIF("sqlite://")
        self.building_ns = Namespace(f"urn:hpflex/{self.site_id}#")
        self.model = Model.create(self.building_ns)
        self.graph = self.model.graph

        # Set up units
        self._setup_units()

        # Bind namespaces
        bind_prefixes(self.graph)
        self.graph.bind("bldg", self.building_ns)

        # Load templates
        self._load_templates()

        logger.info(f"Initialized {ontology} model builder for site: {site_id}")

    def _setup_units(self) -> None:
        """Set up default units based on system of units."""
        if self.system_of_units == "SI":
            self.default_temperature_unit = "DEG_C"
            self.default_area_unit = "M2"
        elif self.system_of_units == "IP":
            self.default_temperature_unit = "DEG_F"
            self.default_area_unit = "FT2"
        else:
            raise ValueError("Invalid system of units. Must be 'SI' or 'IP'")

    def _load_templates(self) -> None:
        """Load ontology-specific templates."""
        template_dir = str(
            files("semantic_mpc_interface").joinpath(
                f"templates/{self.ontology}-templates"
            )
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
            logger.error(f"Failed to load templates from {template_dir}: {e}")
            raise

    def evaluate_template(self, template, data: dict, fill: bool = False) -> None:
        """
        Evaluate a template with the given data.

        Args:
            template: Template to evaluate
            data: Data dictionary for template parameters
            fill: Whether to fill missing parameters automatically
        """
        try:
            graph = template.inline_dependencies().evaluate(data)
            if fill and not isinstance(graph, Graph):
                logger.debug(f"Filling template parameters: {graph.all_parameters}")
                bindings, graph = graph.fill(self.building_ns)

            self.model.add_graph(graph)
        except TypeError as e:
            logger.error(f"Template evaluation failed: {e}")
            if hasattr(graph, "parameters"):
                raise TypeError(
                    f"Template not complete. Additional parameters needed: {graph.parameters}"
                )
            raise

    def add_site(
        self, timezone: str, latitude: float, longitude: float, noaa_station: str
    ) -> None:
        """
        Add site information to the model.

        Args:
            timezone: Site timezone (e.g., 'America/New_York')
            latitude: Site latitude in degrees
            longitude: Site longitude in degrees
            noaa_station: NOAA weather station identifier
        """
        site_template = self.templates.get_template_by_name("site")
        site_info = {
            "name": self.building_ns[self.site_id],
            "timezone": self.building_ns[f"{self.site_id}.timezone"],
            "timezone_value": RDFLiteral(timezone),
            "latitude": self.building_ns[f"{self.site_id}.latitude"],
            "latitude_value": RDFLiteral(latitude),
            "longitude": self.building_ns[f"{self.site_id}.longitude"],
            "longitude_value": RDFLiteral(longitude),
            "noaastation": self.building_ns[f"{self.site_id}.noaastation"],
            "noaastation_value": RDFLiteral(noaa_station),
        }

        self.evaluate_template(site_template, site_info)
        self.model.graph.add(
            (self.building_ns[""], A, Namespace("urn:hpflex#")["Project"])
        )

        logger.info(f"Added site: {self.site_id}")

    def add_zone(self, zone_id: str) -> None:
        """
        Add an HVAC zone to the model.

        Args:
            zone_id: Unique identifier for the zone
        """
        zone_template = self.templates.get_template_by_name("hvac-zone")
        self.evaluate_template(zone_template, {"name": self.building_ns[zone_id]})
        logger.info(f"Added zone: {zone_id}")

    def add_space(
        self, space_id: str, zone_id: str, area_value: float, unit: Optional[str] = None
    ) -> None:
        """
        Add a physical space to the model.

        Args:
            space_id: Unique identifier for the space
            zone_id: Zone that contains this space
            area_value: Floor area of the space
            unit: Area unit (defaults to system default)
        """
        if unit is None:
            unit = self.default_area_unit

        space_template = self.templates.get_template_by_name("space")
        space_dict = {
            "name": self.building_ns[space_id],
            "area_name": self.building_ns[f"{space_id}_area"],
            "area_value": RDFLiteral(area_value),
            "area_unit": UNIT[unit],
        }

        self.evaluate_template(space_template, space_dict)

        has_space_template = self.templates.get_template_by_name("has-space")
        space_relation_dict = {
            "name": self.building_ns[zone_id],
            "target": self.building_ns[space_id],
        }

        # Handle S223 specific space relations
        if self.ontology == "s223":
            space_relation_dict["name-physical-space"] = self.building_ns[
                zone_id + "_physical_space"
            ]

        self.evaluate_template(has_space_template, space_relation_dict)
        logger.info(f"Added space: {space_id} to zone: {zone_id}")

    def save_model(
        self, filename: str, format: str = "turtle", add_inverse_relations: bool = True
    ) -> None:
        """
        Save the model to a file.

        Args:
            filename: Output filename
            format: RDF serialization format
            add_inverse_relations: Whether to add inverse relations (Brick only)
        """
        if add_inverse_relations and self.ontology == "brick":
            self.model.graph = add_brick_inverse_relations(self.model.graph)

        self.model.graph.serialize(filename, format=format)
        logger.info(f"Saved model to: {filename}")


# Backward compatibility alias
BrickModelBuilder = SemanticModelBuilder
