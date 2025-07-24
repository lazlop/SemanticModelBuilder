"""
Semantic Model Builder

Core functionality for building semantic building models using Brick Schema
and ASHRAE Standard 223P ontologies.
"""

import os
from importlib.resources import files
from typing import Literal as PyLiteral

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from rdflib import Graph, Literal, Namespace, URIRef

from .namespaces import *
from .utils import add_brick_inverse_relations


# TODO: make base class and create Brick and 223P versions
class ModelBuilder:
    def __init__(
        self,
        site_id: str,
        ontology: PyLiteral["brick", "s223"] = "brick",
        system_of_units: PyLiteral["SI", "IP"] = "SI",
        hvac_type: str = "hp-rtu",
        tstat_type: str = "tstat-static-properties",
    ):
        # ontology can be brick or s223
        # Should change ontology to template directory if making a package
        self.bm = BuildingMOTIF("sqlite://")
        self.site_id = site_id
        self.building_ns = Namespace(f"urn:hpflex/{self.site_id}#")
        self.model = Model.create(self.building_ns)
        self.graph = self.model.graph
        self.system_of_units = system_of_units
        if system_of_units == "SI":
            self.default_temperature_unit = "DEG_C"
            self.default_area_unit = "M2"
        elif system_of_units == "IP":
            self.default_temperature_unit = "DEG_F"
            self.default_area_unit = "FT2"
        else:
            raise (ValueError("Invalid system of units. Must be 'SI' or 'IP'"))

        bind_prefixes(self.graph)
        self.graph.bind("bldg", self.building_ns)

        self.hvac_type = hvac_type
        self.tstat_type = tstat_type
        self.ontology = ontology
        self._load_templates()

    def _bind_namespaces(self):
        bind_prefixes(self.model.graph)

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

    def evaluate_template(self, template, data, fill=False):
        graph = template.inline_dependencies().evaluate(data)
        if fill & ~isinstance(graph, Graph):
            print("Filling template parameters: ", graph.all_parameters)
            bindings, graph = graph.fill(self.building_ns)
        try:
            self.model.add_graph(graph)
        except TypeError as e:
            print(e)
            raise TypeError(
                f"Template not complete, Additional Parameters needed: {graph.parameters}"
            )

    def add_site(self, timezone, latitude, longitude, noaa_station):
        site_template = self.templates.get_template_by_name("site")
        site_info = {
            "name": self.building_ns[self.site_id],
            "timezone": self.building_ns[f"{self.site_id}.timezone"],
            "timezone_value": Literal(timezone),
            "latitude": self.building_ns[f"{self.site_id}.latitude"],
            "latitude_value": Literal(latitude),
            "longitude": self.building_ns[f"{self.site_id}.longitude"],
            "longitude_value": Literal(longitude),
            "noaastation": self.building_ns[f"{self.site_id}.noaastation"],
            "noaastation_value": Literal(noaa_station),
        }
        self.evaluate_template(site_template, site_info)
        self.model.graph.add(
            (self.building_ns[""], A, Namespace("urn:hpflex#")["Project"])
        )

    def add_zone(self, zone_id):
        # Zone and thermostat could be combined
        zone_template = self.templates.get_template_by_name("hvac-zone")
        self.evaluate_template(zone_template, {"name": self.building_ns[zone_id]})
        # Not sure below relation is necessary.
        # self.model.graph.add((self.building_ns[self.site_id], BRICK.hasPart, self.building_ns[zone_id]))

    def add_window(
        self, window_id, zone_id, area_value, azimuth_value, tilt_value, unit=None
    ):
        if unit == None:
            unit = self.default_area_unit
        window_template = self.templates.get_template_by_name("window")
        window_dict = {
            "name": self.building_ns[window_id],
            "area_name": self.building_ns[f"{window_id}_area"],
            "azimuth_name": self.building_ns[f"{window_id}_azimuth"],
            "tilt_name": self.building_ns[f"{window_id}_tilt"],
            "area_value": Literal(area_value),
            "azimuth_value": Literal(azimuth_value),
            "tilt_value": Literal(tilt_value),
            "area_unit": UNIT[unit],
        }
        self.evaluate_template(window_template, window_dict)
        has_window_template = self.templates.get_template_by_name("has-window")
        self.evaluate_template(
            has_window_template,
            {"name": self.building_ns[zone_id], "target": self.building_ns[window_id]},
            fill=True,
        )
        # Add to brick template
        # self.model.graph.add((self.building_ns[zone_id], BRICK.hasPart, self.building_ns[window_id]))

    def add_thermostat(
        self,
        tstat_id,
        zone_id,
        stage_count,
        setpoint_deadband,
        tolerance,
        active,
        resolution,
        unit=None,
    ):
        if unit == None:
            unit = self.default_temperature_unit
        tstat_template = self.templates.get_template_by_name(self.tstat_type)
        tstat_dict = {
            "name": self.building_ns[tstat_id],
            "stage_count": self.building_ns[f"{tstat_id}_stage_count"],
            "stage_count-value": Literal(stage_count),
            "setpoint_deadband": self.building_ns[f"{tstat_id}_setpoint_deadband"],
            "setpoint_deadband-value": Literal(setpoint_deadband),
            "setpoint_deadband-unit": UNIT[unit],
            "tolerance": self.building_ns[f"{tstat_id}_tolerance"],
            "tolerance-value": Literal(tolerance),
            "tolerance-unit": UNIT[unit],
            "active": self.building_ns[f"{tstat_id}_active"],
            "active-value": Literal(active),
            "resolution": self.building_ns[f"{tstat_id}_resolution"],
            "resolution-value": Literal(resolution),
            "resolution-unit": UNIT[unit],
        }
        self.evaluate_template(tstat_template, tstat_dict)
        has_location_template = self.templates.get_template_by_name("has-location")
        self.evaluate_template(
            has_location_template,
            {"name": self.building_ns[tstat_id], "target": self.building_ns[zone_id]},
        )
        # add below to brick template
        # self.model.graph.add((self.building_ns[zone_id], BRICK.isLocationOf, self.building_ns[tstat_id]))

    def add_hvac(
        self,
        hvac_id,
        feeds_ids,
        cooling_capacity,
        heating_capacity,
        cooling_cop,
        heating_cop,
    ):
        hvac_template = self.templates.get_template_by_name(self.hvac_type)
        hvac_dict = {
            "name": self.building_ns[hvac_id],
            "cooling_capacity_name": self.building_ns[f"{hvac_id}_cooling_capacity"],
            "heating_capacity_name": self.building_ns[f"{hvac_id}_heating_capacity"],
            "cooling_capacity_value": Literal(cooling_capacity),
            "heating_capacity_value": Literal(heating_capacity),
            "cooling_COP_name": self.building_ns[f"{hvac_id}_cooling_COP"],
            "heating_COP_name": self.building_ns[f"{hvac_id}_heating_COP"],
            "cooling_COP_value": Literal(cooling_cop),
            "heating_COP_value": Literal(heating_cop),
        }
        self.evaluate_template(hvac_template, hvac_dict)
        print(feeds_ids)
        if isinstance(feeds_ids, list):
            for feeds_id in feeds_ids:
                self._add_feeds(hvac_id, feeds_id)
        else:
            self._add_feeds(hvac_id, feeds_ids)
        return

    def _add_feeds(self, from_id, to_id):
        template = self.templates.get_template_by_name("air-connects-to")
        self.evaluate_template(
            template,
            {
                "name": self.building_ns[from_id],
                "target": self.building_ns[to_id],
            },
            fill=True,
        )

        # self.evaluate_template(template, {
        #     'name':self.building_ns[from_id],
        #     'target':self.building_ns[to_id],
        #     'name_outlet':self.building_ns[f'{from_id}_out'],
        #     'target_inlet':self.building_ns[f'{to_id}_in'],
        #     'connection':self.building_ns[f'{from_id}_{to_id}_connection']
        #     })

        # Add to brick template
        # self.model.graph.add((self.building_ns[from_id], BRICK.feeds, self.building_ns[to_id]))
        # self.model.graph.add((self.building_ns[to_id], BRICK.isFedBy, self.building_ns[from_id]))

    def add_space(self, space_id, zone_id, area_value, unit="M2"):
        space_template = self.templates.get_template_by_name("space")
        space_dict = {
            "name": self.building_ns[space_id],
            "area_name": self.building_ns[f"{space_id}_area"],
            "area_value": Literal(area_value),
            "area_unit": UNIT[unit],
        }
        self.evaluate_template(space_template, space_dict)
        has_space_template = self.templates.get_template_by_name("has-space")
        self.evaluate_template(
            has_space_template,
            {
                "name": self.building_ns[zone_id],
                "name-physical-space": self.building_ns[zone_id + "_physical_space"],
                "target": self.building_ns[space_id],
            },
        )
        # Add below for brick template
        # self.model.graph.add((self.building_ns[zone_id], BRICK.hasPart, self.building_ns[space_id]))

    def add_point(
        self, point_id, point_of, point_template, point_type, ref_name, ref_type, unit
    ):
        point_dict = {"name": self.building_ns[point_id], "unit": UNIT[unit]}
        template = self.templates.get_template_by_name(point_template)

        # probably don't want a generic point with user defined type - should all be templated.
        if template == "point":
            point_dict.update({"point_type": self.ontology_ns[point_type]})

        ref_template = self.templates.get_template_by_name(
            f"{ref_type}-external-reference"
        )
        has_ref_template = self.templates.get_template_by_name("has-reference")
        has_point_template = self.templates.get_template_by_name("has-point")
        ref_dict = {
            "name": self.building_ns[f"{point_id}_ref"],
            "ref_name": Literal(ref_name),
        }
        self.evaluate_template(template, point_dict)
        self.evaluate_template(ref_template, ref_dict)
        self.evaluate_template(
            has_ref_template, {"name": point_dict["name"], "target": ref_dict["name"]}
        )
        self.evaluate_template(
            has_point_template,
            {"name": self.building_ns[point_of], "target": point_dict["name"]},
        )

    def save_model(self, filename, add_inverse_relations=True):
        if add_inverse_relations:
            self.model.graph = add_brick_inverse_relations(self.model.graph)
        self.model.graph.serialize(filename, format="turtle")
