"""
Tests for metadata processing functionality
"""

import json
import os
import tempfile

import pytest

from semantic_mpc_interface import LoadModel, HPFlexSurvey, get_thermostat_data


class TestHPFlexSurveyBrick:
    """Test cases for HPFlexSurvey with Brick ontology."""

    def test_init_with_parameters_brick(self):
        """Test initialization with parameters for Brick ontology."""
        with tempfile.TemporaryDirectory() as temp_dir:
            survey = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                ontology='brick'
            )
            assert survey.site_id == 'test-site'
            assert survey.building_id == 'test-building'
            assert survey.ontology == 'brick'

    def test_easy_config_brick(self):
        """Test easy config generation for Brick ontology."""
        with tempfile.TemporaryDirectory() as temp_dir:
            survey = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                ontology='brick'
            )
            
            survey.easy_config(zone_space_window_list=[(2, 1), (1, 2)])
            
            # Check that files were created
            expected_path = os.path.join(temp_dir, 'test-site', 'test-building')
            assert os.path.exists(expected_path)
            
            # Check that config file was created
            config_file = os.path.join(expected_path, 'config.json')
            assert os.path.exists(config_file)
            
            # Check that CSV files were created
            csv_files = ['zone.csv', 'space.csv', 'window.csv', 'hvac.csv', 'tstat.csv', 'site.csv']
            for csv_file in csv_files:
                assert os.path.exists(os.path.join(expected_path, csv_file))

    def test_read_csv_and_create_model_brick(self):
        """Test reading CSV files and creating RDF model for Brick ontology."""
        with tempfile.TemporaryDirectory() as temp_dir:
            survey = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                ontology='brick'
            )
            
            # Create basic structure
            survey.easy_config(zone_space_window_list=[(1, 1)])
            
            # Fill in some basic data in the CSV files
            self._fill_basic_csv_data(survey, 'brick')
            
            # Read CSV and create model
            survey.read_csv()
            
            # Check that model file was created
            model_file = os.path.join(survey.base_dir, f'{survey.building_id}.ttl')
            assert os.path.exists(model_file)
            assert os.path.getsize(model_file) > 0

    def _fill_basic_csv_data(self, survey, ontology):
        """Helper method to fill CSV files with basic test data."""
        import pandas as pd
        
        # Fill site.csv
        site_df = pd.read_csv(os.path.join(survey.base_dir, 'site.csv'))
        site_df.loc[0, 'name'] = survey.site_id
        if 'latitude-name-value' in site_df.columns:
            site_df.loc[0, 'latitude-name-value'] = 40.7128
        if 'longitude-name-value' in site_df.columns:
            site_df.loc[0, 'longitude-name-value'] = -74.0060
        site_df.to_csv(os.path.join(survey.base_dir, 'site.csv'), index=False)
        
        # Fill zone.csv
        zone_df = pd.read_csv(os.path.join(survey.base_dir, 'zone.csv'))
        if not zone_df.empty:
            zone_df.loc[0, 'name'] = 'zone_1'
        zone_df.to_csv(os.path.join(survey.base_dir, 'zone.csv'), index=False)
        
        # Fill space.csv
        space_df = pd.read_csv(os.path.join(survey.base_dir, 'space.csv'))
        if not space_df.empty:
            space_df.loc[0, 'name'] = 'space_1_1'
            if 'area-name-value' in space_df.columns:
                space_df.loc[0, 'area-name-value'] = 100
        space_df.to_csv(os.path.join(survey.base_dir, 'space.csv'), index=False)
        
        # Fill window.csv
        window_df = pd.read_csv(os.path.join(survey.base_dir, 'window.csv'))
        if not window_df.empty:
            window_df.loc[0, 'name'] = 'window_1_1'
            if 'area-name-value' in window_df.columns:
                window_df.loc[0, 'area-name-value'] = 10
        window_df.to_csv(os.path.join(survey.base_dir, 'window.csv'), index=False)
        
        # Fill hvac.csv
        hvac_df = pd.read_csv(os.path.join(survey.base_dir, 'hvac.csv'))
        if not hvac_df.empty:
            hvac_df.loc[0, 'name'] = 'hvac_1'
        hvac_df.to_csv(os.path.join(survey.base_dir, 'hvac.csv'), index=False)
        
        # Fill tstat.csv
        tstat_df = pd.read_csv(os.path.join(survey.base_dir, 'tstat.csv'))
        if not tstat_df.empty:
            tstat_df.loc[0, 'name'] = 'tstat_zone_1'
        tstat_df.to_csv(os.path.join(survey.base_dir, 'tstat.csv'), index=False)


