"""
Tests for SHACLHandler
"""

import tempfile
import os

import pytest
from rdflib import Graph

from semantic_mpc_interface import SHACLHandler


class TestSHACLHandlerBrick:
    """Test cases for SHACLHandler with Brick ontology."""

    def test_init_brick(self):
        """Test initialization of SHACLHandler with Brick ontology."""
        handler = SHACLHandler(ontology="brick")
        assert handler is not None
        assert handler.ontology == "brick"

    def test_generate_shapes_brick(self):
        """Test generating SHACL shapes for Brick ontology."""
        handler = SHACLHandler(ontology="brick")
        handler.generate_shapes()
        shapes = handler.shapes_graph
        
        # Check that shapes are returned
        assert shapes is not None
        assert isinstance(shapes, Graph)
        assert len(shapes) > 0  # Should have generated some triples

    def test_save_shapes_brick(self):
        """Test saving SHACL shapes to file for Brick ontology."""
        handler = SHACLHandler(ontology="brick")
        handler.generate_shapes()
        
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            output_file = f.name
        
        try:
            handler.save_shapes(output_file)
            # Check that file was created and has content
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
        finally:
            os.unlink(output_file)

    def test_validate_model_brick(self):
        """Test validating a Brick model against SHACL shapes."""
        handler = SHACLHandler(ontology="brick")
        handler.generate_shapes()
        
        # Create a simple test graph
        test_graph = Graph()
        test_graph.parse(data="""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

ex:test-site a brick:Site ;
    rdfs:label "Test Site" .

ex:zone1 a brick:HVAC_Zone ;
    brick:isPartOf ex:test-site .

ex:tstat1 a brick:Thermostat ;
    brick:controls ex:zone1 .
""", format="turtle")
        
        conforms, results_graph, results_text = handler.validate_model(test_graph)
        
        # Check that validation results are returned
        assert isinstance(conforms, bool)
        assert results_graph is not None
        assert isinstance(results_text, str)

    def test_validate_model_with_violations_brick(self):
        """Test validating a Brick model that should have violations."""
        handler = SHACLHandler(ontology="brick")
        handler.generate_shapes()
        
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

    def test_validate_model_with_custom_shapes_brick(self):
        """Test validation with custom shapes graph for Brick ontology."""
        handler = SHACLHandler(ontology="brick")
        
        # Create custom shapes
        custom_shapes = Graph()
        custom_shapes.parse(data="""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .

ex:TestShape a sh:NodeShape ;
    sh:targetClass ex:TestClass ;
    sh:property [
        sh:path ex:testProperty ;
        sh:minCount 1 ;
    ] .
""", format="turtle")
        
        # Test data
        test_graph = Graph()
        test_graph.parse(data="""
@prefix ex: <http://example.org/> .

ex:testInstance a ex:TestClass ;
    ex:testProperty "test value" .
""", format="turtle")
        
        conforms, results_graph, results_text = handler.validate_model(
            test_graph, shapes_graph=custom_shapes
        )
        
        assert isinstance(conforms, bool)
        assert results_graph is not None
        assert isinstance(results_text, str)


class TestSHACLHandlerS223:
    """Test cases for SHACLHandler with S223 ontology."""

    def test_init_s223(self):
        """Test initialization of SHACLHandler with S223 ontology."""
        handler = SHACLHandler(ontology="s223")
        assert handler is not None
        assert handler.ontology == "s223"

    def test_generate_shapes_s223(self):
        """Test generating SHACL shapes for S223 ontology."""
        handler = SHACLHandler(ontology="s223")
        handler.generate_shapes()
        shapes = handler.shapes_graph
        
        # Check that shapes are returned
        assert shapes is not None
        assert isinstance(shapes, Graph)
        assert len(shapes) > 0  # Should have generated some triples

    def test_save_shapes_s223(self):
        """Test saving SHACL shapes to file for S223 ontology."""
        handler = SHACLHandler(ontology="s223")
        handler.generate_shapes()
        
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            output_file = f.name
        
        try:
            handler.save_shapes(output_file)
            # Check that file was created and has content
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
        finally:
            os.unlink(output_file)

    def test_validate_model_s223(self):
        """Test validating an S223 model against SHACL shapes."""
        handler = SHACLHandler(ontology="s223")
        handler.generate_shapes()
        
        # Create a simple test graph
        test_graph = Graph()
        test_graph.parse(data="""
@prefix s223: <http://data.ashrae.org/standard223#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

ex:test-site a s223:Site ;
    rdfs:label "Test Site" .

ex:zone1 a s223:Zone ;
    s223:cnx ex:test-site .
""", format="turtle")
        
        conforms, results_graph, results_text = handler.validate_model(test_graph)
        
        # Check that validation results are returned
        assert isinstance(conforms, bool)
        assert results_graph is not None
        assert isinstance(results_text, str)

    def test_validate_model_with_violations_s223(self):
        """Test validating an S223 model that should have violations."""
        handler = SHACLHandler(ontology="s223")
        handler.generate_shapes()
        
        # Create a test graph that might have violations
        test_graph = Graph()
        test_graph.parse(data="""
@prefix s223: <http://data.ashrae.org/standard223#> .
@prefix ex: <http://example.org/> .

ex:invalid-entity a s223:NonExistentClass .
""", format="turtle")
        
        conforms, results_graph, results_text = handler.validate_model(test_graph)
        
        # Check that validation results are returned
        assert isinstance(conforms, bool)
        assert results_graph is not None
        assert isinstance(results_text, str)

    def test_validate_model_with_custom_shapes_s223(self):
        """Test validation with custom shapes graph for S223 ontology."""
        handler = SHACLHandler(ontology="s223")
        
        # Create custom shapes
        custom_shapes = Graph()
        custom_shapes.parse(data="""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .

ex:TestShape a sh:NodeShape ;
    sh:targetClass ex:TestClass ;
    sh:property [
        sh:path ex:testProperty ;
        sh:minCount 1 ;
    ] .
""", format="turtle")
        
        # Test data
        test_graph = Graph()
        test_graph.parse(data="""
@prefix ex: <http://example.org/> .

ex:testInstance a ex:TestClass ;
    ex:testProperty "test value" .
""", format="turtle")
        
        conforms, results_graph, results_text = handler.validate_model(
            test_graph, shapes_graph=custom_shapes
        )
        
        assert isinstance(conforms, bool)
        assert results_graph is not None
        assert isinstance(results_text, str)


class TestSHACLHandlerGeneral:
    """Test cases for SHACLHandler that don't depend on specific ontology."""

    def test_init_invalid_ontology(self):
        """Test initialization with invalid ontology raises error."""
        with pytest.raises(ValueError, match="Invalid ontology"):
            SHACLHandler(ontology="invalid")

    def test_save_shapes_without_generation(self):
        """Test that saving shapes without generation raises error."""
        handler = SHACLHandler()
        # Don't generate shapes
        
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            output_file = f.name
        
        try:
            with pytest.raises(ValueError, match="No shapes graph available"):
                handler.save_shapes(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_validate_model_without_shapes(self):
        """Test that validation without shapes raises error."""
        handler = SHACLHandler()
        # Don't generate shapes
        
        test_graph = Graph()
        test_graph.parse(data="""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix ex: <http://example.org/> .

ex:test a brick:Site .
""", format="turtle")
        
        with pytest.raises(ValueError, match="No shapes graph available"):
            handler.validate_model(test_graph)
