# %%
# import sys
# sys.path.insert(0, '..')
from semantic_mpc_interface import (
    LoadModel,
    get_thermostat_data,
    HPFlexSurvey,
    convert_units,
    SHACLHandler,
    # add_connection
)
from buildingmotif.namespaces import BRICK, RDF
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library
import csv
from pyshacl.rdfutil import clone

ontology = 's223'

# %% [markdown]
# # Testing the Model Builder
# 
# ModelBuilder has been deprecated in favor of just survey based workflow. May be readded in the future

# %% [markdown]
# # Testing the Survey Workflow

# %%
# Please disregard excessive outputs (logging and warnings)
# TODO: Figure out how to configure these in building motif 
import logging
logging.disable(logging.CRITICAL)
import warnings
warnings.filterwarnings("ignore")

# %%
# Creating survey, allow overwrite if there is something already there
s = HPFlexSurvey(f'tutorial/{ontology}-test_site','test_build','.', overwrite=True, ontology=ontology)

# Generating a simple building structure that prefills csv files. 
s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
# Now check s223_test_site/test_build to look at survey files


# %%
# Will just fill the columns programmatically for testing, csv should be filled out otherwise
import sys
sys.path.insert(0,'examples')
# sys.path.insert(0,'../examples')
from example_prefill_usage import prefill_csv_survey

# %%
prefill_csv_survey(f'tutorial/{ontology}-test_site/test_build')

# %%
# Reading csv
s.read_csv()

# add_connection(s.graph)

# %% [markdown]
# # Testing SHACL Generation and Validation

# %%
# Create handler
handler = SHACLHandler(ontology=ontology)

# Generate shapes
handler.generate_shapes()

# Save shapes
handler.save_shapes('shapes.ttl')

# Run inference on model
inferred_graph = handler.infer(s.graph)

inferred_graph.serialize(f'tutorial/{ontology}-test_site/test_build/reasoned.ttl', format = 'ttl')
# if not validation_result.valid:
#     print("Validation failed:")
#     print(validation_result.report_string)
# %% [markdown]
# # Testing get Metadata

# %%
# still working on loader, will clean up class, but functionality about right
loader = LoadModel(f'tutorial/{ontology}-test_site/test_build/reasoned.ttl', ontology = ontology)
site_info = loader.get_all_building_objects()

# %%
print(site_info)

# %%
zone = site_info['zones'][0]
print(zone)

# %%
zone.windows

# %%
zone.windows[0].area.name

# %%
zone.tstats[0]

# %%
print(zone.tstats[0].resolution)
zone.tstats[0].resolution.convert_to_si()
print(zone.tstats[0].resolution)
print(zone.tstats[0].resolution.is_delta)

# %%
# optionally just load everything as si 
si_loader = LoadModel(f"tutorial/{ontology}-test_site/test_build/test_build.ttl", ontology = ontology, as_si_units=True)
site_info = si_loader.get_all_building_objects()
print(zone.tstats[0].resolution)

# %%
# Getting the thermostat metadata
get_thermostat_data(si_loader)

# %%
# Getting the thermostat metadata for 1 zone 
get_thermostat_data(si_loader, ['zone_1','zone_2'])

# %% [markdown]
# # Testing Unit Conversion

# %%
convert_units(10, 'FT', 'M')

# %%
convert_units(0, 'DEG_C', 'DEG_F')

# %%
convert_units(0, 'DEG_C', 'K')
