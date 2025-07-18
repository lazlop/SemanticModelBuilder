"""
Metadata Processing

Functionality for generating, reading, and processing building metadata surveys.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SurveyGenerator:
    """Generate building metadata surveys."""
    
    def __init__(self):
        self.survey_template = self._load_survey_template()
    
    def _load_survey_template(self) -> Dict[str, Any]:
        """Load the base survey template."""
        # This would load from a JSON template file
        return {
            "survey_info": {
                "title": "Building Metadata Survey",
                "version": "1.0",
                "description": "Collect building information for semantic model creation"
            },
            "sections": []
        }
    
    def generate_building_survey(self) -> Dict[str, Any]:
        """Generate a complete building survey."""
        survey = self.survey_template.copy()
        
        # Add sections
        survey["sections"].extend([
            self._generate_site_section(),
            self._generate_spaces_section(),
            self._generate_hvac_section(),
            self._generate_points_section()
        ])
        
        return survey
    
    def _generate_site_section(self) -> Dict[str, Any]:
        """Generate site information section."""
        return {
            "id": "site_info",
            "title": "Site Information",
            "fields": [
                {
                    "id": "site_id",
                    "type": "text",
                    "label": "Site ID",
                    "required": True
                },
                {
                    "id": "timezone",
                    "type": "select",
                    "label": "Timezone",
                    "options": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
                    "required": True
                },
                {
                    "id": "latitude",
                    "type": "number",
                    "label": "Latitude",
                    "required": True
                },
                {
                    "id": "longitude", 
                    "type": "number",
                    "label": "Longitude",
                    "required": True
                }
            ]
        }
    
    def _generate_spaces_section(self) -> Dict[str, Any]:
        """Generate spaces section."""
        return {
            "id": "spaces",
            "title": "Spaces and Zones",
            "type": "repeatable",
            "fields": [
                {
                    "id": "space_id",
                    "type": "text", 
                    "label": "Space ID",
                    "required": True
                },
                {
                    "id": "zone_id",
                    "type": "text",
                    "label": "Zone ID", 
                    "required": True
                },
                {
                    "id": "area",
                    "type": "number",
                    "label": "Floor Area",
                    "required": True
                },
                {
                    "id": "area_unit",
                    "type": "select",
                    "label": "Area Unit",
                    "options": ["M2", "FT2"],
                    "default": "M2"
                }
            ]
        }
    
    def _generate_hvac_section(self) -> Dict[str, Any]:
        """Generate HVAC equipment section."""
        return {
            "id": "hvac",
            "title": "HVAC Equipment",
            "type": "repeatable",
            "fields": [
                {
                    "id": "equipment_id",
                    "type": "text",
                    "label": "Equipment ID",
                    "required": True
                },
                {
                    "id": "equipment_type",
                    "type": "select",
                    "label": "Equipment Type",
                    "options": ["hp-rtu", "boiler", "chiller", "ahu"],
                    "required": True
                },
                {
                    "id": "serves_zones",
                    "type": "text",
                    "label": "Serves Zones (comma-separated)",
                    "required": True
                }
            ]
        }
    
    def _generate_points_section(self) -> Dict[str, Any]:
        """Generate points section."""
        return {
            "id": "points",
            "title": "Sensor and Control Points",
            "type": "repeatable", 
            "fields": [
                {
                    "id": "point_id",
                    "type": "text",
                    "label": "Point ID",
                    "required": True
                },
                {
                    "id": "point_type",
                    "type": "select",
                    "label": "Point Type",
                    "options": ["Temperature_Sensor", "Temperature_Setpoint", "Occupancy_Sensor"],
                    "required": True
                },
                {
                    "id": "equipment_id",
                    "type": "text",
                    "label": "Associated Equipment",
                    "required": False
                }
            ]
        }
    
    def save_survey(self, survey: Dict[str, Any], filename: str) -> None:
        """Save survey to JSON file."""
        with open(filename, 'w') as f:
            json.dump(survey, f, indent=2)
        logger.info(f"Survey saved to: {filename}")


class SurveyReader:
    """Read and validate survey responses."""
    
    def __init__(self, survey_file: Optional[str] = None):
        self.survey = None
        if survey_file:
            self.load_survey(survey_file)
        self.responses = {}
        self.validation_errors = []
    
    def load_survey(self, filename: str) -> None:
        """Load survey template from file."""
        with open(filename, 'r') as f:
            self.survey = json.load(f)
        logger.info(f"Survey loaded from: {filename}")
    
    def read_responses(self, filename: str) -> Dict[str, Any]:
        """Read survey responses from file."""
        with open(filename, 'r') as f:
            self.responses = json.load(f)
        logger.info(f"Responses loaded from: {filename}")
        return self.responses
    
    def validate_responses(self) -> List[str]:
        """Validate survey responses against survey template."""
        self.validation_errors = []
        
        if not self.survey:
            self.validation_errors.append("No survey template loaded")
            return self.validation_errors
        
        # Validate each section
        for section in self.survey.get("sections", []):
            self._validate_section(section)
        
        return self.validation_errors
    
    def _validate_section(self, section: Dict[str, Any]) -> None:
        """Validate a single survey section."""
        section_id = section.get("id")
        section_responses = self.responses.get(section_id, {})
        
        # Check required fields
        for field in section.get("fields", []):
            field_id = field.get("id")
            if field.get("required", False) and field_id not in section_responses:
                self.validation_errors.append(
                    f"Required field '{field_id}' missing in section '{section_id}'"
                )


class MetadataProcessor:
    """Process metadata for semantic model creation."""
    
    def __init__(self):
        self.data = {}
    
    def load_from_csv(self, filename: str) -> pd.DataFrame:
        """Load metadata from CSV file."""
        df = pd.read_csv(filename)
        logger.info(f"Loaded metadata from CSV: {filename}")
        return df
    
    def load_from_survey(self, responses: Dict[str, Any]) -> None:
        """Load metadata from survey responses."""
        self.data = responses
        logger.info("Loaded metadata from survey responses")
    
    def extract_site_info(self) -> Dict[str, Any]:
        """Extract site information from metadata."""
        site_info = self.data.get("site_info", {})
        return {
            "site_id": site_info.get("site_id"),
            "timezone": site_info.get("timezone"),
            "latitude": float(site_info.get("latitude", 0)),
            "longitude": float(site_info.get("longitude", 0)),
            "noaa_station": site_info.get("noaa_station", "")
        }
    
    def extract_spaces(self) -> List[Dict[str, Any]]:
        """Extract space information from metadata."""
        spaces = self.data.get("spaces", [])
        if isinstance(spaces, dict):
            spaces = [spaces]
        
        return [
            {
                "space_id": space.get("space_id"),
                "zone_id": space.get("zone_id"),
                "area": float(space.get("area", 0)),
                "area_unit": space.get("area_unit", "M2")
            }
            for space in spaces
        ]
    
    def extract_hvac_equipment(self) -> List[Dict[str, Any]]:
        """Extract HVAC equipment information from metadata."""
        hvac = self.data.get("hvac", [])
        if isinstance(hvac, dict):
            hvac = [hvac]
        
        return [
            {
                "equipment_id": equip.get("equipment_id"),
                "equipment_type": equip.get("equipment_type"),
                "serves_zones": equip.get("serves_zones", "").split(",")
            }
            for equip in hvac
        ]