#%%
from semantic_mpc_interface import BuildingMetadataLoader
from rdflib import Graph

b = BuildingMetadataLoader('../tutorial/test_site/test_build/test_build.ttl', 'brick')
all = b.get_all_building_objects()
print(all)
# %%
# if __name__ == "__main__":
#     b = BuildingMetadataLoader('tutorial/test_site/test_build/test_build.ttl', 'brick')
    
#     # Test with hvac-zone template
#     print("=== Testing with hvac-zone template ===")
#     zones = get_objects_generalized(g, 'hvac-zone')
    
#     # Display the created objects
#     for zone in zones:
#         print(f"\n{zone}")
#         # Dynamically access all entity types
#         for attr_name in dir(zone):
#             if attr_name.endswith('s') and not attr_name.startswith('_'):
#                 entities = getattr(zone, attr_name)
#                 if isinstance(entities, list):
#                     for entity in entities:
#                         print(f"  {entity}")
    
#     # Example: Access specific data from the objects
#     print("\n=== Example data access ===")
#     if zones:
#         first_zone = zones[0]
#         print(f"First zone name: {first_zone.name}")
        
#         # Dynamically access attributes
#         for attr_name in dir(first_zone):
#             if attr_name.endswith('s') and not attr_name.startswith('_'):
#                 entities = getattr(first_zone, attr_name)
#                 if isinstance(entities, list) and entities:
#                     first_entity = entities[0]
#                     print(f"First {attr_name[:-1]}: {first_entity}")
                    
#                     # Access entity attributes
#                     for entity_attr in dir(first_entity):
#                         if not entity_attr.startswith('_') and entity_attr != 'name':
#                             value = getattr(first_entity, entity_attr)
#                             if value is not None:
#                                 print(f"  {entity_attr}: {value}")
    
#     # Test with other templates
#     print("\n=== Testing with other templates ===")
#     try:
#         # Test site template if data exists
#         sites = get_objects_generalized(g, 'site')
#         print(f"Sites found: {len(sites)}")
#         for site in sites:
#             print(f"  {site}")
#     except Exception as e:
#         print(f"Site template test failed: {e}")
    
#     try:
#         # Test space template if data exists  
#         spaces = get_objects_generalized(g, 'space')
#         print(f"Spaces found: {len(spaces)}")
#         for space in spaces:
#             print(f"  {space}")
#     except Exception as e:
#         print(f"Space template test failed: {e}")
    
#     # Verification
#     print(f"\nVerification:")
#     print(f"Total zones created: {len(zones)}")
#     if zones:
#         total_spaces = sum(len(getattr(zone, 'spaces', [])) for zone in zones)
#         total_windows = sum(len(getattr(zone, 'windows', [])) for zone in zones)
#         print(f"Total spaces: {total_spaces}")
#         print(f"Total windows: {total_windows}")