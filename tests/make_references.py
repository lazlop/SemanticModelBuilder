from semantic_mpc_interface import (
    LoadModel,
    get_thermostat_data,
    HPFlexSurvey,
    convert_units,
    SHACLHandler,
    # add_connection
)
from utils import prefill_csv_survey
from buildingmotif import get_building_motif

def make_references(ontology):
    # Creating survey, allow overwrite if there is something already there
    s = HPFlexSurvey(f'{ontology}-test_site','test_build','tests/reference-models', overwrite=True, ontology=ontology,
                    template_dict = {'zone': 'hvac-zone',
                                    "space": "space",
                                    "hvac": "hp-rtu",
                                    "tstat": "tstat",
                                    "window": "window",
                                    "site": "site" })

    # Generating a simple building structure that prefills csv files. 
    s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
    # Now check test_site/test_build to look at survey files

    s.easy_config(zone_space_window_list=[(2,2),(1,2),(1,3)])
    prefill_csv_survey(f'tests/reference-models/{ontology}-test_site/test_build')
    s.read_csv()

    handler = SHACLHandler(ontology=ontology)
    handler.generate_shapes()
    inferred_graph = handler.infer(s.graph)
    inferred_graph.serialize(f'tests/reference-models/{ontology}-test_site/test_build/reasoned.ttl', format = 'ttl')

def main():

    make_references('brick')

    bm = get_building_motif()
    bm.table_connection.delete_db_library(1)

    make_references('s223')

if __name__ == '__main__':
    main()