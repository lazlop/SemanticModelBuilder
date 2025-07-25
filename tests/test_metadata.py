"""
Tests for metadata processing functionality
"""

import json
import os
import tempfile

import pytest

from semantic_mpc_interface import MetadataProcessor, SurveyGenerator, SurveyReader


class TestSurveyGenerator:
    """Test cases for SurveyGenerator."""

    def test_generate_building_survey(self):
        """Test generating a building survey."""
        generator = SurveyGenerator()
        survey = generator.generate_building_survey()

        assert "survey_info" in survey
        assert "sections" in survey
        assert len(survey["sections"]) > 0

        # Check for expected sections
        section_ids = [section["id"] for section in survey["sections"]]
        assert "site_info" in section_ids
        assert "spaces" in section_ids
        assert "hvac" in section_ids
        assert "points" in section_ids

    def test_save_survey(self):
        """Test saving survey to file."""
        generator = SurveyGenerator()
        survey = generator.generate_building_survey()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filename = f.name

        try:
            generator.save_survey(survey, filename)

            # Verify file was created and contains valid JSON
            assert os.path.exists(filename)
            with open(filename, "r") as f:
                loaded_survey = json.load(f)

            assert loaded_survey == survey
        finally:
            os.unlink(filename)


class TestSurveyReader:
    """Test cases for SurveyReader."""

    @pytest.fixture
    def sample_survey(self):
        """Sample survey for testing."""
        return {
            "survey_info": {"title": "Test Survey", "version": "1.0"},
            "sections": [
                {
                    "id": "site_info",
                    "title": "Site Information",
                    "fields": [
                        {"id": "site_id", "type": "text", "required": True},
                        {"id": "timezone", "type": "select", "required": True},
                    ],
                }
            ],
        }

    @pytest.fixture
    def sample_responses(self):
        """Sample responses for testing."""
        return {
            "site_info": {"site_id": "test_building", "timezone": "America/New_York"}
        }

    def test_load_survey(self, sample_survey):
        """Test loading survey from file."""
        reader = SurveyReader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_survey, f)
            filename = f.name

        try:
            reader.load_survey(filename)
            assert reader.survey == sample_survey
        finally:
            os.unlink(filename)

    def test_read_responses(self, sample_responses):
        """Test reading responses from file."""
        reader = SurveyReader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_responses, f)
            filename = f.name

        try:
            responses = reader.read_responses(filename)
            assert responses == sample_responses
            assert reader.responses == sample_responses
        finally:
            os.unlink(filename)

    def test_validate_responses_valid(self, sample_survey, sample_responses):
        """Test validation with valid responses."""
        reader = SurveyReader()
        reader.survey = sample_survey
        reader.responses = sample_responses

        errors = reader.validate_responses()
        assert len(errors) == 0

    def test_validate_responses_missing_required(self, sample_survey):
        """Test validation with missing required field."""
        reader = SurveyReader()
        reader.survey = sample_survey
        reader.responses = {
            "site_info": {
                "site_id": "test_building"
                # Missing required timezone field
            }
        }

        errors = reader.validate_responses()
        assert len(errors) > 0
        assert any("timezone" in error for error in errors)


class TestMetadataProcessor:
    """Test cases for MetadataProcessor."""

    @pytest.fixture
    def sample_survey_responses(self):
        """Sample survey responses for testing."""
        return {
            "site_info": {
                "site_id": "test_building",
                "timezone": "America/New_York",
                "latitude": "40.7128",
                "longitude": "-74.0060",
                "noaa_station": "NYC_CENTRAL_PARK",
            },
            "spaces": [
                {
                    "space_id": "room_101",
                    "zone_id": "zone_001",
                    "area": "25.0",
                    "area_unit": "M2",
                },
                {
                    "space_id": "room_102",
                    "zone_id": "zone_001",
                    "area": "30.0",
                    "area_unit": "M2",
                },
            ],
        }

    def test_load_from_survey(self, sample_survey_responses):
        """Test loading metadata from survey responses."""
        processor = MetadataProcessor()
        processor.load_from_survey(sample_survey_responses)

        assert processor.data == sample_survey_responses

    def test_extract_site_info(self, sample_survey_responses):
        """Test extracting site information."""
        processor = MetadataProcessor()
        processor.load_from_survey(sample_survey_responses)

        site_info = processor.extract_site_info()

        assert site_info["site_id"] == "test_building"
        assert site_info["timezone"] == "America/New_York"
        assert site_info["latitude"] == 40.7128
        assert site_info["longitude"] == -74.0060
        assert site_info["noaa_station"] == "NYC_CENTRAL_PARK"

    def test_extract_spaces(self, sample_survey_responses):
        """Test extracting space information."""
        processor = MetadataProcessor()
        processor.load_from_survey(sample_survey_responses)

        spaces = processor.extract_spaces()

        assert len(spaces) == 2
        assert spaces[0]["space_id"] == "room_101"
        assert spaces[0]["zone_id"] == "zone_001"
        assert spaces[0]["area"] == 25.0
        assert spaces[0]["area_unit"] == "M2"
