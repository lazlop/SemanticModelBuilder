"""
Grafana integration for semantic building models.

This module provides functionality to generate Grafana dashboards
from semantic building models.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class BrickToGrafana:
    """Convert Brick/S223 models to Grafana dashboards."""

    def __init__(self, model_graph=None):
        """
        Initialize the Grafana converter.

        Args:
            model_graph: RDF graph containing the building model
        """
        self.model_graph = model_graph
        self.dashboard_config = {}

    def generate_dashboard(
        self, title: str = "Building Dashboard", datasource: str = "prometheus"
    ) -> Dict[str, Any]:
        """
        Generate a Grafana dashboard from the building model.

        Args:
            title: Dashboard title
            datasource: Data source name

        Returns:
            Grafana dashboard configuration
        """
        dashboard = {
            "dashboard": {
                "id": None,
                "title": title,
                "tags": ["building", "semantic"],
                "timezone": "browser",
                "panels": [],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "5s",
            }
        }

        if self.model_graph:
            panels = self._extract_panels_from_model()
            dashboard["dashboard"]["panels"] = panels

        return dashboard

    def _extract_panels_from_model(self) -> List[Dict[str, Any]]:
        """Extract panel configurations from the semantic model."""
        panels = []

        # Query for temperature sensors
        temp_panels = self._create_temperature_panels()
        panels.extend(temp_panels)

        # Query for power/energy points
        power_panels = self._create_power_panels()
        panels.extend(power_panels)

        return panels

    def _create_temperature_panels(self) -> List[Dict[str, Any]]:
        """Create panels for temperature sensors."""
        panels = []

        # Example temperature panel
        temp_panel = {
            "id": 1,
            "title": "Zone Temperatures",
            "type": "graph",
            "targets": [{"expr": "temperature_sensor", "legendFormat": "{{zone}}"}],
            "yAxes": [{"label": "Temperature (°C)", "min": 15, "max": 30}],
        }
        panels.append(temp_panel)

        return panels

    def _create_power_panels(self) -> List[Dict[str, Any]]:
        """Create panels for power/energy metrics."""
        panels = []

        # Example power panel
        power_panel = {
            "id": 2,
            "title": "HVAC Power Consumption",
            "type": "graph",
            "targets": [{"expr": "hvac_power", "legendFormat": "{{equipment}}"}],
            "yAxes": [{"label": "Power (kW)", "min": 0}],
        }
        panels.append(power_panel)

        return panels

    def save_dashboard(self, dashboard: Dict[str, Any], output_path: Path) -> None:
        """
        Save dashboard configuration to a file.

        Args:
            dashboard: Dashboard configuration
            output_path: Output file path
        """
        with open(output_path, "w") as f:
            json.dump(dashboard, f, indent=2)

    def export_to_grafana(
        self, dashboard: Dict[str, Any], grafana_url: str, api_key: str
    ) -> bool:
        """
        Export dashboard directly to Grafana instance.

        Args:
            dashboard: Dashboard configuration
            grafana_url: Grafana instance URL
            api_key: Grafana API key

        Returns:
            True if successful, False otherwise
        """
        import requests

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{grafana_url}/api/dashboards/db", headers=headers, json=dashboard
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error exporting to Grafana: {e}")
            return False
