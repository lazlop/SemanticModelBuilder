"""
Point Management

Functionality for managing sensor and actuator points in semantic models.
"""

import logging
from typing import Any, Dict, List, Optional

from rdflib import Literal as RDFLiteral
from rdflib import Namespace

logger = logging.getLogger(__name__)


class PointManager:
    """Manage sensor and actuator points in semantic models."""

    def __init__(self, model_builder):
        """
        Initialize point manager.

        Args:
            model_builder: SemanticModelBuilder instance
        """
        self.model_builder = model_builder
        self.templates = model_builder.templates
        self.building_ns = model_builder.building_ns
        self.ontology = model_builder.ontology

    def add_point(
        self,
        point_id: str,
        point_of: str,
        point_type: str,
        ref_name: str,
        ref_type: str = "volttron",
        unit: str = "DEG_C",
        point_template: Optional[str] = None,
    ) -> None:
        """
        Add a sensor or actuator point to the model.

        Args:
            point_id: Unique identifier for the point
            point_of: Equipment or space this point belongs to
            point_type: Type of point (e.g., 'Temperature_Sensor')
            ref_name: External reference name (e.g., topic name)
            ref_type: Type of external reference system
            unit: Unit of measurement
            point_template: Specific template to use (defaults to 'point')
        """
        if point_template is None:
            point_template = "point"

        try:
            # Get templates
            template = self.templates.get_template_by_name(point_template)
            ref_template = self.templates.get_template_by_name(
                f"{ref_type}-external-reference"
            )
            has_ref_template = self.templates.get_template_by_name("has-reference")
            has_point_template = self.templates.get_template_by_name("has-point")

            # Prepare point data
            point_dict = {
                "name": self.building_ns[point_id],
                "unit": (
                    self.model_builder.ontology_ns[unit]
                    if hasattr(self.model_builder.ontology_ns, unit)
                    else RDFLiteral(unit)
                ),
            }

            # Add point type for generic point template
            if point_template == "point":
                point_dict["point_type"] = self.model_builder.ontology_ns[point_type]

            # Prepare reference data
            ref_dict = {
                "name": self.building_ns[f"{point_id}_ref"],
                "ref_name": RDFLiteral(ref_name),
            }

            # Evaluate templates
            self.model_builder.evaluate_template(template, point_dict)
            self.model_builder.evaluate_template(ref_template, ref_dict)

            # Add relationships
            self.model_builder.evaluate_template(
                has_ref_template,
                {"name": point_dict["name"], "target": ref_dict["name"]},
            )

            self.model_builder.evaluate_template(
                has_point_template,
                {"name": self.building_ns[point_of], "target": point_dict["name"]},
            )

            logger.info(f"Added point: {point_id} to {point_of}")

        except Exception as e:
            logger.error(f"Failed to add point {point_id}: {e}")
            raise

    def add_temperature_sensor(
        self, point_id: str, point_of: str, ref_name: str, unit: str = "DEG_C"
    ) -> None:
        """
        Add a temperature sensor point.

        Args:
            point_id: Unique identifier for the sensor
            point_of: Equipment or space this sensor monitors
            ref_name: External reference name
            unit: Temperature unit
        """
        point_type = "Temperature_Sensor"
        if self.ontology == "s223":
            point_template = "temperature"
        else:
            point_template = "point"

        self.add_point(
            point_id=point_id,
            point_of=point_of,
            point_type=point_type,
            ref_name=ref_name,
            unit=unit,
            point_template=point_template,
        )

    def add_temperature_setpoint(
        self,
        point_id: str,
        point_of: str,
        ref_name: str,
        setpoint_type: str = "heating",
        occupancy: str = "occupied",
        unit: str = "DEG_C",
    ) -> None:
        """
        Add a temperature setpoint.

        Args:
            point_id: Unique identifier for the setpoint
            point_of: Equipment this setpoint controls
            ref_name: External reference name
            setpoint_type: Type of setpoint ('heating' or 'cooling')
            occupancy: Occupancy mode ('occupied' or 'unoccupied')
            unit: Temperature unit
        """
        if self.ontology == "s223":
            # Use specific S223 setpoint templates
            if occupancy == "occupied":
                if setpoint_type == "heating":
                    point_template = "occ-heating-setpoint"
                else:
                    point_template = "occ-cooling-setpoint"
            else:
                if setpoint_type == "heating":
                    point_template = "unocc-heating-setpoint"
                else:
                    point_template = "unocc-cooling-setpoint"
        else:
            # Use generic Brick point
            point_template = "point"
            if occupancy == "occupied":
                if setpoint_type == "heating":
                    point_type = "Occupied_Heating_Temperature_Setpoint"
                else:
                    point_type = "Occupied_Cooling_Temperature_Setpoint"
            else:
                if setpoint_type == "heating":
                    point_type = "Unoccupied_Heating_Temperature_Setpoint"
                else:
                    point_type = "Unoccupied_Cooling_Temperature_Setpoint"

        if self.ontology == "s223":
            # For S223, we don't need point_type as it's in the template
            self.add_point(
                point_id=point_id,
                point_of=point_of,
                point_type="",  # Not used for S223 specific templates
                ref_name=ref_name,
                unit=unit,
                point_template=point_template,
            )
        else:
            self.add_point(
                point_id=point_id,
                point_of=point_of,
                point_type=point_type,
                ref_name=ref_name,
                unit=unit,
                point_template=point_template,
            )

    def add_occupancy_sensor(self, point_id: str, point_of: str, ref_name: str) -> None:
        """
        Add an occupancy sensor.

        Args:
            point_id: Unique identifier for the sensor
            point_of: Space this sensor monitors
            ref_name: External reference name
        """
        self.add_point(
            point_id=point_id,
            point_of=point_of,
            point_type="Occupancy_Sensor",
            ref_name=ref_name,
            unit="NUM",  # Dimensionless
        )

    def add_stage_status(
        self, point_id: str, point_of: str, ref_name: str, stage_type: str = "heating"
    ) -> None:
        """
        Add a heating/cooling stage status point.

        Args:
            point_id: Unique identifier for the status point
            point_of: Equipment this status monitors
            ref_name: External reference name
            stage_type: Type of stage ('heating' or 'cooling')
        """
        if self.ontology == "s223":
            if stage_type == "heating":
                point_template = "active-heating-stages"
            else:
                point_template = "active-cooling-stages"
        else:
            point_template = "point"
            if stage_type == "heating":
                point_type = "Heating_Stage_Status"
            else:
                point_type = "Cooling_Stage_Status"

        if self.ontology == "s223":
            self.add_point(
                point_id=point_id,
                point_of=point_of,
                point_type="",
                ref_name=ref_name,
                unit="NUM",
                point_template=point_template,
            )
        else:
            self.add_point(
                point_id=point_id,
                point_of=point_of,
                point_type=point_type,
                ref_name=ref_name,
                unit="NUM",
                point_template=point_template,
            )

    def list_points(self) -> List[Dict[str, Any]]:
        """
        List all points in the model.

        Returns:
            List of point information dictionaries
        """
        points = []

        # Query the model for points
        if self.ontology == "brick":
            query = """
            PREFIX brick: <https://brickschema.org/schema/Brick#>
            SELECT ?point ?type ?equipment WHERE {
                ?point a ?type .
                ?type rdfs:subClassOf* brick:Point .
                OPTIONAL { ?equipment brick:hasPoint ?point }
            }
            """
        else:  # s223
            query = """
            PREFIX s223: <http://data.ashrae.org/standard223#>
            SELECT ?point ?type ?equipment WHERE {
                ?point a ?type .
                ?type rdfs:subClassOf* s223:Property .
                OPTIONAL { ?equipment s223:hasProperty ?point }
            }
            """

        try:
            for row in self.model_builder.graph.query(query):
                points.append(
                    {
                        "point_id": str(row.point).split("#")[-1],
                        "point_type": str(row.type).split("#")[-1],
                        "equipment": (
                            str(row.equipment).split("#")[-1] if row.equipment else None
                        ),
                    }
                )
        except Exception as e:
            logger.error(f"Failed to list points: {e}")

        return points
