#%%
from semantic_mpc_interface import LoadModel
from rdflib import Graph

b = LoadModel('../tutorial/test_site/test_build/test_build.ttl', 'brick')
all = b.get_all_building_objects()
print(all)