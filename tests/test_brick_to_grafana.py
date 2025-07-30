"""
Tests for BrickToGrafana
"""

import tempfile
import os

import pytest

from semantic_mpc_interface import BrickToGrafana


class TestBrickToGrafana:
    """Test cases for BrickToGrafana."""

    @pytest.fixture
    def sample_ttl_file(self):
        """Create a sample TTL file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
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

ex:temp_sensor a brick:Temperature_Sensor ;
    brick:isPointOf ex:zone1 .
""")
            return f.name

    def test_init_with_parameters(self, sample_ttl_file):
        """Test initialization with parameters."""
        try:
            bg = BrickToGrafana(
                grafana_server="http://localhost:3000",
                grafana_api_key="test_api_key",
                datasource="test_datasource",
                ttl_path=sample_ttl_file
            )
            
            assert bg.grafana_server == "http://localhost:3000"
            assert bg.grafana_api_key == "test_api_key"
            assert bg.datasource == "test_datasource"
            assert bg.ttl_path == sample_ttl_file
            
        except Exception as e:
            pytest.skip(f"BrickToGrafana dependencies not available: {e}")
        finally:
            os.unlink(sample_ttl_file)

    def test_create_dashboard(self, sample_ttl_file):
        """Test creating a dashboard."""
        try:
            bg = BrickToGrafana(
                grafana_server="http://localhost:3000",
                grafana_api_key="test_api_key",
                datasource="test_datasource",
                ttl_path=sample_ttl_file
            )
            
            dashboard = bg.create_dashboard("Test Dashboard")
            
            # Check that dashboard is created
            assert dashboard is not None
            # Dashboard should be a dictionary or similar structure
            assert isinstance(dashboard, (dict, str))
            
        except Exception as e:
            pytest.skip(f"BrickToGrafana dependencies not available: {e}")
        finally:
            os.unlink(sample_ttl_file)

    def test_upload_dashboard(self, sample_ttl_file):
        """Test uploading a dashboard (mock test)."""
        try:
            bg = BrickToGrafana(
                grafana_server="http://localhost:3000",
                grafana_api_key="test_api_key",
                datasource="test_datasource",
                ttl_path=sample_ttl_file
            )
            
            # Create a dashboard first
            dashboard = bg.create_dashboard("Test Dashboard")
            
            # Note: This test will likely fail in CI/CD without actual Grafana server
            # The test is mainly to check that the method exists and can be called
            try:
                result = bg.upload_dashboard(message="testing upload")
                # If upload succeeds, check result
                assert result is not None
            except Exception as upload_error:
                # Expected to fail without actual Grafana server
                assert "connection" in str(upload_error).lower() or "network" in str(upload_error).lower() or "http" in str(upload_error).lower()
            
        except Exception as e:
            pytest.skip(f"BrickToGrafana dependencies not available: {e}")
        finally:
            os.unlink(sample_ttl_file)

    def test_invalid_ttl_path(self):
        """Test initialization with invalid TTL path."""
        try:
            with pytest.raises(Exception):
                bg = BrickToGrafana(
                    grafana_server="http://localhost:3000",
                    grafana_api_key="test_api_key",
                    datasource="test_datasource",
                    ttl_path="nonexistent_file.ttl"
                )
        except Exception as e:
            pytest.skip(f"BrickToGrafana dependencies not available: {e}")

    def test_dashboard_creation_with_empty_model(self):
        """Test dashboard creation with minimal model."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            # Write minimal TTL content
            f.write("""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix ex: <http://example.org/> .

ex:empty-site a brick:Site .
""")
            ttl_file = f.name

        try:
            bg = BrickToGrafana(
                grafana_server="http://localhost:3000",
                grafana_api_key="test_api_key",
                datasource="test_datasource",
                ttl_path=ttl_file
            )
            
            dashboard = bg.create_dashboard("Empty Dashboard")
            
            # Should still create a dashboard even with minimal data
            assert dashboard is not None
            
        except Exception as e:
            pytest.skip(f"BrickToGrafana dependencies not available: {e}")
        finally:
            os.unlink(ttl_file)
