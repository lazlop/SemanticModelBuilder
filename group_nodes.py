# %%
from typing import Union, List, Union, Tuple, Optional
from matplotlib import pyplot as plt
import time 
from dataclasses import dataclass
from pyoxigraph import *
from semantic_mpc_interface.namespaces import *
from rdflib import Graph, URIRef
from collections import defaultdict
from itertools import combinations
import pandas as pd
import numpy as np
# from IPython.display import display
import networkx as nx

# %%
@dataclass(frozen=True)
class Triple:
    s: Union[str, list]
    p: Union[str, list]
    o: Union[str, list]

class PatternQuery:
    def __init__(self, triples, graph=None):
        self.triples = triples
        self.graph = graph
        self.prefixes = get_prefixes(graph)
        self.query_dict = self.make_var_names(triples)
        self.filters = self.add_filters(self.query_dict)
        self.where = self.add_where(self.query_dict)
        self.queries = self.get_query()

    def add_filters(self, triples):
        filter_lst = []
        # anything of the same class should not equal another var of the same class
        filter_dict = defaultdict(set)
        for class_triple, var_triple in triples:
            filter_dict[class_triple.s].add(var_triple.s)
            filter_dict[class_triple.o].add(var_triple.o)
        for klass, var_list in filter_dict.items():
            if len(var_list) == 1:
                continue
            for var_1, var_2 in combinations(var_list, 2):
                filter_lst.append(f"FILTER (?{var_1} != ?{var_2}) .")

        return "\n".join(filter_lst)

    def make_var_names(self, triples):
        # makes a dictionary with triples of classes to triples with var names
        """
        Makes a dictionary with triples of classes to triples with var names
        :param triples: a list of tuples, where each tuple contains a triple of classes and a triple of variables
        :return: a list of tuples, where each tuple contains a triple of classes and a triple of variables with var names
        """
        counter = {}
        query_triples = []
        var_names = set()
        for class_triple, var_triple in triples:
            # Also replace dashes?
            subject = self.get_local_name(var_triple.s).replace("-", "_")
            object = self.get_local_name(var_triple.o).replace("-", "_")
            # have to remove angle brackets from predicate
            if class_triple.p.startswith("<"):
                p_var = class_triple.p.split("<")[1].split(">")[0]
            else:
                p_var = class_triple.p
            query_triples.append((class_triple, Triple(subject, p_var, object)))
        return query_triples

    def get_local_name(self, node):
        node = str(node).replace("<", "").replace(">", "")
        if "#" in node:
            return node.rpartition("#")[-1]
        else:
            return node.rpartition("/")[-1]

    # query fragments can be list, then list can be continuously concatenated with fragments. fragments can be joined by '\n'
    def add_where(self, query_triples):
        where = []
        for klass, var in query_triples:
            where.append(f"?{var.s} a {convert_to_prefixed(klass.s, self.graph)} .")
            where.append(f"?{var.s} {convert_to_prefixed(URIRef(var.p), self.graph)} ?{var.o} .")
            where.append(f"?{var.o} a {convert_to_prefixed(klass.o, self.graph)} .")
        return "\n".join(where)

    def get_query(self):
        # may need to add prefixes
        query = f"""{self.prefixes}\nSELECT DISTINCT * WHERE {{ {self.where}\n{self.filters} }}"""
        return query


