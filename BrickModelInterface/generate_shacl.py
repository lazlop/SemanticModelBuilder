import yaml
import rdflib
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from pyshacl import validate
from .namespaces import *
from pathlib import Path
from importlib.resources import files
from .utils import * 
from buildingmotif.dataclasses import Library
from rdflib import Namespace

from buildingmotif import BuildingMOTIF, get_building_motif
from buildingmotif.dataclasses import Library, Model


class SHACLHandler:
    """Class to handle SHACL shape generation and validation"""
    
    def __init__(self, template_dir=None):
        """Initialize SHACL handler
        May want option to pass in existing buildingmotif instance.
        Args:
            template_dir: Directory containing templates. If None, uses default s223 templates
        """
        # Not sure how to manage building motif

        if template_dir is None:
            template_dir = str(files('BrickModelInterface').joinpath('s223-templates'))
        self.template_dir = Path(template_dir)
        self.nodes_templates = self.template_dir.joinpath('nodes.yml')
        self.relations_templates = self.template_dir.joinpath('relations.yml')
        self.shapes_graph = Graph()
        bind_prefixes(self.shapes_graph)

        try:
            self.bm = get_building_motif()
            self.template_library = Library.load(db_id = 1)
        except Exception as e:
            print('BuildingMOTIF or Templates do not exist:', e)
            self.bm = BuildingMOTIF("sqlite://")
            self.template_library = Library.load(directory=str(self.template_dir))
        
    def _get_template_types(self, g):
        """Parse the RDF template body and extract type information"""
        
        # Find the type of the main entity (p:name)
        p = Namespace('urn:___param___#')
        types = list(g.objects(p.name, RDF.type))
        main_type = None
        for rdf_type in types: 
            if URIRef(S223) == g.compute_qname(rdf_type)[1]:
                main_type = rdf_type
        if main_type is None:
            raise ValueError("No main type found in template")
        return main_type, types
    def _get_dependency_name_by_arg_name(self, template_graph,template, name):
        name = get_uri_name(template_graph, name)
        for dependencies in template['dependencies']:
            if dependencies['args']['name'] == name:
                return dependencies['template']

    def generate_shapes(self):
        with open(self.nodes_templates, 'r') as f:
            templates = yaml.safe_load(f)
        self.nodes_templates_names = list(templates.keys())
        
        with open(self.relations_templates, 'r') as f:
            templates = yaml.safe_load(f)
        self.relations_templates_names = list(templates.keys())

        self._generate_shapes(templates_file=self.nodes_templates)
        self._generate_relation_inference(templates_file=self.relations_templates)
    
    def _parse_template(self, template_data):
        if 'body' not in template_data:
            raise ValueError(f"Template does not have a body")
        template_graph = Graph()
        template_graph.parse(data=template_data['body'], format='turtle')
        return template_graph
    
    def _generate_relation_inference(self, templates_file):
        with open(templates_file, 'r') as f:
            templates = yaml.safe_load(f)
        # Kind of turning SHACL into OWL for 223
        for template_name in templates.keys():
            template = self.template_library.get_template_by_name(template_name)
            template_graph = template.inline_dependencies().body
            # main_relation, main_target = list(template.body.predicate_objects(PARAM.name))[0]
            self.shapes_graph.add((HPFS[f'{template_name}Annotation'], RDF.type, SH.NodeShape))
            main_relation, main_target = list(template.body.predicate_objects(PARAM.name))[0]
            self.shapes_graph.add((HPFS[f'{template_name}Annotation'], SH.targetSubjectsOf, main_relation))
            self.shapes_graph.add((HPFS[f'{template_name}Annotation'], SH.rule, HPFS[f'{template_name}AnnotationRule']))
            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], RDF.type, SH.SPARQLRule))
            sparql_rule = f"""
                CONSTRUCT {{
                    ?name <{HPFS[template_name]}> ?target .
                }}
                """
            sparql_rule += "WHERE {\n"
            for s,p,o in template_graph.triples((None, None, None)):
                if template_graph.compute_qname(s)[1] == URIRef(PARAM):
                    s_var = "?"+ get_uri_name(template_graph, s).replace('-', '_')
                else:
                    s_var = f"<{s}>"
                if isinstance(o, Literal):
                    o_var = str(o).capitalize()
                elif template_graph.compute_qname(o)[1] == URIRef(PARAM):
                    o_var = "?"+ get_uri_name(template_graph, o).replace('-', '_')
                else:
                    o_var = f"<{o}>"
                sparql_rule += f"\t{s_var} <{p}> {o_var} . \n"
            sparql_rule += '}'
            
            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], SH.construct, Literal(sparql_rule)))
        
    def _generate_shapes(self, templates_file):
        """Convert templates to SHACL shapes
        
        Args:
            templates_file: Path to templates YAML file. If None, uses default s223 templates
        
        Returns:
            Graph: The generated SHACL shapes graph
        """            
        # Parse YAML
        with open(templates_file, 'r') as f:
            templates = yaml.safe_load(f)
        # Kind of turning SHACL into OWL for 223
        for template_name, template_data in templates.items():
            template_graph = self._parse_template(template_data)
            
            main_type, types = self._get_template_types(template_graph)
            is_relation_shape = False

            shape_uri = HPFS[f'{template_name}']
            
            # Add basic shape properties
            self.shapes_graph.add((shape_uri, RDF.type, SH.NodeShape))
            self.shapes_graph.add((shape_uri, RDF.type, RDFS['Class']))
            self.shapes_graph.add((shape_uri, RDF.type, S223['Class']))
            # self.shapes_graph.add((shape_uri, SH.targetClass, main_type))
            for rdf_type in types:
                self.shapes_graph.add((shape_uri, SH['class'], rdf_type))
            
            if 'dependencies' in template_data:
                dependency_names = {PARAM[template['args']['name']]:template['template'] for template in template_data['dependencies']}
            else:
                dependency_names = {}
            
            prop_counts = {}
            for s, p, o in template_graph.triples((None, None, None)):
                if p == RDF.type:
                    continue
                
                if p in prop_counts.keys():
                    prop_counts[p] += 1
                else:
                    prop_counts[p] = 1
                
                if not isinstance(o,Literal):
                    if PARAM == self.shapes_graph.compute_qname(o)[1]: 
                        continue
                        # Constraint covered by mincount

                prop_shape = create_uri_name_from_uris(self.shapes_graph, HPFS, [shape_uri,o])
                self.shapes_graph.add((shape_uri, SH.property, prop_shape))
                self.shapes_graph.add((prop_shape, RDF.type, SH.PropertyShape))
                self.shapes_graph.add((prop_shape, SH.path, p))
                self.shapes_graph.add((prop_shape, SH.qualifiedMinCount, Literal(1)))

                qual_val_shape = create_uri_name_from_uris(self.shapes_graph, HPFS, [shape_uri,o])
                self.shapes_graph.add((prop_shape, SH.qualifiedValueShape, qual_val_shape))
                self.shapes_graph.add((qual_val_shape, RDF.type, SH.NodeShape))
                
                if isinstance(o,Literal):
                    self.shapes_graph.add((qual_val_shape, SH['hasValue'], o))
                elif o in dependency_names.keys():
                    self.shapes_graph.add((qual_val_shape, SH['class'], HPFS[dependency_names[o]]))
                else:
                    self.shapes_graph.add((qual_val_shape, SH['hasValue'], o))

            # Need to specify that properties can't have any other aspects - this is very specific to 223.
            # If templates defined EVERYTHING that would exist in 223 this could be generalized, but currently we do not do this. 
            # It's a struggle in 223P using SPARQL to get just a temperature measurement and not a temperature deadband property, because the temperature deadband has everything the temperature sensor property has and more
            # Brick classification makes it easier to say if you want a specific class, or if you want to include all the superclasses. 
            # perhaps this just means that SPARQL is not a sufficient query engine for this use case. 

            # Might just add mincount of 0 for aspects, not sure there will be that many edge cases
            # Might learn more about how aspect can be used by helping haystack define their RDF/SHACL export
            
            # Not great implementation, but works for now 
            for p, count in prop_counts.items():
                prop_shape = create_uri_name_from_uris(self.shapes_graph, HPFS, [shape_uri, p])
                self.shapes_graph.add((shape_uri, SH.property, prop_shape))
                self.shapes_graph.add((prop_shape, SH.minCount, Literal(count)))
                self.shapes_graph.add((prop_shape, SH.maxCount, Literal(count)))
                self.shapes_graph.add((prop_shape, SH.path, p))
            if S223['hasAspect'] not in prop_counts.keys():
                prop_shape = create_uri_name_from_uris(self.shapes_graph, HPFS, [shape_uri], '_noAspects')
                self.shapes_graph.add((shape_uri, SH.property, prop_shape))
                self.shapes_graph.add((prop_shape, SH.minCount, Literal(0)))
                self.shapes_graph.add((prop_shape, SH.maxCount, Literal(0)))
                self.shapes_graph.add((prop_shape, SH.path, S223.hasAspect))
            
            self.shapes_graph.add((HPFS[f'{template_name}Annotation'], RDF.type, SH.NodeShape))
            self.shapes_graph.add((HPFS[f'{template_name}Annotation'], SH.rule, HPFS[f'{template_name}AnnotationRule']))
            # Can be done using buildingMOTIF inline dependencies before creating sparql rather than relying on other shape classes
            # Inline dependencies works well for inference for both nodes and properties, but doesn't have other capabilities for validation
            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], RDF.type, SH.TripleRule))
            self.shapes_graph.add((HPFS[f'{template_name}Annotation'], SH.targetClass, main_type))

            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], SH.subject, SH.this))
            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], SH.predicate, RDF.type))
            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], SH.object, shape_uri))
            self.shapes_graph.add((HPFS[f'{template_name}AnnotationRule'], SH.condition, shape_uri))

    def validate_model(self, data_graph, shapes_graph=None, inference='rdfs'):
        """Validate a data graph against SHACL shapes
        
        Args:
            data_graph: The RDF graph to validate
            shapes_graph: Optional SHACL shapes graph. If None, uses previously generated shapes
            inference: Reasoning to apply ('none', 'rdfs', 'owlrl', etc.)
            
        Returns:
            tuple: (conforms, results_graph, results_text)
        """
        # TODO: generic validation output is so verbose that it's useless. Need to use the results to provide a better validation report
        if shapes_graph is None:
            if self.shapes_graph is None:
                raise ValueError("No shapes graph available. Generate shapes first or provide a shapes graph.")
            shapes_graph = self.shapes_graph
            
        return validate(data_graph, shacl_graph=shapes_graph,
            advanced=True,
            allow_warnings=False,
            inplace=True,
            iterate_rules=True,
        )

    def save_shapes(self, filename, format='turtle'):
        """Save the SHACL shapes graph to a file
        
        Args:
            filename: Output file path
            format: RDF serialization format
        """
        if self.shapes_graph is None:
            raise ValueError("No shapes graph available. Generate shapes first.")
        self.shapes_graph.serialize(filename, format=format)