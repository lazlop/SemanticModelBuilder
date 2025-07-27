# Semantic MPC Interface

A Python package for creating and managing semantic building models using Brick Schema and ASHRAE Standard 223P ontologies.

## Overview

The Semantic MPC Interface provides a unified API for working with semantic building models, enabling:

- **Model Creation**: Build semantic models using Brick Schema or ASHRAE Standard 223P
- **Data Integration**: Import building metadata from various sources
- **Validation**: Validate models against SHACL shapes
- **Visualization**: Generate Grafana dashboards from semantic models
- **Unit Conversion**: Handle different unit systems (SI/IP)

## Features

- 🏢 **Multi-Ontology Support**: Works with both Brick Schema and ASHRAE Standard 223P
- 📊 **Grafana Integration**: Automatically generate monitoring dashboards
- ✅ **SHACL Validation**: Ensure model correctness and completeness
- 🔄 **Unit Conversion**: Seamless conversion between SI and Imperial units
- 📋 **Survey Tools**: Generate and process building metadata surveys
- 🎯 **Point Management**: Add and manage sensor/actuator points
- 🔧 **Template System**: Extensible template system for common building components

## Installation

### Basic Installation

Eventually when this is pip installable 
```bash
pip install semantic-mpc-interface
```
For now 
```
uv pip install git+https://github.com/lazlop/SemanticModelBuilder.git
```
```
To install the dev branch using uv
uv pip install git+https://github.com/lazlop/SemanticModelBuilder.git@develop
```
### With Optional Dependencies

```bash
# For Grafana integration
pip install semantic-mpc-interface[grafana]

# For development
pip install semantic-mpc-interface[dev]

# For Jupyter notebook support
pip install semantic-mpc-interface[jupyter]

# Install all optional dependencies
pip install semantic-mpc-interface[grafana,dev,jupyter]
```

### Development Installation

```bash
git clone https://github.com/yourusername/semantic-mpc-interface.git
cd semantic-mpc-interface
pip install -e .[dev]
```

## Quick Start

### Creating a Basic Building Model

```python
from semantic_mpc_interface import SemanticModelBuilder

# Create a model builder
builder = SemanticModelBuilder(
    site_id="building_001",
    ontology="brick",  # or "s223"
    system_of_units="SI"
)

# Add site information
builder.add_site(
    timezone="America/New_York",
    latitude=40.7128,
    longitude=-74.0060,
    noaa_station="NYC_CENTRAL_PARK"
)

# Add a zone
builder.add_zone("zone_001")

# Add a space
builder.add_space(
    space_id="room_101",
    zone_id="zone_001",
    area_value=25.0,  # m²
    unit="M2"
)

# Save the model
builder.save_model("building_model.ttl")
```

### Working with Metadata Surveys

```python
from semantic_mpc_interface import Survey, SurveyReader

# Generate a survey
generator = Survey()
survey = generator.generate_building_survey()
generator.save_survey(survey, "building_survey.json")

# Read survey responses
reader = SurveyReader()
responses = reader.read_responses("survey_responses.json")
errors = reader.validate_responses()

if not errors:
    print("Survey responses are valid!")
```

### Validating Models

```python
from semantic_mpc_interface import SHACLHandler
from rdflib import Graph

# Load your model
model = Graph()
model.parse("building_model.ttl")

# Validate against SHACL shapes
validator = SHACLHandler("shapes.ttl")
report = validator.generate_validation_report(model)

print(f"Model conforms: {report['conforms']}")
print(f"Violations found: {report['total_violations']}")
```

### Generating Grafana Dashboards

```python
from semantic_mpc_interface import BrickToGrafana

# Create dashboard from model
grafana = BrickToGrafana(model_graph=model)
dashboard = grafana.generate_dashboard(
    title="Building Monitoring Dashboard"
)

# Save dashboard configuration
grafana.save_dashboard(dashboard, "dashboard.json")
```

## Project Structure

```
semantic-mpc-interface/
├── src/semantic_mpc_interface/
│   ├── __init__.py              # Main package interface
│   ├── model_builder.py         # Core model building functionality
│   ├── namespaces.py           # RDF namespace definitions
│   ├── metadata.py             # Metadata handling
│   ├── points.py               # Point management
│   ├── conversion.py           # Unit conversion utilities
│   ├── grafana.py              # Grafana integration
│   ├── validation.py           # SHACL validation
│   ├── utils.py                # Utility functions
│   ├── templates/              # Template files
│   │   ├── brick-templates/    # Brick Schema templates
│   │   └── s223-templates/     # ASHRAE 223P templates
│   ├── schemas/                # SHACL shapes
│   └── data/                   # Static data files
├── tests/                      # Test suite
├── docs/                       # Documentation
├── examples/                   # Example scripts
└── tutorial/                   # Tutorial notebooks
```

## Documentation

- [API Reference](https://semantic-mpc-interface.readthedocs.io/api/)
- [User Guide](https://semantic-mpc-interface.readthedocs.io/guide/)
- [Examples](./examples/)
- [Tutorial Notebooks](./tutorial/)

## Supported Ontologies

### Brick Schema
- Full support for Brick Schema v1.3+
- Equipment, spaces, points, and relationships
- Inverse relationship inference

### ASHRAE Standard 223P
- Support for 223P ontology patterns
- Equipment and connection modeling
- Property and aspect modeling

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Clone the repository
2. Install development dependencies: `pip install -e .[dev]`
3. Run tests: `pytest`
4. Format code: `black src/ tests/`
5. Check types: `mypy src/`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this package in your research, please cite:

```bibtex
@software{semantic_mpc_interface,
  title={Semantic MPC Interface: A Python Package for Semantic Building Models},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/semantic-mpc-interface}
}
```

## Acknowledgments

- [Brick Schema](https://brickschema.org/) community
- [ASHRAE Standard 223P](https://www.ashrae.org/) committee
- [BuildingMOTIF](https://github.com/NREL/BuildingMOTIF) project

## Support

- 📧 Email: your.email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/semantic-mpc-interface/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/semantic-mpc-interface/discussions)