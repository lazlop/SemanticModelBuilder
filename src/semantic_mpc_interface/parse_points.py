# Will add points to the brick model from volttron, can do some automation
# currently a placeholder that works for current method
# Can try some methods to generate the following csv file.
import pandas as pd
from rdflib import Literal

from .namespaces import *


def add_points(builder, mapping_file, ontology="brick"):
    # ontology can be brick or 223p
    mapping_df = pd.read_csv(mapping_file)
    for _, row in mapping_df.iterrows():

        zone_id = row["zone_id"]
        point_uri = builder.building_ns[f"{row['topic_name'].replace('/', '_')}"]
        # print(point_uri)
        unit_classes = {
            "F": (UNIT.DEG_F, QK.Temperature),
            "%": (UNIT.PERCENT, QK.DimensionlessRatio),
            "BTU_TH-PER-LB": (UNIT["BTU_TH-PER-LB"], QK.SpecificEnergy),
        }
        if row["unit_type"] in unit_classes:
            builder.model.graph.add(
                (point_uri, QUDT.hasUnit, unit_classes[row["unit_type"]][0])
            )
            builder.model.graph.add(
                (point_uri, QUDT.hasQuantityKind, unit_classes[row["unit_type"]][1])
            )

        if ontology == "brick":
            point_type = BRICK[row["point type"].replace(" ", "_")]
            # adding point to zone vs equipment
            if "domainSpace" in row["equipment"]:
                builder.model.graph.add(
                    (builder.building_ns[zone_id], BRICK.hasPoint, point_uri)
                )
            else:
                # relies on zones and hvac units being mapped consistently in variable-map and metadata
                hvac_unit = builder.model.graph.value(
                    builder.building_ns[str(zone_id)], BRICK.isFedBy, any=False
                )
                # print('hvac unit: ',hvac_unit)
                # print('zone id: ', zone_id)

                builder.model.graph.add((hvac_unit, BRICK.hasPoint, point_uri))
        else:
            point_type = S223[row["point type"].replace(" ", "_")]
            # adding point to zone vs equipment
            builder.model.graph.add(
                (builder.building_ns[zone_id], S223.hasPoint, point_uri)
            )

        builder.model.graph.add((point_uri, A, point_type))

        # Adding external reference to volttron topic
        builder.model.graph.add(
            (point_uri, REF.hasExternalReference, point_uri + "_external_reference")
        )
        builder.model.graph.add(
            (
                point_uri + "_external_reference",
                REF.hasTopic,
                Literal(row["topic_name"]),
            )
        )