class TestHPFlexSurveyS223:
    """Test cases for HPFlexSurvey with S223 ontology."""

    def test_init_with_parameters_s223(self):
        """Test initialization with parameters for S223 ontology."""
        with tempfile.TemporaryDirectory() as temp_dir:
            survey = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                ontology='s223'
            )
            assert survey.site_id == 'test-site'
            assert survey.building_id == 'test-building'
            assert survey.ontology == 's223'

    def test_easy_config_s223(self):
        """Test easy config generation for S223 ontology."""
        with tempfile.TemporaryDirectory() as temp_dir:
            survey = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                ontology='s223'
            )
            
            survey.easy_config(zone_space_window_list=[(2, 1), (1, 2)])
            
            # Check that files were created
            expected_path = os.path.join(temp_dir, 'test-site', 'test-building')
            assert os.path.exists(expected_path)
            
            # Check that config file was created
            config_file = os.path.join(expected_path, 'config.json')
            assert os.path.exists(config_file)
            
            # Check that CSV files were created
            csv_files = ['zone.csv', 'space.csv', 'window.csv', 'hvac.csv', 'tstat.csv', 'site.csv']
            for csv_file in csv_files:
                assert os.path.exists(os.path.join(expected_path, csv_file))

    def test_read_csv_and_create_model_s223(self):
        """Test reading CSV files and creating RDF model for S223 ontology."""
        with tempfile.TemporaryDirectory() as temp_dir:
            survey = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                ontology='s223'
            )
            
            # Create basic structure
            survey.easy_config(zone_space_window_list=[(1, 1)])
            
            # Fill in some basic data in the CSV files
            self._fill_basic_csv_data(survey, 's223')
            
            # Read CSV and create model
            survey.read_csv()
            
            # Check that model file was created
            model_file = os.path.join(survey.base_dir, f'{survey.building_id}.ttl')
            assert os.path.exists(model_file)
            assert os.path.getsize(model_file) > 0

    def _fill_basic_csv_data(self, survey, ontology):
        """Helper method to fill CSV files with basic test data."""
        import pandas as pd
        
        # Fill site.csv
        site_df = pd.read_csv(os.path.join(survey.base_dir, 'site.csv'))
        site_df.loc[0, 'name'] = survey.site_id
        if 'latitude-name-value' in site_df.columns:
            site_df.loc[0, 'latitude-name-value'] = 40.7128
        if 'longitude-name-value' in site_df.columns:
            site_df.loc[0, 'longitude-name-value'] = -74.0060
        site_df.to_csv(os.path.join(survey.base_dir, 'site.csv'), index=False)
        
        # Fill zone.csv
        zone_df = pd.read_csv(os.path.join(survey.base_dir, 'zone.csv'))
        if not zone_df.empty:
            zone_df.loc[0, 'name'] = 'zone_1'
        zone_df.to_csv(os.path.join(survey.base_dir, 'zone.csv'), index=False)
        
        # Fill space.csv
        space_df = pd.read_csv(os.path.join(survey.base_dir, 'space.csv'))
        if not space_df.empty:
            space_df.loc[0, 'name'] = 'space_1_1'
            if 'area-name-value' in space_df.columns:
                space_df.loc[0, 'area-name-value'] = 100
        space_df.to_csv(os.path.join(survey.base_dir, 'space.csv'), index=False)
        
        # Fill window.csv
        window_df = pd.read_csv(os.path.join(survey.base_dir, 'window.csv'))
        if not window_df.empty:
            window_df.loc[0, 'name'] = 'window_1_1'
            if 'area-name-value' in window_df.columns:
                window_df.loc[0, 'area-name-value'] = 10
        window_df.to_csv(os.path.join(survey.base_dir, 'window.csv'), index=False)
        
        # Fill hvac.csv
        hvac_df = pd.read_csv(os.path.join(survey.base_dir, 'hvac.csv'))
        if not hvac_df.empty:
            hvac_df.loc[0, 'name'] = 'hvac_1'
        hvac_df.to_csv(os.path.join(survey.base_dir, 'hvac.csv'), index=False)
        
        # Fill tstat.csv
        tstat_df = pd.read_csv(os.path.join(survey.base_dir, 'tstat.csv'))
        if not tstat_df.empty:
            tstat_df.loc[0, 'name'] = 'tstat_zone_1'
        tstat_df.to_csv(os.path.join(survey.base_dir, 'tstat.csv'), index=False)


