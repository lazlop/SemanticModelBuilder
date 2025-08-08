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

# %%
# still working on loader, will clean up class, but functionality about right
loader = LoadModel(f'tutorial/{ontology}-test_site/test_build/reasoned.ttl', ontology = ontology)
site_info = loader.get_all_building_objects()

# %%
print(site_info)

# %%
zone = site_info['zones'][-1]
print(zone)

# %%
print(zone.spaces[0].area)

# %%
# zone.windows[0].area.name

# # %%
# zone.tstats[0]
# %%
print(zone.tstats[0].tstat_resolution)
zone.tstats[0].tstat_resolution.convert_to_si()
print(zone.tstats[0].tstat_resolution)
print(zone.tstats[0].tstat_resolution.is_delta)

# %%
# optionally just load everything as si 
si_loader = LoadModel(f"tutorial/{ontology}-test_site/test_build/reasoned.ttl", ontology = ontology, as_si_units=True)
site_info = si_loader.get_all_building_objects()
print(zone.tstats[0].tstat_resolution)
print(get_thermostat_data(si_loader))
