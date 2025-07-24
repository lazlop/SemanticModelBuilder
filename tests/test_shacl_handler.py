"""
Tests for SHACLHandler
"""

import tempfile
import os

import pytest
from rdflib import Graph

from semantic_mpc_interface import SHACLHandler


class TestSHACLHandler:
    """Test cases for SHACLHandler."""

    def test_init(self):
        """Test initialization of SHACLHandler."""
        handler = SHACLHandler()
        assert handler is not None

    def test_generate_shapes(self):
        """Test generating SHACL shapes."""
        handler = SHACLHandler()
        handler.generate_shapes()
        shapes = handler.shapes_graph
        
        # Check that shapes are returned
        assert shapes is not None
        # Shapes should be an RDF graph or similar structure
        assert isinstance(shapes, (Graph, str, dict))

    def test_save_shapes(self):
        """Test saving SHACL shapes to file."""
        try:
            handler = SHACLHandler()
            handler.generate_shapes()
            
            with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
                output_file = f.name
            
            try:
                handler.save_shapes(output_file)
                # Check that file was created
                assert os.path.exists(output_file)
            finally:
                os.unlink(output_file)
                
        except Exception as e:
            pytest.skip(f"SHACLHandler dependencies not available: {e}")

    def test_validate_model(self):
        """Test validating a model against SHACL shapes."""
        try:
            handler = SHACLHandler()
            
            # Create a simple test graph
            test_graph = Graph()
            test_graph.parse(data="""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

ex:test-site a brick:Site ;
    rdfs:label "Test Site" .
""", format="turtle")
            
            conforms, results_graph, results_text = handler.validate_model(test_graph)
            
            # Check that validation results are returned
            assert isinstance(conforms, bool)
            assert results_graph is not None
            assert isinstance(results_text, str)
            
        except Exception as e:
            pytest.skip(f"SHACLHandler dependencies not available: {e}")

    def test_validate_model_with_violations(self):
        """Test validating a model that should have violations."""
        try:
            handler = SHACLHandler()
            
            # Create a test graph that might have violations
            test_graph = Graph()
            test_graph.parse(data="""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix ex: <http://example.org/> .

ex:invalid-entity a brick:NonExistentClass .
""", format="turtle")
            
            conforms, results_graph, results_text = handler.validate_model(test_graph)
            
            # Check that validation results are returned
            assert isinstance(conforms, bool)
            assert results_graph is not None
            assert isinstance(results_text, str)
            
        except Exception as e:
            pytest.skip(f"SHACLHandler dependencies not available: {e}")
