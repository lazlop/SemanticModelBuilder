# %%
# import sys
# sys.path.insert(0, '..')
from semantic_mpc_interface import (
    LoadModel,
    get_thermostat_data,
    HPFlexSurvey,
    convert_units,
    SHACLHandler
)
from buildingmotif.namespaces import BRICK, RDF
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library
import csv
from pyshacl.rdfutil import clone

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
s = HPFlexSurvey('s223_test_site','test_build','.', overwrite=True, ontology='s223')

# Generating a simple building structure that prefills csv files. 
s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
# Now check s223_test_site/test_build to look at survey files


# %%
# Will just fill the columns programmatically for testing, csv should be filled out otherwise
import sys
sys.path.insert(0,'examples')
from example_prefill_usage import prefill_csv_survey

# %%
prefill_csv_survey('s223_test_site/test_build')

# %%
# Reading csv
s.read_csv()

# %% [markdown]
# # Testing SHACL Generation and Validation

# %%
og = clone.clone_graph(s.graph)

# %%
# Create handler
handler = SHACLHandler(ontology='s223')

# Generate shapes
handler.generate_shapes()

# Save shapes
handler.save_shapes('shapes.ttl')

# Validate a model
conforms, results_graph, results_text = handler.validate_model(s.graph)

s.graph.serialize('test-s223-model-reasoned.ttl', format = 'ttl')
if not conforms:
    print("Validation failed:")
    print(results_text)

# %%
# lots of new inferred information
(s.graph-og).print()

# %% [markdown]
# # Testing get Metadata

# %%
# still working on loader, will clean up class, but functionality about right
loader = LoadModel("s223_test_site/test_build/test_build.ttl", ontology = 's223')
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
si_loader = LoadModel("s223_test_site/test_build/test_build.ttl", ontology = 's223', as_si_units=True)
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
