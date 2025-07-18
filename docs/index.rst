Semantic MPC Interface Documentation
====================================

Welcome to the Semantic MPC Interface documentation. This package provides a unified API for creating and managing semantic building models using Brick Schema and ASHRAE Standard 223P ontologies.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api/modules
   examples
   contributing

Features
--------

* **Multi-Ontology Support**: Works with both Brick Schema and ASHRAE Standard 223P
* **Grafana Integration**: Automatically generate monitoring dashboards  
* **SHACL Validation**: Ensure model correctness and completeness
* **Unit Conversion**: Seamless conversion between SI and Imperial units
* **Survey Tools**: Generate and process building metadata surveys
* **Point Management**: Add and manage sensor/actuator points
* **Template System**: Extensible template system for common building components

Quick Start
-----------

.. code-block:: python

   from semantic_mpc_interface import SemanticModelBuilder

   # Create a model builder
   builder = SemanticModelBuilder(
       site_id="building_001",
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

   # Save the model
   builder.save_model("building_model.ttl")

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`