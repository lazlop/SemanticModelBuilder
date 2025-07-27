"""
Tests for metadata processing functionality
"""

import json
import os
import tempfile

import pytest

from semantic_mpc_interface import BuildingMetadataLoader, Survey, SurveyReader


class TestSurvey:
    """Test cases for Survey."""

    def test_init_with_parameters(self):
        """Test initialization with parameters."""
        generator = Survey(
            site_id='test-site',
            building_id='test-building',
            hvac_type='hp-rtu'
        )
        assert generator.site_id == 'test-site'
        assert generator.building_id == 'test-building'
        assert generator.hvac_type == 'hp-rtu'

    def test_easy_config(self):
        """Test easy config generation."""
        generator = Survey(
            site_id='test-site',
            building_id='test-building',
            hvac_type='hp-rtu'
        )
        
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            generator.easy_config(
                zone_space_window_list=[(1, 1)],
                output_path=temp_dir
            )
            
            # Check that files were created
            expected_path = os.path.join(temp_dir, 'test-site')
            assert os.path.exists(expected_path)

    def test_generate_template(self):
        """Test custom template generation."""
        generator = Survey(
            site_id='test-site',
            building_id='test-building',
            hvac_type='vrf'
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            generator.generate_template(
                hvacs_feed_hvacs={'HP1': ['FCU1']},
                hvacs_feed_zones={'FCU1': ['Zone1']},
                zones_contain_spaces={'Zone1': ['Space1']},
                zones_contain_windows={'Zone1': ['Window1']},
                output_path=temp_dir
            )
            
            # Check that files were created
            expected_path = os.path.join(temp_dir, 'test-site')
            assert os.path.exists(expected_path)


class TestSurveyReader:
    """Test cases for SurveyReader."""

    def test_init_with_path(self):
        """Test initialization with survey path."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            survey_path = os.path.join(temp_dir, "test-survey")
            os.makedirs(survey_path)
            
            # Create a basic config file
            config = {"site_id": "test-site", "building_id": "test-building"}
            with open(os.path.join(survey_path, "config.json"), "w") as f:
                json.dump(config, f)
            
            # Create required site_info.csv file
            with open(os.path.join(survey_path, "site_info.csv"), "w") as f:
                f.write("site_id,timezone,latitude,longitude,noaa_station\n")
                f.write("test-site,America/New_York,40.7128,-74.0060,KJFK\n")
            
            reader = SurveyReader(survey_path)
            # Check that reader was created successfully
            assert reader is not None

    def test_create_model(self):
        """Test model creation from survey data."""
        # Create a temporary directory structure with sample data
        with tempfile.TemporaryDirectory() as temp_dir:
            survey_path = os.path.join(temp_dir, "test-survey")
            os.makedirs(survey_path)
            
            # Create required subdirectories
            os.makedirs(os.path.join(survey_path, "zones"))
            os.makedirs(os.path.join(survey_path, "spaces"))
            os.makedirs(os.path.join(survey_path, "windows"))
            os.makedirs(os.path.join(survey_path, "hvac"))
            
            # Create basic config
            config = {
                "site_id": "test-site",
                "building_id": "test-building",
                "hvac_type": "hp-rtu",
                "hvacs_feed_hvacs": {},
                "hvacs_feed_zones": {
                    "hvac1": [
                        "zone1"
                    ],
                },
                "zones_contain_spaces": {
                    "zone1": [
                        "space1",
                    ],
                },
                "zones_contain_windows": {
                    "zone1": [
                        "window1"
                    ],
                }
            }
            
            with open(os.path.join(survey_path, "config.json"), "w") as f:
                json.dump(config, f)
            
            # Create site info with all required fields
            site_info = {
                "site_id": "test-site",
                "timezone": "America/New_York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "noaa_station": "KJFK"
            }
            with open(os.path.join(survey_path, "site_info.csv"), "w") as f:
                f.write("site_id,timezone,latitude,longitude,noaa_station\n")
                f.write(f"{site_info['site_id']},{site_info['timezone']},{site_info['latitude']},{site_info['longitude']},{site_info['noaa_station']}\n")
            
            # Create zones.csv
            with open(os.path.join(survey_path, "zones", "zones.csv"), "w") as f:
                f.write("zone_id,tstat_id,stage_count,setpoint_deadband,tolerance,active,resolution,temperature_unit\n")
                f.write("zone1,tstat1,2,1.0,2.0,True,1.0,DEG_C\n")
            
            # Create minimal space and window files
            with open(os.path.join(survey_path, "spaces", "zone1_spaces.csv"), "w") as f:
                f.write("space_id,zone_id,area_value,area_unit\n")
                f.write("space1,zone1,100,M2\n")
            
            with open(os.path.join(survey_path, "windows", "zone1_windows.csv"), "w") as f:
                f.write("window_id,zone_id,area_value,area_unit,azimuth_value,tilt_value\n")
                f.write("window1,zone1,10,M2,180,30\n")
            
            # Create hvac_units.csv
            with open(os.path.join(survey_path, "hvac", "hvac_units.csv"), "w") as f:
                f.write("hvac_id,zone_id,cooling_capacity,heating_capacity,cooling_cop,heating_cop\n")
                f.write("hvac1,zone1,5000,4000,3.5,3.0\n")
            
            # Create point_list.csv
            with open(os.path.join(survey_path, "point_list.csv"), "w") as f:
                f.write("point_name,point_of,point_template,point_type,ref_name,ref_type,unit\n")
                f.write("temp1,zone1,temperature,Temperature_Sensor,temp1_ref,sensor,DEG_C\n")
            
            reader = SurveyReader(survey_path)
            
            # Test model creation
            output_file = os.path.join(temp_dir, "test-model.ttl")
            reader.create_model(output_file)
            
            # Check that model file was created
            assert os.path.exists(output_file)


class TestBuildingMetadataLoader:
    """Test cases for BuildingMetadataLoader."""

    @pytest.fixture
    def sample_model_file(self):
        """Create a sample TTL model file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            # Write a minimal Brick model
            f.write("""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

ex:test-site a brick:Site ;
    rdfs:label "Test Site" .

ex:zone1 a brick:HVAC_Zone ;
    brick:isPartOf ex:test-site .

ex:tstat1 a brick:Thermostat ;
    brick:controls ex:zone1 .
""")
            return f.name

    def test_init_with_model_file(self, sample_model_file):
        """Test initialization with model file."""
        try:
            loader = BuildingMetadataLoader(sample_model_file, ontology='brick')
            # Check that loader was created successfully
            assert loader is not None
            assert loader.ontology == 'brick'
        finally:
            os.unlink(sample_model_file)

    def test_get_site_info(self, sample_model_file):
        """Test extracting site information."""
        try:
            loader = BuildingMetadataLoader(sample_model_file, ontology='brick')
            site_info = loader.get_site_info()
            
            # Check that site_info is returned (structure may vary)
            assert isinstance(site_info, dict)
        finally:
            os.unlink(sample_model_file)

    def test_get_thermostat_data(self, sample_model_file):
        """Test extracting thermostat data."""
        try:
            loader = BuildingMetadataLoader(sample_model_file, ontology='brick')
            thermostat_data = loader.get_thermostat_data()
            
            # Check that thermostat_data is returned
            assert isinstance(thermostat_data, (dict, list))
        finally:
            os.unlink(sample_model_file)

    def test_get_thermostat_data_for_zone(self, sample_model_file):
        """Test extracting thermostat data for specific zone."""
        try:
            loader = BuildingMetadataLoader(sample_model_file, ontology='brick')
            thermostat_data = loader.get_thermostat_data(for_zone='zone1')
            
            # Check that zone-specific data is returned
            assert isinstance(thermostat_data, (dict, list))
        finally:
            os.unlink(sample_model_file)

    def test_get_complete_output(self, sample_model_file):
        """Test getting complete metadata output."""
        try:
            loader = BuildingMetadataLoader(sample_model_file, ontology='brick')
            complete_output = loader.get_complete_output()
            
            # Check that complete output is returned
            assert isinstance(complete_output, dict)
        finally:
            os.unlink(sample_model_file)

    def test_convert_model_to_si(self, sample_model_file):
        """Test converting model units to SI."""
        try:
            loader = BuildingMetadataLoader(sample_model_file, ontology='brick')
            loader.convert_model_to_si()
            
            # Test should complete without error
            assert True
        finally:
            os.unlink(sample_model_file)
