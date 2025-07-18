"""
Tests for SemanticModelBuilder
"""

import pytest
from unittest.mock import Mock, patch
from rdflib import Graph, Namespace

from semantic_mpc_interface import SemanticModelBuilder


class TestSemanticModelBuilder:
    """Test cases for SemanticModelBuilder."""
    
    @pytest.fixture
    def mock_templates(self):
        """Mock templates for testing."""
        mock_template = Mock()
        mock_template.inline_dependencies.return_value.evaluate.return_value = Graph()
        
        mock_library = Mock()
        mock_library.get_template_by_name.return_value = mock_template
        
        return mock_library
    
    @patch('semantic_mpc_interface.model_builder.Library.load')
    @patch('semantic_mpc_interface.model_builder.BuildingMOTIF')
    def test_init_brick(self, mock_buildingmotif, mock_library_load, mock_templates):
        """Test initialization with Brick ontology."""
        mock_library_load.return_value = mock_templates
        
        builder = SemanticModelBuilder(
            site_id="test_site",
            ontology="brick",
            system_of_units="SI"
        )
        
        assert builder.site_id == "test_site"
        assert builder.ontology == "brick"
        assert builder.system_of_units == "SI"
        assert builder.default_temperature_unit == "DEG_C"
        assert builder.default_area_unit == "M2"
    
    @patch('semantic_mpc_interface.model_builder.Library.load')
    @patch('semantic_mpc_interface.model_builder.BuildingMOTIF')
    def test_init_s223(self, mock_buildingmotif, mock_library_load, mock_templates):
        """Test initialization with S223 ontology."""
        mock_library_load.return_value = mock_templates
        
        builder = SemanticModelBuilder(
            site_id="test_site",
            ontology="s223",
            system_of_units="IP"
        )
        
        assert builder.ontology == "s223"
        assert builder.default_temperature_unit == "DEG_F"
        assert builder.default_area_unit == "FT2"
    
    def test_invalid_ontology(self):
        """Test initialization with invalid ontology."""
        with pytest.raises(ValueError, match="Invalid ontology"):
            SemanticModelBuilder(
                site_id="test_site",
                ontology="invalid"
            )
    
    def test_invalid_units(self):
        """Test initialization with invalid unit system."""
        with pytest.raises(ValueError, match="Invalid system of units"):
            SemanticModelBuilder(
                site_id="test_site",
                system_of_units="invalid"
            )
    
    @patch('semantic_mpc_interface.model_builder.Library.load')
    @patch('semantic_mpc_interface.model_builder.BuildingMOTIF')
    def test_add_site(self, mock_buildingmotif, mock_library_load, mock_templates):
        """Test adding site information."""
        mock_library_load.return_value = mock_templates
        
        builder = SemanticModelBuilder(site_id="test_site")
        
        builder.add_site(
            timezone="America/New_York",
            latitude=40.7128,
            longitude=-74.0060,
            noaa_station="NYC_CENTRAL_PARK"
        )
        
        # Verify template was called
        mock_templates.get_template_by_name.assert_called_with('site')
    
    @patch('semantic_mpc_interface.model_builder.Library.load')
    @patch('semantic_mpc_interface.model_builder.BuildingMOTIF')
    def test_add_zone(self, mock_buildingmotif, mock_library_load, mock_templates):
        """Test adding a zone."""
        mock_library_load.return_value = mock_templates
        
        builder = SemanticModelBuilder(site_id="test_site")
        builder.add_zone("zone_001")
        
        # Verify template was called
        mock_templates.get_template_by_name.assert_called_with('hvac-zone')
    
    @patch('semantic_mpc_interface.model_builder.Library.load')
    @patch('semantic_mpc_interface.model_builder.BuildingMOTIF')
    def test_add_space(self, mock_buildingmotif, mock_library_load, mock_templates):
        """Test adding a space."""
        mock_library_load.return_value = mock_templates
        
        builder = SemanticModelBuilder(site_id="test_site")
        builder.add_space(
            space_id="room_101",
            zone_id="zone_001",
            area_value=25.0
        )
        
        # Verify templates were called
        calls = mock_templates.get_template_by_name.call_args_list
        template_names = [call[0][0] for call in calls]
        assert 'space' in template_names
        assert 'has-space' in template_names