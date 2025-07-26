from rdflib import Graph, Namespace, Literal
import os
from typing import Dict, Any, Union, List, Optional
from .unit_conversion import convert_units
from .namespaces import * 

UNIT_CONVERSIONS = {
            UNIT["DEG_F"]: UNIT["DEG_C"],
            UNIT["FT"]: UNIT["M"],
            UNIT["FT2"]: UNIT["M2"],
            UNIT["FT3"]: UNIT["M3"],
            UNIT["PSI"]: UNIT["PA"],
            UNIT["DEGREE"]: UNIT["DEGREE"],  # Degrees don't need conversion
            UNIT["KILOW"]: UNIT["KILOW"]     # Kilowatts don't need conversion
        }
# Should probably have something like  .namespaces.bind_namespaces to put prefixes in all the queries
sparql_queries = {
    "convert_to_si": {"brick": """
        SELECT ?s ?v ?u ?isDelta
        WHERE {
            ?s brick:value ?v ;
            qudt:hasUnit ?u .
            OPTIONAL { ?s qudt:isDeltaQuantity ?isDelta } .
        }
        """,
        "s223": """
        SELECT ?s ?v ?u ?isDelta
        WHERE {
            ?s s223:hasValue ?v ;
            qudt:hasUnit ?u .
            OPTIONAL { ?s qudt:isDeltaQuantity ?isDelta } .
        }
        """
    },
    "site_info": {"brick": """""",
        "s223": """SELECT DISTINCT ?tz ?latitude ?longitude ?NOAAstation ?project_id ?site_id
        WHERE {
            ?site_id s223:hasProperty ?tzprop, ?latprop, ?longprop, ?noaprop, ?project_idprop, ?site_idprop .
            ?tzprop s223:hasValue ?tz ;
                a hpfs:timezone .
            ?latprop s223:hasValue ?latitude ;
                a hpfs:latitude .
            ?longprop s223:hasValue ?longitude ;
                a hpfs:longitude .
            ?noaprop s223:hasValue ?NOAAstation ;
                a hpfs:noaastation .
            ?site_id a hpfs:site .
            BIND(?site_id as ?project_id).
        }"""
    },
    "get_tstats": {"brick": """
                SELECT DISTINCT ?tstat ?zone 
                    WHERE {
                            ?tstat a brick:Thermostat ;
                                    brick:hasLocation ?zone .
                            ?zone a brick:HVAC_Zone .           
                                    }
            """,
        "s223": """SELECT DISTINCT ?tstat ?zone 
                    WHERE {
                            ?tstat a hpfs:tstat-static-properties ;
                                    hpfs:has-location ?zone .          
                                    
        }"""
    },
    "get_tstat_data": {"brick": """
                SELECT DISTINCT ?deadband_value ?tolerance_value ?active_value
                        ?stage_count ?resolution ?control_group WHERE {
                <%s> brick:hasPoint ?deadband, ?tolerance, ?active;
                    brick:operationalStageCount/brick:value ?stage_count ;
                    brick:resolution/brick:value ?resolution .
                ?deadband a brick:Temperature_Deadband_Setpoint ;
                    brick:value ?deadband_value .
                ?tolerance a brick:Temperature_Tolerance_Parameter ;
                    brick:value ?tolerance_value .
                ?active a brick:Availability_Status ;
                    brick:value ?active_value .
                BIND("DEPRECATED" as ?control_group)
            }""",
        "s223": """ SELECT DISTINCT ?deadband_value ?tolerance_value ?active_value ?stage_count ?resolution ?control_group
                WHERE {
                <%s> s223:hasProperty ?deadband, ?tolerance, ?active, ?stage_count_prop, ?resolution_prop.
                ?deadband a hpfs:tstat-deadband ;
                    s223:hasValue ?deadband_value.
                ?tolerance a hpfs:tstat-tolerance ;
                    s223:hasValue ?tolerance_value.
                ?active a hpfs:tstat-active ;
                    s223:hasValue ?active_value.
                ?stage_count_prop a hpfs:tstat-stage_count ;
                    s223:hasValue ?stage_count.
                ?resolution_prop a hpfs:tstat-resolution ;
                    s223:hasValue ?resolution.
                BIND("DEPRECATED" as ?control_group)
                }"""
    },
        "get_unit_data": {"brick": """
                SELECT DISTINCT ?zone ?hvac ?cooling_capacity ?cooling_capacity_unit ?heating_capacity ?heating_capacity_unit ?cooling_cop ?heating_cop  WHERE {
                <%s> brick:hasLocation ?zone .
                ?zone a brick:HVAC_Zone ;
                    brick:isFedBy ?hvac .
                ?hvac brick:coolingCapacity ?cooling_capacity_prop; 
                    brick:heatingCapacity ?heating_capacity_prop.
                ?cooling_capacity_prop brick:value ?cooling_capacity;
                    qudt:hasUnit ?cooling_capacity_unit .
                ?heating_capacity_prop brick:value ?heating_capacity;
                    qudt:hasUnit ?heating_capacity_unit .
                ?hvac brick:heatingCoefficientOfPerformance/brick:value ?heating_cop;
                    brick:coolingCoefficientOfPerformance/brick:value ?cooling_cop .
                }
            """,
            "s223": """
                SELECT DISTINCT ?zone ?hvac ?cooling_capacity ?cooling_capacity_unit ?heating_capacity ?heating_capacity_unit ?cooling_cop ?heating_cop   WHERE {
                <%s> hpfs:has-location ?zone .
                ?zone a s223:DomainSpace .
                ?hvac s223:connectsTo ?zone ;
                    s223:hasProperty ?c_cap_prop, ?h_cap_prop, ?c_cop_prop, ?h_cop_prop.
                ?c_cap_prop a hpfs:cooling-capacity ;
                    s223:hasValue ?cooling_capacity ;
                    qudt:hasUnit ?cooling_capacity_unit .
                ?h_cap_prop a hpfs:heating-capacity ;
                    s223:hasValue ?heating_capacity ;
                    qudt:hasUnit ?heating_capacity_unit .
                ?c_cop_prop a hpfs:cooling-COP ;
                    s223:hasValue ?cooling_cop .
                ?h_cop_prop a hpfs:heating-COP ;
                    s223:hasValue ?heating_cop .

            }"""
        },
        # Need to double check change to ask dual sp
        # <%s> (brick:isPartOf?|brick:feeds?|brick:hasLocation/brick:isFedBy)/brick:hasPoint ?hsp, ?csp . to ?p
        'ask-dual-sp':{'brick':"""
                ASK {
                <%s> (brick:isPartOf?|brick:feeds?|brick:hasLocation/brick:isFedBy?)/brick:hasPoint ?hsp, ?csp .
                ?hsp a brick:Heating_Temperature_Setpoint .
                ?csp a brick:Cooling_Temperature_Setpoint .
            }""",
                    's223':"""ASK {
                <%s> hpfs:has-location?/s223:hasProperty ?hsp, ?csp .
                ?hsp s223:hasAspect s223:Role-Heating, s223:Aspect-Setpoint .
                ?csp s223:hasAspect s223:Role-Cooling, s223:Aspect-Setpoint .
            }"""
       },
       "ask-single-sp":{'brick':"""
                ASK {
                <%s> (brick:isPartOf?|brick:feeds?|brick:hasLocation/brick:isFedBy)/brick:hasPoint ?sp, ?db .
                ?sp a brick:Temperature_Setpoint .
                ?db a brick:Temperature_Deadband_Setpoint . 
            }""",
            "s223":"""
                ASK {
                <%s> hpfs:has-location?/s223:hasProperty ?hsp, ?csp .
                ?hsp s223:hasAspect s223:Role-Heating, s223:Role-Cooling, s223:Aspect-Setpoint .
            }"""
        },
        # PREFIX needed for qudt for this query but no others for some reason
        "get-tstat-units":{"brick": """
                SELECT DISTINCT ?unit WHERE {
                <%s> brick:hasPoint ?resolution_point .
                ?resolution_point qudt:hasUnit ?unit ;
                    qudt:isDeltaQuantity true .
                }""",
                    "s223":"""
                PREFIX qudt: <http://qudt.org/schema/qudt/>
                SELECT DISTINCT ?unit WHERE {
                <%s> s223:hasProperty ?temp_prop .
                ?temp_prop qudt:hasQuantityKind quantitykind:Temperature ;
                    qudt:hasUnit ?unit .
                }""" },
        "ask-electric-heat":{"brick":"""
                ASK {
                <%s> brick:hasLocation ?zone .
                ?zone brick:isFedBy ?hvac .
                {
                     ?hvac a brick:VRF_System .
                } UNION {
                     ?hvac a brick:Packaged_Heat_Pump . 
                } 
            }""",
            "s223":f"""
                PREFIX qudt: <http://qudt.org/schema/qudt/>
                ASK {{
                <%s> hpfs:has-location/^s223:connectsTo ?unit .
                ?unit a/rdfs:subClassOf* s223:HeatPump .
            }}"""
        },
        "get_floor_area_data": {"brick": """
                SELECT ?zone (SUM(?areaValue) AS ?floor_area) (SAMPLE(?areaUnit) AS ?floor_area_unit)
                WHERE {
                <%s> brick:hasLocation ?zone .
                ?space a brick:Space ;
                        brick:isPartOf ?zone ;
                        brick:area ?area .
                ?area qudt:hasQuantityKind quantitykind:Area ;
                        qudt:hasUnit ?areaUnit ;
                        brick:value ?areaValue .
                }
                GROUP BY ?zone
                """,
            "s223": """
                SELECT ?zone (SUM(?areaValue) AS ?floor_area) (SAMPLE(?areaUnit) AS ?floor_area_unit)
                WHERE {
                <%s> hpfs:has-location ?zone .
                ?zone hpfs:has-space ?space .
                ?space s223:hasProperty ?area .
                ?area a hpfs:area; 
                    s223:hasValue ?areaValue ;
                    qudt:hasUnit ?areaUnit .
                }
                GROUP BY ?zone
                """
        },
        "get_window_data": {"brick": """
                SELECT ?window ?window_area_value ?window_area_unit ?window_tilt_value ?window_azimuth_value
                WHERE {
                <%s> brick:hasLocation ?zone .
                ?zone a brick:HVAC_Zone .
                ?window a brick:Window ;
                        brick:isPartOf ?zone ;
                        brick:area ?window_area ;
                        brick:tilt ?window_tilt ;
                        brick:azimuth ?window_azimuth .
                        
                ?window_area qudt:hasQuantityKind quantitykind:Area ;
                            qudt:hasUnit ?window_area_unit ;
                            brick:value ?window_area_value .
                        
                ?window_tilt qudt:hasQuantityKind quantitykind:Tilt ;
                            qudt:hasUnit unit:Degree ;
                            brick:value ?window_tilt_value .
                        
                ?window_azimuth qudt:hasQuantityKind quantitykind:Azimuth ;
                                qudt:hasUnit unit:Degree ;
                                brick:value ?window_azimuth_value .
                }
                ORDER BY DESC(?window_area_value)
                LIMIT 1
                """,
            "s223": """
                SELECT ?window ?window_area_value ?window_area_unit ?window_tilt_value ?window_azimuth_value
                WHERE {
                <%s> hpfs:has-location ?zone .
                ?zone hpfs:has-window ?window .
                ?window s223:hasProperty ?warea, ?tilt_prop, ?azimuth_prop .
                ?warea a hpfs:area ;
                    s223:hasValue ?window_area_value ;
                    qudt:hasUnit ?window_area_unit .
                ?tilt_prop a hpfs:tilt ;
                    s223:hasValue ?window_tilt_value ;
                    qudt:hasUnit unit:Degree .
                ?azimuth_prop a hpfs:azimuth ;
                    s223:hasValue ?window_azimuth_value ;
                    qudt:hasUnit unit:Degree .
                }
                ORDER BY DESC(?window_area_value)
                LIMIT 1
                """
        }
    
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
        if ontology == 's223':
            self.g.parse("https://open223.info/223p.ttl", format = 'ttl')

    def convert_model_to_si(self):
        """
        Convert all quantities in a Brick model to SI units
        
        Args:
            g: The RDF graph containing the Brick model
            
        Returns:
            Graph: The modified graph with SI units
        """        
        query = sparql_queries["convert_to_si"][self.ontology]
        
        for row_dict in self.g.query(query).bindings:
            # will throw error if not all things are present
            subject, value, unit = row_dict['s'], row_dict['v'], row_dict['u']
            isDelta = row_dict.get('isDelta', False)
        
            if unit in UNIT_CONVERSIONS:
                print('changing value of ', subject, 'from', unit, 'to', UNIT_CONVERSIONS[unit])
                new_unit = UNIT_CONVERSIONS[unit]
                new_value = convert_units(value, unit, new_unit, isDelta)

                if self.ontology == 'brick':
                    self.g.set((subject, BRICK.value, Literal(new_value)))
                    self.g.set((subject, QUDT.hasUnit, new_unit))
                else:
                    self.g.set((subject, S223.hasValue, Literal(new_value)))
                    self.g.set((subject, QUDT.hasUnit, new_unit))



    def _get_value(self, subject, predicate) -> Any:
        """Helper method to get a value from the RDF graph."""
        value = self.g.value(subject, predicate)
        return value.toPython() if value else None

    def get_site_info(self) -> Dict:
        """Fetch site-level metadata."""
        if self.ontology == 'brick':
            return{
            "tz": self._get_value(self.site, BRICK.timezone),
            "latitude": self._get_value(self.site, BRICK.latitude),
            "longitude": self._get_value(self.site, BRICK.longitude),
            "NOAAstation": self._get_value(self.site, BRICK.hasNOAAStation),
            # project_id and site_id are currently the same
            "project_id": next(self.g.triples((None,RDF.type, BRICK.Site)))[0],
            "site_id": next(self.g.triples((None,RDF.type, BRICK.Site)))[0],
        }
        else:
            results = self.g.query(sparql_queries["site_info"][self.ontology])
            return {str(k): v.toPython() for k, v in results.bindings[0].items()} 

    # May want to break this out into separate queries to make debugging a bit easier
    def get_thermostat_data(self, for_zone_list: Optional[List[str]] = None) -> Dict:
        # for_zone will just be ID, not URI. I assume this is better for how MPC is used
        # TODO: Add zone_filter and building_filter
        """Fetch thermostat metadata."""
        thermostat_data = {
            "heat_availability": [],
            "cool_availability": [],
            "heat_tolerance": [],
            "cool_tolerance": [],
            "setpoint_deadband": [],
            "active": [],
            "control_group": [],
            "control_type_list": [],
            "floor_area_list": [],
            "floor_area_unit": [],
            "window_area_list": [],
            "window_area_unit": [],
            "azimuth_list": [],
            "azimuth_unit": [],
            "tilt_list": [],
            "tilt_unit": [],
            "zone_ids": [],
            "hvacs": [],
            "setpoint_type": [],
            "fuel_heat_list": [],
            "fuel_cool_list": [],
            "cooling_capacity": [],
            "cooling_capacity_unit": [],
            "heating_capacity": [],
            "heating_capacity_unit": [],
            "cooling_cop": [],
            "heating_cop": [],
            "cooling_electricity": [],
            "heating_electricity": [],
            "resolution": [],
            "temperature_unit": [],
        }
        
        results = self.g.query(sparql_queries['get_tstats'][self.ontology])
        
        tstats_zones = [(r['tstat'], r['zone']) for r in results]
        
        # TODO: Add error messages for when zone is or isn't present
        for tstat, zone in tstats_zones:
        # Method for filtering depends on if URIs should be used elsewere, can just use id, and not namespace if that is more suitable
            if (for_zone_list is not None):
                if (self.g.compute_qname(zone)[-1] not in for_zone_list):
                    continue
            
        #     MPC configuration should be separate, but can determine defaults based on whether heat/cool are electric
        #     thermostat_data["heat_availability"].append(self._get_value(tstat, self.HPF.isHeatAvailable))
        #     thermostat_data["cool_availability"].append(self._get_value(tstat, self.HPF.isCoolAvailable))
        # TODO: check which of the returned data points should be URIs (may be none)
        # brick:resolution/brick:value ?resolution .
            ## brick:resolution/brick:value ?resolution .
            # Query thermostat-specific data
            results = self.g.query(sparql_queries['get_tstat_data'][self.ontology] % tstat)

            if len(results) != 1:
                raise Exception(f"Expected 1 result for each variable, got {len(results)}")

            result = results.bindings[0]
            thermostat_data["heat_tolerance"].append(-1.0 * result["tolerance_value"].toPython())
            thermostat_data["cool_tolerance"].append(1.0 * result["tolerance_value"].toPython())
            thermostat_data["setpoint_deadband"].append(result["deadband_value"].toPython())
            thermostat_data["active"].append(result["active_value"].toPython())
            thermostat_data["control_group"].append(result["control_group"].toPython())
            stage_count = result["stage_count"].toPython()
            thermostat_data["control_type_list"].append("binary" if stage_count == 1 else "stage")
            thermostat_data["resolution"].append(result["resolution"].toPython())

            # Query zone-specific data (HVAC capacity and COP)
            zone_results = self.g.query(sparql_queries['get_unit_data'][self.ontology] % tstat)

            if len(zone_results) != 1:
                raise Exception(f"Expected 1 result for each variable, got {len(zone_results)}")

            zone_result = zone_results.bindings[0]
            
            # Query floor area data (sum of all spaces in zone)
            floor_area_results = self.g.query(sparql_queries['get_floor_area_data'][self.ontology] % tstat)
            
            if len(floor_area_results) != 1:
                raise Exception(f"Expected 1 result for floor area, got {len(floor_area_results)}")
            
            floor_area_result = floor_area_results.bindings[0]
            
            # Convert floor area units
            floor_area_value = floor_area_result["floor_area"].toPython()
            floor_area_unit = floor_area_result["floor_area_unit"]
            if floor_area_unit in UNIT_CONVERSIONS:
                floor_area_value = convert_units(floor_area_value, floor_area_unit, UNIT_CONVERSIONS[floor_area_unit], False)
                floor_area_unit = UNIT_CONVERSIONS[floor_area_unit].toPython().split("/")[-1]
            else:
                floor_area_unit = floor_area_unit.toPython().split("/")[-1]
            
            # Query window data (largest window by area)
            window_results = self.g.query(sparql_queries['get_window_data'][self.ontology] % tstat)
            
            if len(window_results) != 1:
                raise Exception(f"Expected 1 result for window data, got {len(window_results)}")
            
            window_result = window_results.bindings[0]
            
            # Convert window area units
            window_area_value = window_result["window_area_value"].toPython()
            window_area_unit = window_result["window_area_unit"]
            if window_area_unit in UNIT_CONVERSIONS:
                window_area_value = convert_units(window_area_value, window_area_unit, UNIT_CONVERSIONS[window_area_unit], False)
                window_area_unit = UNIT_CONVERSIONS[window_area_unit].toPython().split("/")[-1]
            else:
                window_area_unit = window_area_unit.toPython().split("/")[-1]
            
            # Convert azimuth units
            azimuth_value = window_result["window_azimuth_value"].toPython()
            # Azimuth and tilt are already in degrees, no conversion needed
            azimuth_unit = "DEGREE"
            
            # Convert tilt units
            tilt_value = window_result["window_tilt_value"].toPython()
            # Azimuth and tilt are already in degrees, no conversion needed
            tilt_unit = "DEGREE"
            
            # Convert cooling capacity units
            cooling_capacity_value = zone_result["cooling_capacity"].toPython()
            cooling_capacity_unit = zone_result["cooling_capacity_unit"]
            if cooling_capacity_unit in UNIT_CONVERSIONS:
                cooling_capacity_value = convert_units(cooling_capacity_value, cooling_capacity_unit, UNIT_CONVERSIONS[cooling_capacity_unit], False)
                cooling_capacity_unit = UNIT_CONVERSIONS[cooling_capacity_unit].toPython().split("/")[-1]
            else:
                cooling_capacity_unit = cooling_capacity_unit.toPython().split("/")[-1]
            
            # Convert heating capacity units
            heating_capacity_value = zone_result["heating_capacity"].toPython()
            heating_capacity_unit = zone_result["heating_capacity_unit"]
            if heating_capacity_unit in UNIT_CONVERSIONS:
                heating_capacity_value = convert_units(heating_capacity_value, heating_capacity_unit, UNIT_CONVERSIONS[heating_capacity_unit], False)
                heating_capacity_unit = UNIT_CONVERSIONS[heating_capacity_unit].toPython().split("/")[-1]
            else:
                heating_capacity_unit = heating_capacity_unit.toPython().split("/")[-1]
            
            thermostat_data["floor_area_list"].append(floor_area_value)
            thermostat_data["floor_area_unit"].append(floor_area_unit.split("/")[-1])
            thermostat_data["window_area_list"].append(window_area_value)
            thermostat_data["window_area_unit"].append(window_area_unit.split("/")[-1])
            thermostat_data["azimuth_list"].append(azimuth_value)
            thermostat_data["azimuth_unit"].append(azimuth_unit.split("/")[-1])
            thermostat_data["tilt_list"].append(tilt_value)
            thermostat_data["tilt_unit"].append(tilt_unit.split("/")[-1])
            thermostat_data["zone_ids"].append(zone_result["zone"].toPython().split("#")[-1])
            thermostat_data["hvacs"].append(zone_result["hvac"].toPython().split("#")[-1])
            thermostat_data["cooling_capacity"].append(cooling_capacity_value)
            thermostat_data["cooling_capacity_unit"].append(cooling_capacity_unit)
            thermostat_data["heating_capacity"].append(heating_capacity_value)
            thermostat_data["heating_capacity_unit"].append(heating_capacity_unit)
            thermostat_data["cooling_cop"].append(zone_result["cooling_cop"].toPython())
            thermostat_data["heating_cop"].append(zone_result["heating_cop"].toPython())

            ## TODO: Add setpoint type
            # # Determine setpoint type
            # double_setpoint = self.g.query(sparql_queries["ask-dual-sp"][self.ontology] % tstat).askAnswer

            # single_setpoint = self.g.query(sparql_queries['ask-single-sp'][self.ontology] % tstat).askAnswer

            # if double_setpoint:
            #     thermostat_data["setpoint_type"].append("double")
            # elif single_setpoint:
            #     thermostat_data["setpoint_type"].append("single")
            # else:
            #     raise Exception(f"Setpoint configuration unrecognized for thermostat {tstat}")

            # Determine heating fuel type
            electric_heat = self.g.query(sparql_queries['ask-electric-heat'][self.ontology] % tstat).askAnswer

            thermostat_data["fuel_heat_list"].append("electricity" if electric_heat else "gas")
            thermostat_data["fuel_cool_list"].append("electricity")
            thermostat_data['heat_availability'].append(True if electric_heat else False)
            thermostat_data['cool_availability'].append(True)

            # determining temperature unit 
            unit_results = self.g.query(sparql_queries['get-tstat-units'][self.ontology] % tstat)
            if len(unit_results) > 1:
                raise Exception("Multiple unit results, expected 1 unit, got %d" % len(unit_results))
            tstat_unit = unit_results.bindings[0]['unit'].toPython().split('/')[-1]
            thermostat_data['temperature_unit'].append('IP' if tstat_unit == 'DEG_F' else 'SI')


        return thermostat_data

    def get_complete_output(self) -> Dict:
        """Combine site info and thermostat data into a final output dictionary."""
        site_info = self.get_site_info()
        thermostat_data = self.get_thermostat_data()

        return {**site_info, **thermostat_data}
    