class TestHPFlexSurveyGeneral:
    """Test cases for HPFlexSurvey that don't depend on specific ontology."""

    def test_overwrite_protection(self):
        """Test that overwrite protection works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first survey
            survey1 = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir
            )
            
            # Try to create second survey without overwrite - should raise error
            with pytest.raises(FileExistsError):
                survey2 = HPFlexSurvey(
                    site_id='test-site',
                    building_id='test-building',
                    output_dir=temp_dir,
                    overwrite=False
                )

    def test_overwrite_allowed(self):
        """Test that overwrite works when enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first survey
            survey1 = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir
            )
            
            # Create second survey with overwrite - should work
            survey2 = HPFlexSurvey(
                site_id='test-site',
                building_id='test-building',
                output_dir=temp_dir,
                overwrite=True
            )
            assert survey2 is not None


class TestLoadModelBrick:
    """Test cases for LoadModel with Brick ontology."""

    @pytest.fixture
    def sample_brick_model_file(self):
        """Create a sample Brick TTL model file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write("""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix ex: <http://example.org/> .

ex:test-site a brick:Site ;
    rdfs:label "Test Site" .

ex:zone1 a brick:HVAC_Zone ;
    brick:isPartOf ex:test-site .

ex:tstat1 a brick:Thermostat ;
    brick:controls ex:zone1 ;
    brick:hasPoint ex:temp1 .

ex:temp1 a brick:Temperature_Sensor ;
    brick:hasQuantity ex:temp1_qty .

ex:temp1_qty a qudt:QuantityValue ;
    qudt:hasValue 22.5 ;
    qudt:hasUnit unit:DEG_C .

ex:space1 a brick:Space ;
    brick:isPartOf ex:zone1 ;
    brick:hasQuantity ex:space1_area .

ex:space1_area a qudt:QuantityValue ;
    qudt:hasValue 100.0 ;
    qudt:hasUnit unit:M2 .
""")
            return f.name

    def test_init_with_model_file_brick(self, sample_brick_model_file):
        """Test initialization with model file for Brick ontology."""
        try:
            loader = LoadModel(sample_brick_model_file, ontology="brick")
            assert loader is not None
            assert loader.ontology == "brick"
            assert loader.g is not None
        finally:
            os.unlink(sample_brick_model_file)

    def test_get_all_building_objects_brick(self, sample_brick_model_file):
        """Test extracting building objects for Brick ontology."""
        try:
            loader = LoadModel(sample_brick_model_file, ontology="brick")
            building_objects = loader.get_all_building_objects()
            
            assert isinstance(building_objects, dict)
            # Should have some objects (exact structure depends on templates)
            
        finally:
            os.unlink(sample_brick_model_file)

    def test_as_si_units_brick(self, sample_brick_model_file):
        """Test loading model with SI unit conversion for Brick ontology."""
        try:
            loader = LoadModel(sample_brick_model_file, ontology="brick", as_si_units=True)
            building_objects = loader.get_all_building_objects()
            
            assert isinstance(building_objects, dict)
            
        finally:
            os.unlink(sample_brick_model_file)

    def test_list_available_templates_brick(self, sample_brick_model_file):
        """Test listing available templates for Brick ontology."""
        try:
            loader = LoadModel(sample_brick_model_file, ontology="brick")
            templates = loader.list_available_templates()
            
            assert isinstance(templates, list)
            assert len(templates) > 0
            assert all(isinstance(template, str) for template in templates)
            
        finally:
            os.unlink(sample_brick_model_file)


class TestLoadModelS223:
    """Test cases for LoadModel with S223 ontology."""

    @pytest.fixture
    def sample_s223_model_file(self):
        """Create a sample S223 TTL model file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write("""
@prefix s223: <http://data.ashrae.org/standard223#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix ex: <http://example.org/> .

ex:test-site a s223:Site ;
    rdfs:label "Test Site" .

ex:zone1 a s223:Zone ;
    s223:cnx ex:test-site .

ex:space1 a s223:PhysicalSpace ;
    s223:cnx ex:zone1 ;
    s223:hasProperty ex:space1_area .

ex:space1_area a s223:QuantifiableProperty ;
    qudt:hasValue 100.0 ;
    qudt:hasUnit unit:M2 .
""")
            return f.name

    def test_init_with_model_file_s223(self, sample_s223_model_file):
        """Test initialization with model file for S223 ontology."""
        try:
            loader = LoadModel(sample_s223_model_file, ontology="s223")
            assert loader is not None
            assert loader.ontology == "s223"
            assert loader.g is not None
        finally:
            os.unlink(sample_s223_model_file)

    def test_get_all_building_objects_s223(self, sample_s223_model_file):
        """Test extracting building objects for S223 ontology."""
        try:
            loader = LoadModel(sample_s223_model_file, ontology="s223")
            building_objects = loader.get_all_building_objects()
            
            assert isinstance(building_objects, dict)
            # Should have some objects (exact structure depends on templates)
            
        finally:
            os.unlink(sample_s223_model_file)

    def test_as_si_units_s223(self, sample_s223_model_file):
        """Test loading model with SI unit conversion for S223 ontology."""
        try:
            loader = LoadModel(sample_s223_model_file, ontology="s223", as_si_units=True)
            building_objects = loader.get_all_building_objects()
            
            assert isinstance(building_objects, dict)
            
        finally:
            os.unlink(sample_s223_model_file)

    def test_list_available_templates_s223(self, sample_s223_model_file):
        """Test listing available templates for S223 ontology."""
        try:
            loader = LoadModel(sample_s223_model_file, ontology="s223")
            templates = loader.list_available_templates()
            
            assert isinstance(templates, list)
            assert len(templates) > 0
            assert all(isinstance(template, str) for template in templates)
            
        finally:
            os.unlink(sample_s223_model_file)




