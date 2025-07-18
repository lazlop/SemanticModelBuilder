"""
SHACL Validation

Functionality for validating semantic models against SHACL shapes.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyshacl import validate
from rdflib import Graph

logger = logging.getLogger(__name__)


class SHACLHandler:
    """Handle SHACL validation of semantic models."""

    def __init__(self, shapes_file: Optional[str] = None):
        """
        Initialize SHACL handler.

        Args:
            shapes_file: Path to SHACL shapes file
        """
        self.shapes_graph = None
        if shapes_file:
            self.load_shapes(shapes_file)

    def load_shapes(self, shapes_file: str) -> None:
        """
        Load SHACL shapes from file.

        Args:
            shapes_file: Path to SHACL shapes file
        """
        try:
            self.shapes_graph = Graph()
            self.shapes_graph.parse(shapes_file)
            logger.info(f"Loaded SHACL shapes from: {shapes_file}")
        except Exception as e:
            logger.error(f"Failed to load SHACL shapes: {e}")
            raise

    def validate_model(self, model_graph: Graph) -> Dict[str, Any]:
        """
        Validate a model graph against SHACL shapes.

        Args:
            model_graph: RDF graph to validate

        Returns:
            Dictionary containing validation results
        """
        if not self.shapes_graph:
            raise ValueError("No SHACL shapes loaded")

        try:
            conforms, results_graph, results_text = validate(
                data_graph=model_graph,
                shacl_graph=self.shapes_graph,
                inference="rdfs",
                abort_on_first=False,
                allow_infos=True,
                allow_warnings=True,
            )

            # Parse validation results
            violations = self._parse_validation_results(results_graph)

            return {
                "conforms": conforms,
                "total_violations": len(violations),
                "violations": violations,
                "results_text": results_text,
                "results_graph": results_graph,
            }

        except Exception as e:
            logger.error(f"SHACL validation failed: {e}")
            raise

    def _parse_validation_results(self, results_graph: Graph) -> List[Dict[str, Any]]:
        """
        Parse SHACL validation results into structured format.

        Args:
            results_graph: SHACL validation results graph

        Returns:
            List of violation dictionaries
        """
        violations = []

        # SHACL namespace
        SH = "http://www.w3.org/ns/shacl#"

        # Query for validation results
        query = f"""
        PREFIX sh: <{SH}>
        SELECT ?result ?focusNode ?resultPath ?value ?message ?severity
        WHERE {{
            ?result a sh:ValidationResult ;
                    sh:focusNode ?focusNode ;
                    sh:resultMessage ?message ;
                    sh:resultSeverity ?severity .
            OPTIONAL {{ ?result sh:resultPath ?resultPath }}
            OPTIONAL {{ ?result sh:value ?value }}
        }}
        """

        for row in results_graph.query(query):
            violation = {
                "focus_node": str(row.focusNode) if row.focusNode else None,
                "result_path": str(row.resultPath) if row.resultPath else None,
                "value": str(row.value) if row.value else None,
                "message": str(row.message) if row.message else None,
                "severity": str(row.severity).split("#")[-1] if row.severity else None,
            }
            violations.append(violation)

        return violations

    def generate_validation_report(
        self, model_graph: Graph, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive validation report.

        Args:
            model_graph: RDF graph to validate
            output_file: Optional file to save report

        Returns:
            Validation report dictionary
        """
        validation_results = self.validate_model(model_graph)

        # Generate summary statistics
        violations_by_severity = {}
        for violation in validation_results["violations"]:
            severity = violation.get("severity", "Unknown")
            violations_by_severity[severity] = (
                violations_by_severity.get(severity, 0) + 1
            )

        report = {
            "summary": {
                "conforms": validation_results["conforms"],
                "total_violations": validation_results["total_violations"],
                "violations_by_severity": violations_by_severity,
            },
            "violations": validation_results["violations"],
            "raw_results": validation_results["results_text"],
        }

        if output_file:
            self._save_report(report, output_file)

        return report

    def _save_report(self, report: Dict[str, Any], filename: str) -> None:
        """
        Save validation report to file.

        Args:
            report: Validation report dictionary
            filename: Output filename
        """
        import json

        # Create a JSON-serializable version of the report
        json_report = {
            "summary": report["summary"],
            "violations": report["violations"],
            "raw_results": report["raw_results"],
        }

        with open(filename, "w") as f:
            json.dump(json_report, f, indent=2)

        logger.info(f"Validation report saved to: {filename}")

    def create_shapes_from_template(self, ontology: str = "brick") -> Graph:
        """
        Create basic SHACL shapes for an ontology.

        Args:
            ontology: Ontology type ('brick' or 's223')

        Returns:
            Graph containing SHACL shapes
        """
        shapes_graph = Graph()

        # Add basic namespace bindings
        shapes_graph.bind("sh", "http://www.w3.org/ns/shacl#")
        shapes_graph.bind("ex", "http://example.org/shapes#")

        if ontology == "brick":
            shapes_graph.bind("brick", "https://brickschema.org/schema/Brick#")
            self._add_brick_shapes(shapes_graph)
        elif ontology == "s223":
            shapes_graph.bind("s223", "http://data.ashrae.org/standard223#")
            self._add_s223_shapes(shapes_graph)

        return shapes_graph

    def _add_brick_shapes(self, shapes_graph: Graph) -> None:
        """Add basic Brick Schema SHACL shapes."""
        # This would add specific SHACL shapes for Brick Schema validation
        # For now, just add a placeholder
        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix brick: <https://brickschema.org/schema/Brick#> .
        @prefix ex: <http://example.org/shapes#> .
        
        ex:SiteShape a sh:NodeShape ;
            sh:targetClass brick:Site ;
            sh:property [
                sh:path brick:hasLocation ;
                sh:minCount 0 ;
            ] .
        """
        shapes_graph.parse(data=shapes_ttl, format="turtle")

    def _add_s223_shapes(self, shapes_graph: Graph) -> None:
        """Add basic S223 SHACL shapes."""
        # This would add specific SHACL shapes for S223 validation
        # For now, just add a placeholder
        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix s223: <http://data.ashrae.org/standard223#> .
        @prefix ex: <http://example.org/shapes#> .
        
        ex:PhysicalSpaceShape a sh:NodeShape ;
            sh:targetClass s223:PhysicalSpace ;
            sh:property [
                sh:path s223:hasProperty ;
                sh:minCount 0 ;
            ] .
        """
        shapes_graph.parse(data=shapes_ttl, format="turtle")
