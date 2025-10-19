#!/usr/bin/env python3
"""
Survey Workflow Example

This example demonstrates how to generate, fill out, and process
building metadata surveys.
"""

from semantic_mpc_interface import Survey, SurveyReader, MetadataProcessor, SemanticModelBuilder
import json

def main():
    """Demonstrate survey workflow."""
    
    # Step 1: Generate a survey
    print("Step 1: Generating survey...")
    generator = Survey()
    survey = generator.generate_building_survey()
    generator.save_survey(survey, "building_survey.json")
    print("Survey saved to: building_survey.json")
    
    # Step 2: Create mock survey responses
    print("\nStep 2: Creating mock survey responses...")
    responses = {
        "site_info": {
            "site_id": "demo_building",
            "timezone": "America/Chicago",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "noaa_station": "CHICAGO_OHARE"
        },
        "spaces": [
            {
                "space_id": "office_101",
                "zone_id": "zone_north",
                "area": 30.0,
                "area_unit": "M2"
            },
            {
                "space_id": "office_102", 
                "zone_id": "zone_north",
                "area": 25.0,
                "area_unit": "M2"
            },
            {
                "space_id": "conference_room",
                "zone_id": "zone_south", 
                "area": 50.0,
                "area_unit": "M2"
            }
        ],
        "hvac": [
            {
                "equipment_id": "rtu_north",
                "equipment_type": "hp-rtu",
                "serves_zones": "zone_north"
            },
            {
                "equipment_id": "rtu_south",
                "equipment_type": "hp-rtu", 
                "serves_zones": "zone_south"
            }
        ],
        "points": [
            {
                "point_id": "temp_office_101",
                "point_type": "Temperature_Sensor",
                "equipment_id": "office_101"
            },
            {
                "point_id": "temp_office_102",
                "point_type": "Temperature_Sensor", 
                "equipment_id": "office_102"
            },
            {
                "point_id": "occ_conference",
                "point_type": "Occupancy_Sensor",
                "equipment_id": "conference_room"
            }
        ]
    }
    
    # Save mock responses
    with open("survey_responses.json", "w") as f:
        json.dump(responses, f, indent=2)
    print("Mock responses saved to: survey_responses.json")
    
    # Step 3: Read and validate responses
    print("\nStep 3: Reading and validating responses...")
    reader = SurveyReader("building_survey.json")
    reader.read_responses("survey_responses.json")
    
    errors = reader.validate_responses()
    if errors:
        print("Validation errors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Survey responses are valid!")
    
    # Step 4: Process metadata
    print("\nStep 4: Processing metadata...")
    processor = MetadataProcessor()
    processor.load_from_survey(responses)
    
    site_info = processor.extract_site_info()
    spaces = processor.extract_spaces()
    hvac_equipment = processor.extract_hvac_equipment()
    
    print(f"Site: {site_info['site_id']}")
    print(f"Spaces: {len(spaces)}")
    print(f"HVAC Equipment: {len(hvac_equipment)}")
    
    # Step 5: Create semantic model from survey data
    print("\nStep 5: Creating semantic model from survey data...")
    builder = SemanticModelBuilder(
        site_id=site_info["site_id"],
        ontology="brick",
        system_of_units="SI"
    )
    
    # Add site
    builder.add_site(
        timezone=site_info["timezone"],
        latitude=site_info["latitude"],
        longitude=site_info["longitude"],
        noaa_station=site_info["noaa_station"]
    )
    
    # Add zones (extract unique zones from spaces)
    zones = set(space["zone_id"] for space in spaces)
    for zone_id in zones:
        builder.add_zone(zone_id)
    
    # Add spaces
    for space in spaces:
        builder.add_space(
            space_id=space["space_id"],
            zone_id=space["zone_id"],
            area_value=space["area"],
            unit=space["area_unit"]
        )
    
    # Save the model
    builder.save_model("survey_generated_model.ttl")
    print("Model saved to: survey_generated_model.ttl")
    
    print("\nSurvey workflow completed successfully!")


if __name__ == "__main__":
    main()