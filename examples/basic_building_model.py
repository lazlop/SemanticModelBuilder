#!/usr/bin/env python3
"""
Basic Building Model Example

This example demonstrates how to create a simple building model using
the Semantic MPC Interface package.
"""

from semantic_mpc_interface import SemanticModelBuilder, PointManager

def main():
    """Create a basic building model."""
    
    # Create a model builder for Brick Schema
    builder = SemanticModelBuilder(
        site_id="example_building",
        ontology="brick",
        system_of_units="SI"
    )
    
    # Add site information
    builder.add_site(
        timezone="America/New_York",
        latitude=40.7128,
        longitude=-74.0060,
        noaa_station="NYC_CENTRAL_PARK"
    )
    
    # Add zones and spaces
    builder.add_zone("zone_001")
    builder.add_space(
        space_id="room_101",
        zone_id="zone_001", 
        area_value=25.0,  # m²
        unit="M2"
    )
    
    # Add HVAC equipment
    try:
        builder.add_hvac(
            hvac_id="rtu_001",
            feeds_ids=["zone_001"],
            cooling_capacity=12000,  # W
            heating_capacity=10000,  # W
            cooling_cop=3.5,
            heating_cop=2.8
        )
    except AttributeError:
        print("HVAC method not available in current builder")
    
    # Add thermostat
    try:
        builder.add_thermostat(
            tstat_id="tstat_001",
            zone_id="zone_001",
            stage_count=2,
            setpoint_deadband=1.0,  # °C
            tolerance=0.5,  # °C
            active=True,
            resolution=0.1  # °C
        )
    except AttributeError:
        print("Thermostat method not available in current builder")
    
    # Add points using PointManager
    point_manager = PointManager(builder)
    
    # Add temperature sensor
    point_manager.add_temperature_sensor(
        point_id="temp_sensor_001",
        point_of="room_101",
        ref_name="building/room_101/temperature",
        unit="DEG_C"
    )
    
    # Add temperature setpoints
    point_manager.add_temperature_setpoint(
        point_id="heating_setpoint_001",
        point_of="tstat_001",
        ref_name="building/tstat_001/heating_setpoint",
        setpoint_type="heating",
        occupancy="occupied",
        unit="DEG_C"
    )
    
    point_manager.add_temperature_setpoint(
        point_id="cooling_setpoint_001", 
        point_of="tstat_001",
        ref_name="building/tstat_001/cooling_setpoint",
        setpoint_type="cooling",
        occupancy="occupied",
        unit="DEG_C"
    )
    
    # Add occupancy sensor
    point_manager.add_occupancy_sensor(
        point_id="occ_sensor_001",
        point_of="room_101",
        ref_name="building/room_101/occupancy"
    )
    
    # List all points
    points = point_manager.list_points()
    print(f"Created {len(points)} points:")
    for point in points:
        print(f"  - {point['point_id']}: {point['point_type']}")
    
    # Save the model
    builder.save_model("example_building_model.ttl")
    print("Model saved to: example_building_model.ttl")


if __name__ == "__main__":
    main()