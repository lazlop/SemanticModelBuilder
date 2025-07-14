
from grafanalib.core import (
    Dashboard, TimeSeries, GaugePanel,
    Target, GridPos, SqlTarget,
    OPS_FORMAT
)
from buildingmotif.namespaces import bind_prefixes
from .namespaces import BRICK, UNIT, QUDT, HPF, A, RDF, RDFS, REF
from rdflib import Graph, URIRef, Variable
from typing import List, Dict, Optional, Any
import json
import requests
import yaml
from .utils import get_prefixes
from grafanalib._gen import DashboardEncoder

DEFAULT_QUERY = """SELECT 
                ts AS "time", 
                CAST(value_string AS FLOAT) AS "{point_type}"
            FROM 
                data 
            WHERE 
                topic_id in (select topic_id from topics where topic_name = '{point_id}')
            AND 
                $__timeFilter(ts) 
            ORDER BY 1"""

DEFAULT_SPARQL_REF = """
        ?point ref:hasExternalReference/ref:hasTopic ?point_id .
"""

class BrickToGrafana:
    """Class to handle conversion of Brick models to Grafana dashboards"""
    
    def __init__(self, grafana_server: str, grafana_api_key: str, datasource, ttl_path: str):
        """Initialize with Grafana connection details
        
        Args:
            grafana_server: URL of the Grafana server
            grafana_api_key: API key with admin privileges
        """
        self.grafana_server = grafana_server
        self.grafana_api_key = grafana_api_key
        self.datasource = datasource
        self.g = Graph(store = 'Oxigraph')
        self.g.parse('https://brickschema.org/schema/Brick.ttl', format='turtle')
        bind_prefixes(self.g)
        self.g.parse(ttl_path, format="turtle")
        self.prefixes = get_prefixes(self.g)
        self.panels = []
        self.dashboard = None

      
    def _get_points(self, point_types, sparql_ref = DEFAULT_SPARQL_REF) -> Dict[str, List[str]]:
        
        all_points = f"""
                {self.prefixes}
                SELECT ?point ?point_id ?point_type ?zone_panel ?other_panel
                WHERE {{
                    ?point a ?point_type .
                    ?point_type rdfs:subClassOf* ?point_super_type .
                    ?zone a/rdfs:subClassOf* brick:Zone .
                    ?zone_panel brick:feeds? ?zone ;
                            brick:hasPoint ?point . 
                    OPTIONAL {{
                        ?other_panel brick:hasPoint ?point . 
                        FILTER (?other_panel != ?zone_panel)
                    }}
                    {sparql_ref}
                    FILTER (?point_super_type IN ({','.join(['brick:'+ point for point in point_types])})) .
            }}"""
        point_results = self.g.query(all_points)
        return point_results

    def _get_sql(self, point_id, point_type, sql_query = DEFAULT_QUERY):
        return sql_query.format(point_id=point_id, point_type=point_type)

    def create_dashboard(self, title, point_types = ['Sensor','Setpoint','Command','Status']):
        """Create a Grafana dashboard from a Brick model"""
        # TODO: Consider defining rows for the dashboard by zone/hvac, then having different panels for different groups of points
        # TODO: eg: Row 1 = HVAC1, Panel 1: Sensors and Setpoints, Panel 2: Commands and Statuses, Panel 3: Power Readings
        point_results = self._get_points(point_types=point_types)
        panel_dict_list = {}
        for binding in point_results.bindings:
            panel_name = binding[Variable('zone_panel')] if binding[Variable('zone_panel')] else binding[Variable('other_panel')]
            panel_name = self.g.compute_qname(panel_name)[-1]
            point_type=self.g.compute_qname(binding[Variable('point_type')])[-1]
            query =  self._get_sql(binding[Variable('point_id')], point_type)
            if panel_name not in panel_dict_list:
                panel_dict_list[panel_name] = {
                    'title': panel_name,
                    'query_dict': {point_type:query}
                }
            else:
                panel_dict_list[panel_name]['query_dict'][point_type] = query

        y= 0
        panels = []
        for name, panel in panel_dict_list.items():
            panels.append(self._create_timeseries_panel(panel['title'], panel['query_dict'], y))
            y+=10

        dashboard = Dashboard(
            title=title,
            description="Zone-based dashboard generated from Brick model",
            tags=['brick'],
            timezone="browser",
            panels=self.panels,
        ).auto_panel_ids()
        self.dashboard = dashboard
        return dashboard
    
    def _create_timeseries_panel(self, title: str, sql_query_dict,y):
        targets = []
        for name, query in sql_query_dict.items():
            targets.append(
                SqlTarget(
                    datasource=self.datasource,
                    rawSql = query,
                    refId = name
                )
            )
        panel = TimeSeries(
                title=title,
                dataSource=self.datasource,
                targets=targets,
                gridPos=GridPos(h=8, w=16, x=0, y=y),
            )
        panel.overrides = [{
            "matcher": {
              "id": "byValue",
              "options": {
                "op": "lte",
                "reducer": "max",
                "value": 10
              }
            },
            "properties": [
              {
                "id": "custom.axisPlacement",
                "value": "right"
              }
            ]},
            {
            "matcher": {
              "id": "byValue",
              "options": {
                "op": "gte",
                "reducer": "allIsZero",
                "value": 0
              }
            },
            "properties": [
              {
                "id": "custom.hideFrom",
                "value": {
                  "legend": True,
                  "tooltip": False,
                  "viz": True
                }
              }
            ]
          }]
        
        self.panels.append(panel)
        return panel
    
    def upload_dashboard(self, overwrite: bool = True,
                        message: str = "Updated by BrickToGrafana") -> None:
        """Upload a dashboard to Grafana
        
        Args:
            dashboard: Dashboard object to upload
            overwrite: Whether to overwrite existing dashboard
            message: Commit message for the dashboard
        """
        json_data = self._get_dashboard_json(self.dashboard, overwrite, message)
        self._upload_to_grafana(json_data)
    def _add_datasource(self):
        """ Add a datasource to Grafana. 
        Currently not implemented. Depends significantly on networking setup of Grafana
        """
        pass
    def _get_dashboard_json(self, dashboard: Dashboard, overwrite: bool = False,
                          message: str = "Updated by BrickToGrafana") -> str:
        """Generate JSON representation of a dashboard
        
        Args:
            dashboard: Dashboard object
            overwrite: Whether to overwrite existing dashboard
            message: Commit message
            
        Returns:
            JSON string representation of the dashboard
        """
        return json.dumps(
            {
                "dashboard": dashboard.to_json_data(),
                "overwrite": overwrite,
                "message": message
            }, sort_keys=True, indent=2, cls=DashboardEncoder)
            
    def _upload_to_grafana(self, json_data: str, verify: bool = True) -> None:
        """Upload dashboard JSON to Grafana
        
        Args:
            json_data: Dashboard JSON string
            verify: Whether to verify SSL certificate
        """
        headers = {'Authorization': f"Bearer {self.grafana_api_key}",
                  'Content-Type': 'application/json'}
        r = requests.post(
            f"{self.grafana_server}api/dashboards/db",
            data=json_data,
            headers=headers,
            verify=verify
        )
        print(f"Upload status: {r.status_code} - {r.content}")