class TestGetThermostatData:
    """Test cases for get_thermostat_data function."""

    @pytest.fixture
    def sample_model_with_thermostats(self):
        """Create a sample model with thermostat data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write("""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix ex: <http://example.org/> .

ex:test-site a brick:Site ;
    rdfs:label "Test Site" .

ex:zone1 a brick:HVAC_Zone ;
    brick:isPartOf ex:test-site .

ex:tstat1 a brick:Thermostat ;
    brick:controls ex:zone1 ;
    brick:hasQuantity ex:tstat1_tolerance, ex:tstat1_deadband .

ex:tstat1_tolerance a qudt:QuantityValue ;
    qudt:hasValue 2.0 ;
    qudt:hasUnit unit:DEG_C .

ex:tstat1_deadband a qudt:QuantityValue ;
    qudt:hasValue 1.0 ;
    qudt:hasUnit unit:DEG_C .

ex:hvac1 a brick:Heat_Pump ;
    brick:feeds ex:zone1 ;
    brick:hasQuantity ex:hvac1_cooling_cap, ex:hvac1_heating_cap .

ex:hvac1_cooling_cap a qudt:QuantityValue ;
    qudt:hasValue 5000.0 ;
    qudt:hasUnit unit:BTU_IT-PER-HR .

ex:hvac1_heating_cap a qudt:QuantityValue ;
    qudt:hasValue 4000.0 ;
    qudt:hasUnit unit:BTU_IT-PER-HR .
""")
            return f.name

    def test_get_thermostat_data_basic(self, sample_model_with_thermostats):
        """Test basic thermostat data extraction."""
        try:
            loader = LoadModel(sample_model_with_thermostats, ontology="brick")
            thermostat_data = get_thermostat_data(loader)
            
            # Check that thermostat_data is returned as a dictionary
            assert isinstance(thermostat_data, dict)
            
            # Check that expected keys are present
            expected_keys = [
                "zone_ids", "heat_tolerance", "cool_tolerance", "setpoint_deadband",
                "active", "control_group", "control_type_list", "floor_area_list",
                "window_area_list", "hvacs", "cooling_capacity", "heating_capacity"
            ]
            
            for key in expected_keys:
                assert key in thermostat_data
                assert isinstance(thermostat_data[key], list)
                
        finally:
            os.unlink(sample_model_with_thermostats)

    def test_get_thermostat_data_filtered(self, sample_model_with_thermostats):
        """Test thermostat data extraction with zone filtering."""
        try:
            loader = LoadModel(sample_model_with_thermostats, ontology="brick")
            thermostat_data = get_thermostat_data(loader, for_zone_list=['zone1'])
            
            # Check that thermostat_data is returned
            assert isinstance(thermostat_data, dict)
            
            # Should have filtered results
            if thermostat_data["zone_ids"]:
                assert all(zone_id in ['zone1'] for zone_id in thermostat_data["zone_ids"])
                
        finally:
            os.unlink(sample_model_with_thermostats)

    def test_get_thermostat_data_empty_filter(self, sample_model_with_thermostats):
        """Test thermostat data extraction with empty zone filter."""
        try:
            loader = LoadModel(sample_model_with_thermostats, ontology="brick")
            thermostat_data = get_thermostat_data(loader, for_zone_list=['nonexistent_zone'])
            
            # Check that thermostat_data is returned but empty
            assert isinstance(thermostat_data, dict)
            
            # Should have empty results for non-existent zone
            assert len(thermostat_data["zone_ids"]) == 0
                
        finally:
            os.unlink(sample_model_with_thermostats)
