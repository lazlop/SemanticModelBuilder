import csv
import json
from pathlib import Path
from typing import Any, Dict, Union

from .model_builder import ModelBuilder


class SurveyReader:
    def __init__(self, survey_directory: str, ontology="brick"):
        self.base_dir = Path(survey_directory)
        self.config = self._load_config()
        self.site_info = self._load_site_info()
        self.ontology = ontology

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        with open(self.base_dir / "config.json", "r") as f:
            return json.load(f)

    def _validate_csv_row(self, row: Dict[str, str], context: str) -> bool:
        """
        Validate a CSV row for empty values.

        Args:
            row: Dictionary representing a CSV row
            context: Context string for error messages (e.g., "Zone", "HVAC")

        Returns:
            bool: True if row is valid, False if row should be skipped

        Raises:
            ValueError: If row has partial empty values
        """

        def is_empty_value(value):
            """Check if a value is considered empty"""
            if value is None:
                return True
            if isinstance(value, str):
                # Check for empty string, whitespace-only string, or common empty representations
                stripped = value.strip()
                return (
                    stripped == ""
                    or stripped.lower() in ["nan", "none", "null", "na", "n/a", ""]
                    or stripped == ""
                )
            # Handle other types that might be empty (e.g., from pandas)
            try:
                import numpy as np

                if isinstance(value, (float, int)) and np.isnan(value):
                    return True
            except (ImportError, TypeError):
                pass
            try:
                import pandas as pd

                if pd.isna(value):
                    return True
            except (ImportError, AttributeError):
                pass
            return False

        # Check if row is completely empty
        if all(is_empty_value(value) for value in row.values()):
            return False

        # Check for any empty values
        skip_fields = ["NOAAstation", "noaa_station"]
        empty_fields = [
            field
            for field, value in row.items()
            if is_empty_value(value) and field not in skip_fields
        ]
        if empty_fields:
            raise ValueError(
                f"{context} row has empty values for fields: {', '.join(empty_fields)}"
            )

        return True

    def _load_site_info(self) -> Dict[str, str]:
        """Load site information from site_info.csv"""
        with open(self.base_dir / "site_info.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._validate_csv_row(row, "Site info"):
                    return row
        raise ValueError("No valid site info found")

    def _load_zones(self) -> list:
        """Load zone information from zones.csv"""
        zones = []
        with open(self.base_dir / "zones" / "zones.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._validate_csv_row(row, "Zone"):
                    zones.append(row)
        return zones

    def _load_spaces(self, zone_id: str) -> list:
        """Load space information for a specific zone"""
        spaces = []
        with open(self.base_dir / "spaces" / f"{zone_id}_spaces.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._validate_csv_row(row, f"Space for zone {zone_id}"):
                    spaces.append(row)
        return spaces

    def _load_hvac(self) -> list:
        """Load HVAC information from hvac_units.csv"""
        hvac_units = []
        with open(self.base_dir / "hvac" / "hvac_units.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._validate_csv_row(row, "HVAC"):
                    hvac_units.append(row)
        return hvac_units

    def _load_windows(self, zone_id) -> list:
        """Load window information from windows.csv"""
        windows = []
        with open(self.base_dir / "windows" / f"{zone_id}_windows.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._validate_csv_row(row, f"Window for zone {zone_id}"):
                    windows.append(row)
        return windows

    def create_model(self, output_file: Union[str, None] = None):
        """Generate the Brick model from the survey data"""
        # Initialize the model builder with site information
        builder = ModelBuilder(
            site_id=self.site_info["site_id"], ontology=self.ontology
        )
        builder.add_site(
            timezone=self.site_info["timezone"],
            latitude=float(self.site_info["latitude"]),
            longitude=float(self.site_info["longitude"]),
            noaa_station=self.site_info["noaa_station"],
        )
        # Process zones and their associated equipment
        zones = self._load_zones()
        for zone in zones:
            zone_id = zone["zone_id"]

            # Add zone
            builder.add_zone(zone_id)

            # Add thermostat for the zone
            builder.add_thermostat(
                tstat_id=zone["tstat_id"],
                zone_id=zone_id,
                stage_count=int(zone["stage_count"]),
                setpoint_deadband=float(zone["setpoint_deadband"]),
                tolerance=float(zone["tolerance"]),
                active=zone["active"].lower() == "true",
                resolution=zone["resolution"],
                unit=zone["temperature_unit"],
            )

            # Add spaces for the zone
            spaces = self._load_spaces(zone_id)
            for space in spaces:
                builder.add_space(
                    space_id=space["space_id"],
                    zone_id=zone_id,
                    area_value=float(space["area_value"]),
                    unit=space["area_unit"],
                )
            # Add windows
            windows = self._load_windows(zone_id)
            for window in windows:
                builder.add_window(
                    window_id=window["window_id"],
                    zone_id=zone_id,
                    area_value=float(window["area_value"]),
                    azimuth_value=float(window["azimuth_value"]),
                    tilt_value=float(window["tilt_value"]),
                    unit=window["area_unit"],
                )

        # Add HVAC units
        hvac_units = self._load_hvac()
        for hvac in hvac_units:
            if hvac in list(self.config["hvacs_feed_zones"].keys()):
                # TODO: may want to get zone_id from config - a little weird having two sources for this.
                builder.add_hvac(
                    hvac_id=hvac["hvac_id"],
                    feeds_ids=hvac["zone_id"],
                    cooling_capacity=float(hvac["cooling_capacity"]),
                    heating_capacity=float(hvac["heating_capacity"]),
                    cooling_cop=float(hvac["cooling_cop"]),
                    heating_cop=float(hvac["heating_cop"]),
                )
            if hvac in list(self.config["hvacs_feed_hvacs"].keys()):
                feeds_hvacs = self.config["hvacs_feed_hvacs"][hvac]
                builder.add_hvac(
                    hvac_id=hvac["hvac_id"],
                    feeds_ids=feeds_hvacs,
                    cooling_capacity=float(hvac["cooling_capacity"]),
                    heating_capacity=float(hvac["heating_capacity"]),
                    cooling_cop=float(hvac["cooling_cop"]),
                    heating_cop=float(hvac["heating_cop"]),
                )

        self.graph = builder.model.graph
        self.builder = builder

        if output_file:
            # Save the model
            builder.save_model(output_file)
