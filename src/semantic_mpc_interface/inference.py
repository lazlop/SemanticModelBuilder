from typing import Optional

import pandas as pd
from rdflib import Graph, Literal, URIRef

from .namespaces import *
from .utils import * 

from importlib.resources import files

def add_brick_inverse_relations(g):
    # Dictionary of relationships and their inverses
    inverse_pairs = {
        BRICK.isFedBy: BRICK.feeds,
        BRICK.feeds: BRICK.isFedBy,
        BRICK.hasPart: BRICK.isPartOf,
        BRICK.isPartOf: BRICK.hasPart,
        BRICK.hasPoint: BRICK.isPointOf,
        BRICK.isPointOf: BRICK.hasPoint,
        BRICK.hasLocation: BRICK.isLocationOf,
        BRICK.isLocationOf: BRICK.hasLocation,
        BRICK.controls: BRICK.isControlledBy,
        BRICK.isControlledBy: BRICK.controls,
        BRICK.affects: BRICK.isAffectedBy,
        BRICK.isAffectedBy: BRICK.affects,
        BRICK.hasInput: BRICK.isInputOf,
        BRICK.isInputOf: BRICK.hasInput,
        BRICK.hasOutput: BRICK.isOutputOf,
        BRICK.isOutputOf: BRICK.hasOutput,
        BRICK.measures: BRICK.isMeasuredBy,
        BRICK.isMeasuredBy: BRICK.measures,
        BRICK.regulates: BRICK.isRegulatedBy,
        BRICK.isRegulatedBy: BRICK.regulates,
        BRICK.hasSubject: BRICK.isSubjectOf,
        BRICK.isSubjectOf: BRICK.hasSubject,
    }
    # For each relationship in the graph, add its inverse
    for s, p, o in g:
        if p in inverse_pairs:
            g.add((o, inverse_pairs[p], s))

    return g

# def add_connection(g: Graph):
#     for sub, pred, obj in g:
#         if pred == S223.connectedTo:
#             # namespace, sub, pred
#             base_name = str(g.compute_qname(sub)[1]) + g.compute_qname(sub)[-1] + '-' +  g.compute_qname(obj)[-1]
#             from_name = base_name + 'from'
#             to_name = base_name + 'to'
#             con_name = base_name + 'con'
#             temp = s.templates.get_template_by_name('air-connected-to-complete').inline_dependencies()
#             add_graph = temp.evaluate({'from-cp': URIRef(from_name), 
#                         'target': obj,
#                             'to-cp': URIRef(to_name),
#                             'name': sub,
#                             'connection': URIRef(con_name)})
#             g = g + add_graph