class GraphPatternProcessor:
    """
    A class for processing graph patterns and identifying node groupings in RDF graphs.
    """
    
    def __init__(self, test_graph_file="test-graphs/test-graph.ttl", 
                 schema_graph_file="test-graphs/223p.ttl", 
                 namespace=S223):
        """
        Initialize the GraphPatternProcessor.
        
        Args:
            test_graph_file (str): Path to the test graph file
            schema_graph_file (str): Path to the schema graph file  
            namespace: The namespace to use for processing
        """
        self.test_graph_file = test_graph_file
        self.schema_graph_file = schema_graph_file
        self.namespace = namespace
        
        # Initialize graphs and store
        self.g = Graph(store="Oxigraph")
        self.g.parse(self.test_graph_file, format="turtle")
        self.EX = Namespace("urn:example#")
        
        self.prefixes = get_prefixes(self.g)
        
        self.store = Store()
        self.odg = NamedNode("urn:original-data-graph")
        self.dg = NamedNode("urn:data-graph")
        self.sg = NamedNode("urn:schema-graph")
        
        # Load data into store
        self.store.load(path=self.test_graph_file, format=RdfFormat.TURTLE, to_graph=self.odg)
        self.store.load(path=self.schema_graph_file, format=RdfFormat.TURTLE, to_graph=self.sg)
        
        # Initialize counter
        self.count_generator = self._counter()
        self.group_count_generator = self._counter()
        
    def _counter(self, start: int = 0, step: int = 1):
        """Generator for creating unique counters."""
        current = start
        while True:
            yield current
            current += step

    def get_local_name(self, node):
        """Extract the local name from a URI node."""
        node = str(node).replace("<", "").replace(">", "")
        if "#" in node:
            return node.rpartition("#")[-1]
        else:
            return node.rpartition("/")[-1]

    def check_ns(self, node, ns=None):
        """Check if a node belongs to a specific namespace."""
        if ns is None:
            ns = self.namespace
        return self.get_local_name(node) == str(node).replace(str(ns), "").replace(
            "<", ""
        ).replace(">", "")

    def get_class(self, node, store=None, prefixes=None, ns=None):
        """Get the most specific class for a node."""
        if store is None:
            store = self.store
        if prefixes is None:
            prefixes = self.prefixes
        if ns is None:
            ns = self.namespace
            
        ns_prefix = prefix_dict[ns]
        query = f"""
        {prefixes}
        # PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?class WHERE {{
            {str(node)} a ?class . 
            FILTER NOT EXISTS {{
                {str(node)} a ?subclass .
                ?subclass rdfs:subClassOf ?class .
            }}
            FILTER(STRSTARTS(STR(?class), str({ns_prefix}:)))
        }} """
        classes = list(store.query(query, use_default_graph_as_union=True))
        if len(classes) == 0:
            return None
        return classes[0]["class"].value

    def shorten_graph(self, store=None, prefixes=None, dg=None, odg=None, 
                     ns=None, exempt_predicates=["rdf:type"]):
        """
        Shorten the original data graph and put into new named graph.
        
        Args:
            exempt_predicates (list): Predicates to exclude from shortening
        """
        if store is None:
            store = self.store
        if prefixes is None:
            prefixes = self.prefixes
        if dg is None:
            dg = self.dg
        if odg is None:
            odg = self.odg
        if ns is None:
            ns = self.namespace
            
        # for s223 graphs I think we get rid of ["s223:cnx", "rdf:type"]
        # shortens original data graph (odg) and puts into new named graph called dg
        ns_prefix = prefix_dict[ns]
        print('ns_prefix', ns_prefix)
        pred_filters = """
            """.join(
            [f"FILTER(?p != {predicate} )" for predicate in exempt_predicates]
        )
        query = f"""
        {prefixes}
        CONSTRUCT {{
            ?s ?p ?o
            }} 
            WHERE {{  
            ?s ?p ?o . 
            {pred_filters}
            FILTER(STRSTARTS(STR(?p), str({ns_prefix}:)))
        }} """
        for r in store.query(query, default_graph=[odg]):
            s_class = self.get_class(r.subject, ns=ns)
            o_class = self.get_class(r.object, ns=ns)
            if o_class:
                store.add(Quad(r.subject, r.predicate, r.object, dg))
                store.add(Quad(r.subject, NamedNode(A), NamedNode(s_class), dg))
                store.add(Quad(r.object, NamedNode(A), NamedNode(o_class), dg))

    def get_triples(self, store=None, graph_name=None, ns=None):
        """Extract triples from the store for pattern matching."""
        if store is None:
            store = self.store
        if graph_name is None:
            graph_name = self.dg
        if ns is None:
            ns = self.namespace
            
        triples = []
        for quad in list(store.quads_for_pattern(None, None, None, graph_name)):
            if not self.check_ns(quad.predicate, ns):
                continue
            s_class = self.get_class(str(quad.subject), ns=ns)
            if s_class is None:
                continue
            o_class = self.get_class(str(quad.object), ns=ns)
            if o_class is None:
                continue
            triples.append(
                (
                    Triple(str(s_class), str(quad.predicate), str(o_class)),
                    Triple(str(quad.subject), str(quad.predicate), str(quad.object)),
                )
            )
        return triples

    def find_overlap_columns(self, df):
        """
        Check if any two columns in a DataFrame have the same value counts.

        Parameters:
        df (pandas.DataFrame): The DataFrame to check

        Returns:
        list: Pairs of column names that have identical value counts
        """
        result = []

        # Get all possible pairs of columns
        column_pairs = list(combinations(df.columns, 2))

        for col1, col2 in column_pairs:
            # Get value counts for both columns
            counts1 = df[col1].value_counts().sort_index()
            counts2 = df[col2].value_counts().sort_index()

            # Check if they have the same indices (values)
            if not counts1.index.equals(counts2.index):
                continue

            # Check if the counts are the same
            if not counts1.equals(counts2):
                continue

            # check if the columns are identical
            if np.array_equal(df[col1], df[col2]):
                # print('columns are identical')
                continue

            result.append((col1, col2))
        # get unpaired columns
        unpaired = []
        for col in df.columns:
            if col not in [c1 for c1, c2 in result] and col not in [
                c2 for c1, c2 in result
            ]:
                unpaired.append(col)

        return result, unpaired

    def find_cycles(self, pairs):
        """Find cycles in pairs using NetworkX."""
        G = nx.Graph()
        G.add_edges_from(pairs)
        cycles = list(nx.simple_cycles(G))
        return cycles

    def find_sets_from_pairs(self, pairs):
        """Find sets from pairs, handling cycles."""
        cycles = self.find_cycles(pairs)
        # Convert to tuples for hashability
        pair_tuples = [tuple(lst) for lst in pairs]
        check_set = set(pair_tuples)

        for cycle in cycles:
            cycle_tuple_set = set(combinations(cycle, 2))
            intersection = check_set.intersection(cycle_tuple_set)
            if intersection:
                check_set -= intersection

        groups = list(check_set)
        return groups + [tuple(cycle) for cycle in cycles]

    def find_sets(self, query, store=None, default_graph=None):
        """Find sets by running query and analyzing results."""
        if store is None:
            store = self.store
        if default_graph is None:
            default_graph = self.dg
            
        print("running query")
        st = time.time()
        res = store.query(query, default_graph=[default_graph])
        print("getting results to list")
        res_list = list(res)
        print("converting to dataframe")
        df = pd.DataFrame(res_list, columns=res.variables).map(self.get_local_name)
        et = time.time()
        print(f"took {et-st} seconds")
        print("finding overlapped columns")
        pairs, unpaired = self.find_overlap_columns(df)
        print("finding sets from pairs")
        groups = self.find_sets_from_pairs(pairs)
        return groups + unpaired

    def get_group_relations(self, groups, sets):
        """Get relations between groups and compose a new graph."""
        new_graph_triples = []
        for class_triple, triple in groups:
            for s_set in sets:
                if isinstance(s_set, tuple):
                    s_set = list(s_set)
                else:
                    s_set = [s_set]
                if Variable(triple.s) in s_set:
                    for o_set in sets:
                        if isinstance(o_set, tuple):
                            o_set = list(o_set)
                        else:
                            o_set = [o_set]
                        if Variable(triple.o) in o_set:
                            new_graph_triples.append(
                                (
                                    Triple(class_triple.s, triple.p, class_triple.o),
                                    Triple(s_set, triple.p, o_set),
                                )
                            )
        return new_graph_triples

    def group_serialization(self, group, var_replacement=""):
        """Serialize a group for naming purposes."""
        # doesn't work 
        # name = str(group[0])[:3].replace("?", var_replacement) + '_' + str(next(self.group_count_generator)) + '_' + str(len(group))
        print('serializing grouping')
        print(group)

        # this is only naming that works
        # return "_".join(str(var).replace("?", var_replacement) for var in group)
    
        return "_".join(str(var).replace("?", var_replacement) for var in group)

        # name = str(next(self.group_count_generator))
        # return name


    def create_new_graph(self, triples, ns=None):
        """
        Create a new graph with the triples.
        
        Args:
            triples: List of triples to add to the new graph
            ns: Namespace for the new graph
        """
        if ns is None:
            ns = self.EX
            
        # create a new graph with the triples
        # serialize groups
        group_dict = {}
        for class_triple, triple in triples:
            s = self.group_serialization(triple.s)
            o = self.group_serialization(triple.o)
            group_dict[s] = triple.s
            group_dict[o] = triple.o
            self.store.add(
                Quad(NamedNode(ns[s]), NamedNode(triple.p), NamedNode(ns[o]), NamedNode(ns))
            )
            self.store.add(
                Quad(
                    NamedNode(ns[s]), NamedNode(A), NamedNode(class_triple.s), NamedNode(ns)
                )
            )
            self.store.add(
                Quad(
                    NamedNode(ns[o]), NamedNode(A), NamedNode(class_triple.o), NamedNode(ns)
                )
            )
        return group_dict

    def run(self):
        """Run the initial pattern matching process."""
        print("getting triples")
        groups = self.get_triples()
        print("building query")
        p = PatternQuery(groups, graph=self.g)
        p.graph = self.g
        p.prefixes = self.prefixes
        sets = self.find_sets(p.queries, self.store, self.dg)
        return p, sets

    def run_for_groups(self, p, sets, store=None, schema_ns=None):
        """Run pattern matching for groups."""
        if store is None:
            store = self.store
        if schema_ns is None:
            schema_ns = self.namespace
            
        # ns is new graph namespace
        ns_str = self.dg.value + str(next(self.count_generator)) + "#"
        ns = Namespace(ns_str)
        print("getting_relations")
        new_graph_triples = self.get_group_relations(p.query_dict, sets)
        print("completed getting relations")
        group_dict = self.create_new_graph(new_graph_triples, ns)
        groups = self.get_triples(graph_name=NamedNode(ns), store=store, ns=schema_ns)

        p = PatternQuery(groups, graph = self.g)
        p.graph = self.g
        p.prefixes = self.prefixes
        sets = self.find_sets(p.queries, store, NamedNode(ns))
        return p, sets, group_dict

    def run_to_completion(self, store=None, schema_ns=None):
        """Run the pattern matching process to completion."""
        if store is None:
            store = self.store
        if schema_ns is None:
            schema_ns = self.namespace
            
        group_dicts = []
        all_sets = []
        all_p = []
        p, sets = self.run()
        all_sets.append(sets)
        all_p.append(p)
        break_next = False
        while True:
            p, sets, group_dict = self.run_for_groups(p, sets, store=store, schema_ns=schema_ns)
            print("set length ", len(sets))
            print("last set length", len(all_sets[-1]))
            group_dicts.append(group_dict)
            all_sets.append(sets)
            all_p.append(p)
            if break_next:
                break
            if len(sets) == len(all_sets[-1]):
                break_next = True 
        return all_p, all_sets, group_dicts
    
    def visualize_triples(self,
                      triples_data: List[str], 
                      figsize: Tuple[int, int] = (12, 10),
                      node_size: int = 2000,
                      node_color: str = "lightblue",
                      edge_color: str = "gray",
                      font_size: int = 10,
                      title: str = "Graph of Triples with Connection Relationships",
                      save_path: Optional[str] = None) -> plt.Figure:
        """
        Visualize RDF-like triples as a directed graph.
        
        Args:
            triples_data: List of triple strings in the format "Triple(s=[...], p='...', o=[...])"
            figsize: Figure size as (width, height) in inches
            node_size: Size of nodes in the graph
            node_color: Color of nodes
            edge_color: Color of edges
            font_size: Size of node labels
            title: Title of the graph
            save_path: Path to save the figure (if None, figure will be shown but not saved)
            
        Returns:
            matplotlib Figure object
        """
        # Create a directed graph
        G = nx.DiGraph()

        # Process each triple
        for triple in triples_data:
            # Extract subjects and objects
            G.add_edge(triple.s, triple.o)

        # Create a more organized layout
        pos = nx.spring_layout(G, seed=42)

        # Create figure
        fig = plt.figure(figsize=figsize)

        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_color, alpha=0.8)

        # Draw edges with arrows
        nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.7, edge_color=edge_color, 
                            connectionstyle='arc3,rad=0.1', arrowsize=15)

        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=font_size, font_family="sans-serif")

        # Add a title
        plt.title(title, fontsize=16)

        # Remove axis
        plt.axis("off")
        plt.tight_layout()
        
        # Save or show the figure
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
        
        return fig

    def process_and_visualize(self, exempt_predicates=None):
        """
        Main method to process the graph and visualize results.
        
        Args:
            exempt_predicates (list): Predicates to exempt from processing
        """
        if exempt_predicates is None:
            exempt_predicates = []

        # Process the graph
        self.shorten_graph(exempt_predicates=exempt_predicates)
        self.store.dump(
            "vrf-cut-short.ttl", format=RdfFormat.TURTLE, 
            from_graph=self.dg, prefixes=namespace_dict
        )
        
        all_p, all_sets, group_dicts = self.run_to_completion()
        
        # Display results
        display(all_sets)
        display(group_dicts)
        
        for i,p in enumerate(all_p):
            triples = [triples for _, triples in p.query_dict]
            self.visualize_triples(triples, save_path=f"graph-{i}.png")

        return all_p, all_sets, group_dicts


# Example usage and main execution
# if __name__ == "__main__":
#     # Create processor instance
#     # 1 (test-graph) and 5 (test-graph5) may be best
#     # TEST_GRAPH_FILE = "test-graphs/test-graph8.ttl"
#     TEST_GRAPH_FILE = "test-graphs/test-graph5.ttl"
#     # TEST_GRAPH_FILE = "test-graphs/test-graph.ttl"
#     SCHEMA_GRAPH_FILE = "test-graphs/223p.ttl"

#     processor = GraphPatternProcessor(test_graph_file=TEST_GRAPH_FILE, 
#                  schema_graph_file=SCHEMA_GRAPH_FILE, 
#                  namespace=S223)
    
#     # Process and visualize
#     all_p, all_sets, group_dicts = processor.process_and_visualize(exempt_predicates=[])

# # %%

# %%
