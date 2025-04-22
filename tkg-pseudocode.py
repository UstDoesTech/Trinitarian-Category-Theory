"""
Trinitarian Knowledge Graph (TKG) Implementation
A demonstration of the three-dimensional knowledge representation approach
that unifies ontological, instance, and contextual knowledge.
"""

from typing import Dict, List, Set, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
import json
import datetime
import re
from collections import defaultdict


# =============================================================================
# 1. CORE DATA STRUCTURES
# =============================================================================

@dataclass
class Node:
    """Base node class for all graphs"""
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    graph: Any = None
    
    def __hash__(self):
        return hash((self.id, self.type))
    
    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id and self.type == other.type
    
    def to_dict(self):
        """Convert node to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type,
            "properties": self.properties
        }


@dataclass
class Edge:
    """Base edge class for all graphs"""
    id: str
    source: Node
    target: Node
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    graph: Any = None
    
    def __hash__(self):
        return hash((self.id, self.source.id, self.target.id, self.type))
    
    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return (self.id == other.id and
                self.source.id == other.source.id and
                self.target.id == other.target.id and
                self.type == other.type)
    
    def to_dict(self):
        """Convert edge to dictionary for serialization"""
        return {
            "id": self.id,
            "source": self.source.id,
            "target": self.target.id,
            "type": self.type,
            "properties": self.properties
        }


class Graph:
    """Base graph class with core functionality"""
    
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.indexes: Dict[str, Dict] = {}
    
    def add_node(self, node: Node) -> Node:
        """Add a node to the graph"""
        self.nodes[node.id] = node
        node.graph = self
        self._update_indexes("node_added", node)
        return node
    
    def add_edge(self, edge: Edge) -> Edge:
        """Add an edge to the graph"""
        self.edges[edge.id] = edge
        edge.graph = self
        self._update_indexes("edge_added", edge)
        return edge
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its connected edges"""
        if node_id not in self.nodes:
            return False
        
        # Remove all connected edges
        connected_edges = self.get_edges_for_node(node_id)
        for edge in connected_edges:
            self.remove_edge(edge.id)
        
        node = self.nodes[node_id]
        self._update_indexes("node_removed", node)
        del self.nodes[node_id]
        return True
    
    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph"""
        if edge_id not in self.edges:
            return False
        
        edge = self.edges[edge_id]
        self._update_indexes("edge_removed", edge)
        del self.edges[edge_id]
        return True
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by its ID"""
        return self.nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by its ID"""
        return self.edges.get(edge_id)
    
    def get_nodes_of_type(self, node_type: str) -> List[Node]:
        """Get all nodes of a specific type"""
        return [node for node in self.nodes.values() if node.type == node_type]
    
    def get_edges_of_type(self, edge_type: str) -> List[Edge]:
        """Get all edges of a specific type"""
        return [edge for edge in self.edges.values() if edge.type == edge_type]
    
    def get_edges_for_node(self, node_id: str, direction: str = "both") -> List[Edge]:
        """Get all edges connected to a node"""
        if node_id not in self.nodes:
            return []
        
        result = []
        for edge in self.edges.values():
            if direction == "outgoing" and edge.source.id == node_id:
                result.append(edge)
            elif direction == "incoming" and edge.target.id == node_id:
                result.append(edge)
            elif direction == "both" and (edge.source.id == node_id or edge.target.id == node_id):
                result.append(edge)
        
        return result
    
    def find_nodes(self, constraints: Dict) -> List[Node]:
        """Find nodes matching the given constraints"""
        result = []
        for node in self.nodes.values():
            if self._matches_constraints(node, constraints):
                result.append(node)
        return result
    
    def find_edges(self, constraints: Dict) -> List[Edge]:
        """Find edges matching the given constraints"""
        result = []
        for edge in self.edges.values():
            if self._matches_constraints(edge, constraints):
                result.append(edge)
        return result
    
    def _matches_constraints(self, entity: Union[Node, Edge], constraints: Dict) -> bool:
        """Check if an entity matches the given constraints"""
        for key, value in constraints.items():
            if key == "$and":
                if not all(self._matches_constraints(entity, sub_constraint) for sub_constraint in value):
                    return False
            elif key == "$or":
                if not any(self._matches_constraints(entity, sub_constraint) for sub_constraint in value):
                    return False
            elif "." in key:
                # Handle nested properties with dot notation
                parts = key.split(".")
                current = entity
                for part in parts[:-1]:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    elif isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return False
                
                last_part = parts[-1]
                if hasattr(current, last_part):
                    current_value = getattr(current, last_part)
                elif isinstance(current, dict) and last_part in current:
                    current_value = current[last_part]
                else:
                    return False
                
                if isinstance(value, dict) and list(value.keys())[0].startswith("$"):
                    # Handle operators like $gt, $lt, etc.
                    operator = list(value.keys())[0]
                    operator_value = value[operator]
                    
                    if operator == "$gt" and not (current_value > operator_value):
                        return False
                    elif operator == "$lt" and not (current_value < operator_value):
                        return False
                    elif operator == "$gte" and not (current_value >= operator_value):
                        return False
                    elif operator == "$lte" and not (current_value <= operator_value):
                        return False
                    elif operator == "$ne" and not (current_value != operator_value):
                        return False
                elif current_value != value:
                    return False
            else:
                # Direct property check
                if isinstance(entity, Node) or isinstance(entity, Edge):
                    if key == "properties":
                        # Match all properties
                        for prop_key, prop_value in value.items():
                            if prop_key not in entity.properties or entity.properties[prop_key] != prop_value:
                                return False
                    elif key == "id" and entity.id != value:
                        return False
                    elif key == "type" and entity.type != value:
                        return False
                    elif key in entity.properties and entity.properties[key] != value:
                        return False
                    elif key not in ["id", "type", "properties"] and not hasattr(entity, key):
                        return False
                    elif hasattr(entity, key) and getattr(entity, key) != value:
                        return False
                else:
                    return False
        
        return True
    
    def _update_indexes(self, operation: str, entity: Union[Node, Edge]) -> None:
        """Update all indexes based on operation"""
        for index_name, index in self.indexes.items():
            if operation == "node_added" and isinstance(entity, Node):
                if hasattr(index, "add_node"):
                    index.add_node(entity)
            elif operation == "edge_added" and isinstance(entity, Edge):
                if hasattr(index, "add_edge"):
                    index.add_edge(entity)
            elif operation == "node_removed" and isinstance(entity, Node):
                if hasattr(index, "remove_node"):
                    index.remove_node(entity)
            elif operation == "edge_removed" and isinstance(entity, Edge):
                if hasattr(index, "remove_edge"):
                    index.remove_edge(entity)
    
    def create_index(self, name: str, index_type: str, properties: List[str]) -> None:
        """Create an index of the specified type on the specified properties"""
        # This is a simplified index implementation
        if index_type == "hash":
            self.indexes[name] = HashIndex(properties)
        elif index_type == "btree":
            self.indexes[name] = BTreeIndex(properties)
        
        # Populate the index with existing data
        if properties[0].startswith("node."):
            for node in self.nodes.values():
                self.indexes[name].add_node(node)
        elif properties[0].startswith("edge."):
            for edge in self.edges.values():
                self.indexes[name].add_edge(edge)
    
    def identity(self, obj: Node) -> Edge:
        """Create or get identity edge for a node"""
        for edge in self.edges.values():
            if (edge.source == obj and edge.target == obj and 
                edge.type == f"identity_{obj.type}"):
                return edge
        
        # Create new identity edge
        identity_edge = Edge(
            id=f"identity_{obj.id}",
            source=obj,
            target=obj,
            type=f"identity_{obj.type}"
        )
        return self.add_edge(identity_edge)


# Simple index implementations
class HashIndex:
    """Simple hash index implementation"""
    
    def __init__(self, properties: List[str]):
        self.properties = properties
        self.node_index: Dict[Any, Set[Node]] = defaultdict(set)
        self.edge_index: Dict[Any, Set[Edge]] = defaultdict(set)
    
    def add_node(self, node: Node) -> None:
        """Add a node to the index"""
        for prop in self.properties:
            if prop.startswith("node.properties."):
                prop_name = prop.split(".")[-1]
                if prop_name in node.properties:
                    self.node_index[node.properties[prop_name]].add(node)
            elif prop == "node.type":
                self.node_index[node.type].add(node)
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the index"""
        for prop in self.properties:
            if prop.startswith("edge.properties."):
                prop_name = prop.split(".")[-1]
                if prop_name in edge.properties:
                    self.edge_index[edge.properties[prop_name]].add(edge)
            elif prop == "edge.type":
                self.edge_index[edge.type].add(edge)
    
    def remove_node(self, node: Node) -> None:
        """Remove a node from the index"""
        for nodes in self.node_index.values():
            if node in nodes:
                nodes.remove(node)
    
    def remove_edge(self, edge: Edge) -> None:
        """Remove an edge from the index"""
        for edges in self.edge_index.values():
            if edge in edges:
                edges.remove(edge)


class BTreeIndex:
    """Simple B-tree index simulation (actual implementation would be more complex)"""
    
    def __init__(self, properties: List[str]):
        self.properties = properties
        self.node_index: Dict[Any, Set[Node]] = defaultdict(set)
        self.edge_index: Dict[Any, Set[Edge]] = defaultdict(set)
        self.sorted_keys = []
    
    # Methods same as HashIndex for this demo
    def add_node(self, node: Node) -> None:
        """Add a node to the index"""
        for prop in self.properties:
            if prop.startswith("node.properties."):
                prop_name = prop.split(".")[-1]
                if prop_name in node.properties:
                    self.node_index[node.properties[prop_name]].add(node)
                    if node.properties[prop_name] not in self.sorted_keys:
                        self.sorted_keys.append(node.properties[prop_name])
                        self.sorted_keys.sort()
            elif prop == "node.type":
                self.node_index[node.type].add(node)
                if node.type not in self.sorted_keys:
                    self.sorted_keys.append(node.type)
                    self.sorted_keys.sort()
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the index"""
        for prop in self.properties:
            if prop.startswith("edge.properties."):
                prop_name = prop.split(".")[-1]
                if prop_name in edge.properties:
                    self.edge_index[edge.properties[prop_name]].add(edge)
                    if edge.properties[prop_name] not in self.sorted_keys:
                        self.sorted_keys.append(edge.properties[prop_name])
                        self.sorted_keys.sort()
            elif prop == "edge.type":
                self.edge_index[edge.type].add(edge)
                if edge.type not in self.sorted_keys:
                    self.sorted_keys.append(edge.type)
                    self.sorted_keys.sort()
    
    def remove_node(self, node: Node) -> None:
        """Remove a node from the index"""
        for nodes in self.node_index.values():
            if node in nodes:
                nodes.remove(node)
    
    def remove_edge(self, edge: Edge) -> None:
        """Remove an edge from the index"""
        for edges in self.edge_index.values():
            if edge in edges:
                edges.remove(edge)


# =============================================================================
# 2. SPECIALIZED GRAPH TYPES
# =============================================================================

class OntologicalGraph(Graph):
    """Graph for ontological knowledge - concepts, properties, and relations"""
    
    def __init__(self, name: str):
        super().__init__(name)
        # Create indexes specific to ontological graphs
        self.create_index("concept_hierarchy", "btree", ["edge.type"])
        self.create_index("concept_properties", "hash", ["edge.type"])
    
    def add_concept(self, id: str, properties: Dict[str, Any]) -> Node:
        """Add a concept node to the graph"""
        node = Node(id=id, type="Concept", properties=properties)
        return self.add_node(node)
    
    def add_relation(self, id: str, properties: Dict[str, Any]) -> Node:
        """Add a relation node to the graph"""
        node = Node(id=id, type="Relation", properties=properties)
        return self.add_node(node)
    
    def add_property(self, id: str, properties: Dict[str, Any]) -> Node:
        """Add a property node to the graph"""
        node = Node(id=id, type="Property", properties=properties)
        return self.add_node(node)
    
    def define_is_a(self, source_id: str, target_id: str, properties: Dict = None) -> Optional[Edge]:
        """Define an IS-A relationship between concepts"""
        if properties is None:
            properties = {}
        
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        
        if source and target:
            edge = Edge(
                id=f"{source_id}_ISA_{target_id}",
                source=source,
                target=target,
                type="IS_A",
                properties=properties
            )
            return self.add_edge(edge)
        return None
    
    def define_has_property(self, concept_id: str, property_id: str, properties: Dict = None) -> Optional[Edge]:
        """Define a HAS_PROPERTY relationship"""
        if properties is None:
            properties = {}
        
        concept = self.get_node(concept_id)
        prop = self.get_node(property_id)
        
        if concept and prop:
            edge = Edge(
                id=f"{concept_id}_HAS_PROPERTY_{property_id}",
                source=concept,
                target=prop,
                type="HAS_PROPERTY",
                properties=properties
            )
            return self.add_edge(edge)
        return None
    
    def define_relationship(self, source_concept_id: str, relation_id: str, target_concept_id: str, 
                            properties: Dict = None) -> List[Edge]:
        """Define a relationship between concepts"""
        if properties is None:
            properties = {}
        
        source_concept = self.get_node(source_concept_id)
        relation = self.get_node(relation_id)
        target_concept = self.get_node(target_concept_id)
        
        if source_concept and relation and target_concept:
            source_edge = Edge(
                id=f"{source_concept_id}_DOMAIN_{relation_id}",
                source=source_concept,
                target=relation,
                type="DOMAIN",
                properties={}
            )
            
            target_edge = Edge(
                id=f"{relation_id}_RANGE_{target_concept_id}",
                source=relation,
                target=target_concept,
                type="RANGE",
                properties={}
            )
            
            self.add_edge(source_edge)
            self.add_edge(target_edge)
            return [source_edge, target_edge]
        return []
    
    def get_all_subconcepts(self, concept_id: str) -> List[Node]:
        """Get all subconcepts of a concept"""
        results = []
        concept = self.get_node(concept_id)
        if not concept:
            return results
        
        visited = set()
        queue = [concept]
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            
            visited.add(current.id)
            if current.id != concept_id:
                results.append(current)
            
            # Find all edges where current is the target of IS_A
            subconcept_edges = self.find_edges({
                "type": "IS_A",
                "target.id": current.id
            })
            
            for edge in subconcept_edges:
                queue.append(edge.source)
        
        return results
    
    def get_all_superconcepts(self, concept_id: str) -> List[Node]:
        """Get all superconcepts of a concept"""
        results = []
        concept = self.get_node(concept_id)
        if not concept:
            return results
        
        visited = set()
        queue = [concept]
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            
            visited.add(current.id)
            if current.id != concept_id:
                results.append(current)
            
            # Find all edges where current is the source of IS_A
            superconcept_edges = self.find_edges({
                "type": "IS_A",
                "source.id": current.id
            })
            
            for edge in superconcept_edges:
                queue.append(edge.target)
        
        return results


class InstanceGraph(Graph):
    """Graph for instance knowledge - concrete entities and their relationships"""
    
    def __init__(self, name: str):
        super().__init__(name)
        # Create indexes specific to instance graphs
        self.create_index("entity_type", "hash", ["node.properties.conceptId"])
        self.create_index("relation_index", "hash", ["edge.type"])
    
    def add_entity(self, id: str, concept_id: str, properties: Dict[str, Any]) -> Node:
        """Add an entity node to the graph"""
        props = properties.copy()
        props["conceptId"] = concept_id
        node = Node(id=id, type="Entity", properties=props)
        return self.add_node(node)
    
    def add_relation_instance(self, id: str, source_id: str, relation_type_id: str, 
                              target_id: str, properties: Dict = None) -> Optional[Edge]:
        """Add a relation between entities"""
        if properties is None:
            properties = {}
        
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        
        if source and target:
            props = properties.copy()
            props["relationTypeId"] = relation_type_id
            
            edge = Edge(
                id=id,
                source=source,
                target=target,
                type="RELATION",
                properties=props
            )
            return self.add_edge(edge)
        return None
    
    def get_entities_of_concept(self, concept_id: str) -> List[Node]:
        """Get all entities of a specific concept"""
        return self.find_nodes({"properties.conceptId": concept_id})
    
    def get_relations_of_type(self, relation_type_id: str) -> List[Edge]:
        """Get all relations of a specific type"""
        return self.find_edges({"properties.relationTypeId": relation_type_id})
    
    def get_relations_for_entity(self, entity_id: str, direction: str = "both") -> List[Edge]:
        """Get all relations for an entity"""
        return self.get_edges_for_node(entity_id, direction)


class ContextGraph(Graph):
    """Graph for context knowledge - situations, perspectives, conditions"""
    
    def __init__(self, name: str):
        super().__init__(name)
        # Create indexes specific to context graphs
        self.create_index("context_type", "hash", ["node.type"])
        self.create_index("context_hierarchy", "btree", ["edge.type"])
    
    def add_context(self, id: str, context_type: str, properties: Dict[str, Any]) -> Node:
        """Add a context node to the graph"""
        node = Node(id=id, type=context_type, properties=properties)
        return self.add_node(node)
    
    def add_temporal_context(self, id: str, start_time: Any, end_time: Any, properties: Dict = None) -> Node:
        """Add a temporal context"""
        if properties is None:
            properties = {}
        
        props = properties.copy()
        props["startTime"] = start_time
        props["endTime"] = end_time
        
        return self.add_context(id, "TemporalContext", props)
    
    def add_spatial_context(self, id: str, location: str, properties: Dict = None) -> Node:
        """Add a spatial context"""
        if properties is None:
            properties = {}
        
        props = properties.copy()
        props["location"] = location
        
        return self.add_context(id, "SpatialContext", props)
    
    def add_perspective_context(self, id: str, perspective: str, properties: Dict = None) -> Node:
        """Add a perspective context"""
        if properties is None:
            properties = {}
        
        props = properties.copy()
        props["perspective"] = perspective
        
        return self.add_context(id, "PerspectiveContext", props)
    
    def relate_contexts(self, source_id: str, target_id: str, relation_type: str, properties: Dict = None) -> Optional[Edge]:
        """Create a relationship between contexts"""
        if properties is None:
            properties = {}
        
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        
        if source and target:
            edge = Edge(
                id=f"{source_id}_{relation_type}_{target_id}",
                source=source,
                target=target,
                type=relation_type,
                properties=properties
            )
            return self.add_edge(edge)
        return None
    
    def refine_context(self, general_id: str, specific_id: str, properties: Dict = None) -> Optional[Edge]:
        """Create a refinement relationship between contexts"""
        return self.relate_contexts(specific_id, general_id, "REFINES", properties)
    
    def get_compatible_contexts(self, context_id: str) -> List[Node]:
        """Get all contexts compatible with the given context"""
        results = []
        context = self.get_node(context_id)
        if not context:
            return results
        
        # Find all contexts that are not incompatible with this one
        incompatible_edges = self.find_edges({
            "type": "INCOMPATIBLE_WITH",
            "source.id": context_id
        })
        
        incompatible_ids = {edge.target.id for edge in incompatible_edges}
        
        for node in self.nodes.values():
            if node.id != context_id and node.id not in incompatible_ids:
                results.append(node)
        
        return results


# =============================================================================
# 3. ADJUNCTION MECHANISM
# =============================================================================

class Adjunction:
    """Implements an adjunction between two graphs"""
    
    def __init__(self, name: str, source_tkg: Any, source_graph: Graph, target_graph: Graph,
                 left_mapping_function: Callable, right_mapping_function: Callable):
        self.name = name
        self.source_tkg = source_tkg
        self.source_graph = source_graph
        self.target_graph = target_graph
        self.left_mapping_function = left_mapping_function
        self.right_mapping_function = right_mapping_function
        
        # Cache for adjunction results
        self.left_cache: Dict[str, str] = {}
        self.right_cache: Dict[str, str] = {}
    
    def apply_left_adjoint(self, source_id: str) -> Optional[str]:
        """Apply the left adjoint functor to map from source to target"""
        if source_id in self.left_cache:
            return self.left_cache[source_id]
        
        source_node = self.source_graph.get_node(source_id)
        if not source_node:
            return None
        
        target_node = self.left_mapping_function(source_node, self.source_tkg)
        if target_node:
            self.left_cache[source_id] = target_node.id
            return target_node.id
        return None
    
    def apply_right_adjoint(self, target_id: str) -> Optional[str]:
        """Apply the right adjoint functor to map from target to source"""
        if target_id in self.right_cache:
            return self.right_cache[target_id]
        
        target_node = self.target_graph.get_node(target_id)
        if not target_node:
            return None
        
        source_node = self.right_mapping_function(target_node, self.source_tkg)
        if source_node:
            self.right_cache[target_id] = source_node.id
            return source_node.id
        return None
    
    def clear_cache(self) -> None:
        """Clear the adjunction caches"""
        self.left_cache = {}
        self.right_cache = {}


# =============================================================================
# 4. MAIN TKG SYSTEM
# =============================================================================

class TrinitarianKnowledgeGraph:
    """Main Trinitarian Knowledge Graph implementation"""
    
    def __init__(self, name: str):
        self.name = name
        
        # The three core graphs
        self.ontological_graph = OntologicalGraph("Ontological")
        self.instance_graph = InstanceGraph("Instance")
        self.context_graph = ContextGraph("Context")
        
        # Maps to store various structures
        self.adjunctions: Dict[str, Adjunction] = {}
    
    def initialize_adjunctions(self) -> None:
        """Initialize the predefined adjunctions between the three graphs"""
        # 1. Instantiation: Ontological → Instance
        self.adjunctions["instantiation"] = Adjunction(
            "instantiation",
            self,
            self.ontological_graph,
            self.instance_graph,
            self.instantiation_left_adjoint,
            self.instantiation_right_adjoint
        )
        
        # 2. Classification: Instance → Ontological
        self.adjunctions["classification"] = Adjunction(
            "classification",
            self,
            self.instance_graph,
            self.ontological_graph,
            self.classification_left_adjoint,
            self.classification_right_adjoint
        )
        
        # 3. Contextualization: Instance → Context
        self.adjunctions["contextualization"] = Adjunction(
            "contextualization",
            self,
            self.instance_graph,
            self.context_graph,
            self.contextualization_left_adjoint,
            self.contextualization_right_adjoint
        )
        
        # 4. Exemplification: Context → Instance
        self.adjunctions["exemplification"] = Adjunction(
            "exemplification",
            self,
            self.context_graph,
            self.instance_graph,
            self.exemplification_left_adjoint,
            self.exemplification_right_adjoint
        )
        
        # 5. Interpretation: Context → Ontological
        self.adjunctions["interpretation"] = Adjunction(
            "interpretation",
            self,
            self.context_graph,
            self.ontological_graph,
            self.interpretation_left_adjoint,
            self.interpretation_right_adjoint
        )
        
        # 6. Applicability: Ontological → Context
        self.adjunctions["applicability"] = Adjunction(
            "applicability",
            self,
            self.ontological_graph,
            self.context_graph,
            self.applicability_left_adjoint,
            self.applicability_right_adjoint
        )
    
    # Adjoint functor implementations
    
    def instantiation_left_adjoint(self, concept_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a concept to its instances"""
        # Find all entities in the instance graph with this concept ID
        instances = tkg.instance_graph.get_entities_of_concept(concept_node.id)
        
        # Return the first instance found (simplified for demo)
        if instances:
            return instances[0]
        return None
    
    def instantiation_right_adjoint(self, instance_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map an instance to its concept"""
        concept_id = instance_node.properties.get("conceptId")
        if concept_id:
            return tkg.ontological_graph.get_node(concept_id)
        return None
    
    def classification_left_adjoint(self, instance_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map an instance to its concept"""
        return tkg.instantiation_right_adjoint(instance_node, tkg)
    
    def classification_right_adjoint(self, concept_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a concept to a representative instance"""
        return tkg.instantiation_left_adjoint(concept_node, tkg)
    
    def contextualization_left_adjoint(self, instance_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map an instance to its relevant contexts"""
        relevant_contexts = []
        
        # If it's a temporal entity, find relevant temporal contexts
        if "timestamp" in instance_node.properties:
            timestamp = instance_node.properties["timestamp"]
            # Find contexts where startTime <= timestamp <= endTime
            temporal_contexts = tkg.context_graph.find_nodes({
                "type": "TemporalContext",
                "$and": [
                    {"properties.startTime": {"$lte": timestamp}},
                    {"properties.endTime": {"$gte": timestamp}}
                ]
            })
            relevant_contexts.extend(temporal_contexts)
        
        # If it has a location, find relevant spatial contexts
        if "location" in instance_node.properties:
            location = instance_node.properties["location"]
            spatial_contexts = tkg.context_graph.find_nodes({
                "type": "SpatialContext",
                "properties.location": location
            })
            relevant_contexts.extend(spatial_contexts)
        
        # Return the first relevant context (simplified for demo)
        if relevant_contexts:
            return relevant_contexts[0]
        return None
    
    def contextualization_right_adjoint(self, context_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a context to representative instances"""
        relevant_instances = []
        
        # Find instances relevant to this context based on its type
        if context_node.type == "SpatialContext" and "location" in context_node.properties:
            location = context_node.properties["location"]
            location_instances = tkg.instance_graph.find_nodes({
                "properties.location": location
            })
            relevant_instances.extend(location_instances)
        
        elif context_node.type == "TemporalContext" and "startTime" in context_node.properties and "endTime" in context_node.properties:
            start_time = context_node.properties["startTime"]
            end_time = context_node.properties["endTime"]
            time_instances = tkg.instance_graph.find_nodes({
                "$and": [
                    {"properties.timestamp": {"$gte": start_time}},
                    {"properties.timestamp": {"$lte": end_time}}
                ]
            })
            relevant_instances.extend(time_instances)
        
        # Return the first relevant instance (simplified for demo)
        if relevant_instances:
            return relevant_instances[0]
        return None
    
    def exemplification_left_adjoint(self, context_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a context to representative instances (Context → Instance)"""
        # Find the most representative instance for this context
        relevant_instances = []
        
        # Different logic depending on context type
        if context_node.type == "TemporalContext" and "startTime" in context_node.properties and "endTime" in context_node.properties:
            # For temporal contexts, find instances with timestamps in the middle of the period
            # (most representative of the time period)
            start_time = context_node.properties["startTime"]
            end_time = context_node.properties["endTime"]
            mid_time = (start_time + end_time) / 2
            
            # Find entities with timestamps close to the middle of the period
            all_instances = list(tkg.instance_graph.nodes.values())
            for instance in all_instances:
                if "timestamp" in instance.properties:
                    timestamp = instance.properties["timestamp"]
                    # Calculate how central this instance is to the time period
                    if start_time <= timestamp <= end_time:
                        # Add to relevant instances with a score based on centrality
                        distance_from_mid = abs(timestamp - mid_time)
                        range_halfwidth = (end_time - start_time) / 2
                        centrality = 1.0 - (distance_from_mid / range_halfwidth)
                        relevant_instances.append((instance, centrality))
        
        elif context_node.type == "SpatialContext" and "location" in context_node.properties:
            # For spatial contexts, find instances in that location
            location = context_node.properties["location"]
            all_instances = list(tkg.instance_graph.nodes.values())
            for instance in all_instances:
                if instance.properties.get("location") == location:
                    # All matching instances are equally relevant for spatial contexts
                    relevant_instances.append((instance, 1.0))
        
        # Sort by relevance score and take the most relevant
        relevant_instances.sort(key=lambda x: x[1], reverse=True)
        if relevant_instances:
            return relevant_instances[0][0]
        
        return None

    def exemplification_right_adjoint(self, instance_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map an instance to contexts it exemplifies (Instance → Context)"""
        # Find contexts that this instance exemplifies - typically the most specific
        # applicable context where this instance is particularly representative
        relevant_contexts = []
        
        # Check for temporal relevance
        if "timestamp" in instance_node.properties:
            timestamp = instance_node.properties["timestamp"]
            temporal_contexts = tkg.context_graph.get_nodes_of_type("TemporalContext")
            
            for context in temporal_contexts:
                if "startTime" in context.properties and "endTime" in context.properties:
                    start_time = context.properties["startTime"]
                    end_time = context.properties["endTime"]
                    
                    if start_time <= timestamp <= end_time:
                        # Calculate how representative this instance is for the context
                        # (smaller time periods where instance is more central get higher scores)
                        period_width = end_time - start_time
                        mid_time = (start_time + end_time) / 2
                        distance_from_mid = abs(timestamp - mid_time)
                        
                        # Instances closer to the middle of narrower periods are more representative
                        if period_width > 0:
                            specificity = 1.0 / period_width
                            centrality = 1.0 - (distance_from_mid / (period_width / 2))
                            score = specificity * centrality
                            relevant_contexts.append((context, score))
        
        # Check for spatial relevance
        if "location" in instance_node.properties:
            location = instance_node.properties["location"]
            spatial_contexts = tkg.context_graph.get_nodes_of_type("SpatialContext")
            
            for context in spatial_contexts:
                if context.properties.get("location") == location:
                    # For spatial contexts, use any additional properties to determine
                    # how representative this instance is for the context
                    # (for now, just use a default score)
                    relevant_contexts.append((context, 0.8))
        
        # Sort by relevance score and take the most relevant
        relevant_contexts.sort(key=lambda x: x[1], reverse=True)
        if relevant_contexts:
            return relevant_contexts[0][0]
        
        return None
    
    def interpretation_left_adjoint(self, context_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a context to ontological concepts that are relevant in this context"""
        # Simplified implementation for demo
        if context_node.type == "TemporalContext":
            # Find a concept related to temporality
            temporal_concepts = tkg.ontological_graph.find_nodes({
                "type": "Concept",
                "properties.temporal": True
            })
            if temporal_concepts:
                return temporal_concepts[0]
        
        elif context_node.type == "SpatialContext":
            # Find a concept related to spatiality
            spatial_concepts = tkg.ontological_graph.find_nodes({
                "type": "Concept",
                "properties.spatial": True
            })
            if spatial_concepts:
                return spatial_concepts[0]
        
        # Default: return any concept (simplified for demo)
        all_concepts = tkg.ontological_graph.get_nodes_of_type("Concept")
        if all_concepts:
            return all_concepts[0]
        
        return None
    
    def interpretation_right_adjoint(self, concept_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a concept to contexts where it's most relevant"""
        relevant_contexts = []
        
        # Check if concept has temporal or spatial attributes
        if concept_node.properties.get("temporal"):
            temporal_contexts = tkg.context_graph.get_nodes_of_type("TemporalContext")
            relevant_contexts.extend(temporal_contexts)
        
        if concept_node.properties.get("spatial"):
            spatial_contexts = tkg.context_graph.get_nodes_of_type("SpatialContext")
            relevant_contexts.extend(spatial_contexts)
        
        # If no specific relevance found, return any context
        if not relevant_contexts:
            all_contexts = list(tkg.context_graph.nodes.values())
            if all_contexts:
                return all_contexts[0]
        elif relevant_contexts:
            return relevant_contexts[0]
        
        return None
    
    def applicability_left_adjoint(self, concept_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a concept to contexts where it applies"""
        return tkg.interpretation_right_adjoint(concept_node, tkg)
    
    def applicability_right_adjoint(self, context_node: Node, tkg: 'TrinitarianKnowledgeGraph') -> Optional[Node]:
        """Map a context to concepts it applies to"""
        return tkg.interpretation_left_adjoint(context_node, tkg)
    
    def clear_adjunction_caches(self) -> None:
        """Clear all adjunction caches"""
        for adjunction in self.adjunctions.values():
            adjunction.clear_cache()
    
    # Context-aware operations
    
    def is_concept_applicable_in_context(self, concept_id: str, context_id: str) -> bool:
        """Check if a concept is applicable in a given context"""
        context_node = self.context_graph.get_node(context_id)
        concept_node = self.ontological_graph.get_node(concept_id)
        
        if not context_node or not concept_node:
            return False
        
        # Use both directions of the adjunction to check compatibility
        mapped_context_id = self.adjunctions["applicability"].apply_left_adjoint(concept_id)
        if mapped_context_id:
            mapped_context = self.context_graph.get_node(mapped_context_id)
            if mapped_context and self.contexts_are_compatible(mapped_context, context_node):
                return True
        
        mapped_concept_id = self.adjunctions["interpretation"].apply_left_adjoint(context_id)
        if mapped_concept_id:
            mapped_concept = self.ontological_graph.get_node(mapped_concept_id)
            if mapped_concept and self.concepts_are_compatible(mapped_concept, concept_node):
                return True
        
        # Simplified fallback logic for demo
        # Temporal concepts apply in temporal contexts, etc.
        if (concept_node.properties.get("temporal") and context_node.type == "TemporalContext" or
            concept_node.properties.get("spatial") and context_node.type == "SpatialContext"):
            return True
        
        return False
    
    def is_instance_relevant_in_context(self, instance_id: str, context_id: str) -> bool:
        """Check if an instance is relevant in a given context"""
        instance_node = self.instance_graph.get_node(instance_id)
        context_node = self.context_graph.get_node(context_id)
        
        if not instance_node or not context_node:
            return False
        
        # Check temporal relevance
        if context_node.type == "TemporalContext" and "timestamp" in instance_node.properties:
            start_time = context_node.properties.get("startTime")
            end_time = context_node.properties.get("endTime")
            timestamp = instance_node.properties["timestamp"]
            
            if start_time <= timestamp <= end_time:
                return True
        
        # Check spatial relevance
        elif context_node.type == "SpatialContext" and "location" in instance_node.properties:
            if instance_node.properties["location"] == context_node.properties.get("location"):
                return True
        
        # Check perspective relevance
        elif context_node.type == "PerspectiveContext" and "perspective" in instance_node.properties:
            if instance_node.properties["perspective"] == context_node.properties.get("perspective"):
                return True
        
        # Use adjunctions for more complex cases
        mapped_context_id = self.adjunctions["contextualization"].apply_left_adjoint(instance_id)
        if mapped_context_id:
            mapped_context = self.context_graph.get_node(mapped_context_id)
            if mapped_context and self.contexts_are_compatible(mapped_context, context_node):
                return True
        
        mapped_instance_id = self.adjunctions["exemplification"].apply_left_adjoint(context_id)
        if mapped_instance_id:
            mapped_instance = self.instance_graph.get_node(mapped_instance_id)
            if mapped_instance and self.instances_are_related(mapped_instance, instance_node):
                return True
        
        return False
    
    def contexts_are_compatible(self, context1: Node, context2: Node) -> bool:
        """Check if two contexts are compatible"""
        # Check for direct incompatibility
        incompatible_edges = self.context_graph.find_edges({
            "type": "INCOMPATIBLE_WITH",
            "source.id": context1.id,
            "target.id": context2.id
        })
        
        if incompatible_edges:
            return False
        
        # Check if one refines the other
        refines_edges = self.context_graph.find_edges({
            "type": "REFINES",
            "source.id": context1.id,
            "target.id": context2.id
        })
        
        if refines_edges:
            return True
        
        refines_edges = self.context_graph.find_edges({
            "type": "REFINES",
            "source.id": context2.id,
            "target.id": context1.id
        })
        
        if refines_edges:
            return True
        
        # Default compatibility for different types of contexts
        if context1.type != context2.type:
            return True
        
        # For same type contexts, check overlap
        if context1.type == "TemporalContext" and context2.type == "TemporalContext":
            start1 = context1.properties.get("startTime")
            end1 = context1.properties.get("endTime")
            start2 = context2.properties.get("startTime")
            end2 = context2.properties.get("endTime")
            
            if start1 is not None and end1 is not None and start2 is not None and end2 is not None:
                # Check for overlap
                return not (end1 < start2 or end2 < start1)
        
        elif context1.type == "SpatialContext" and context2.type == "SpatialContext":
            # Simplified spatial check - just check if locations match
            return context1.properties.get("location") == context2.properties.get("location")
        
        # Default to compatible
        return True
    
    def concepts_are_compatible(self, concept1: Node, concept2: Node) -> bool:
        """Check if two concepts are compatible"""
        # Check if one is a subconcept of the other
        is_a_edges = self.ontological_graph.find_edges({
            "type": "IS_A",
            "source.id": concept1.id,
            "target.id": concept2.id
        })
        
        if is_a_edges:
            return True
        
        is_a_edges = self.ontological_graph.find_edges({
            "type": "IS_A",
            "source.id": concept2.id,
            "target.id": concept1.id
        })
        
        if is_a_edges:
            return True
        
        # For demo purposes, consider all concepts compatible unless explicitly stated otherwise
        return True
    
    def instances_are_related(self, instance1: Node, instance2: Node) -> bool:
        """Check if two instances are related"""
        # Check if they're of the same concept
        if instance1.properties.get("conceptId") == instance2.properties.get("conceptId"):
            return True
        
        # Check if they're connected by a relation
        relations = self.instance_graph.find_edges({
            "source.id": instance1.id,
            "target.id": instance2.id
        })
        
        if relations:
            return True
        
        relations = self.instance_graph.find_edges({
            "source.id": instance2.id,
            "target.id": instance1.id
        })
        
        if relations:
            return True
        
        # For demo purposes, consider instances related if they share properties
        for key, value in instance1.properties.items():
            if key in instance2.properties and instance2.properties[key] == value:
                return True
        
        return False
    
    def find_across_graphs(self, start_graph: str, start_node_id: str, traversal_plan: List[Dict]) -> List[Dict]:
        """Traverse across graphs following a sequence of adjunctions"""
        result = []
        
        # Set the starting point
        if start_graph == "ontological":
            current_graph = self.ontological_graph
        elif start_graph == "instance":
            current_graph = self.instance_graph
        elif start_graph == "context":
            current_graph = self.context_graph
        else:
            raise ValueError(f"Unknown graph: {start_graph}")
        
        current_node_id = start_node_id
        
        # Add the starting node to results
        start_node = current_graph.get_node(current_node_id)
        if not start_node:
            return []
        
        result.append({
            "graph": start_graph,
            "nodeId": current_node_id,
            "node": start_node
        })
        
        # Perform the traversal
        for step in traversal_plan:
            adjunction_name = step.get("adjunction")
            direction = step.get("direction")
            
            if adjunction_name not in self.adjunctions:
                raise ValueError(f"Adjunction {adjunction_name} not found")
            
            adjunction = self.adjunctions[adjunction_name]
            
            # Apply the appropriate direction of the adjunction
            if current_graph == adjunction.source_graph and direction == "left":
                current_node_id = adjunction.apply_left_adjoint(current_node_id)
                current_graph = adjunction.target_graph
                graph_name = "ontological" if current_graph == self.ontological_graph else \
                            "instance" if current_graph == self.instance_graph else "context"
            elif current_graph == adjunction.target_graph and direction == "right":
                current_node_id = adjunction.apply_right_adjoint(current_node_id)
                current_graph = adjunction.source_graph
                graph_name = "ontological" if current_graph == self.ontological_graph else \
                            "instance" if current_graph == self.instance_graph else "context"
            else:
                raise ValueError(f"Invalid direction {direction} for current graph")
            
            if not current_node_id:
                # No mapping found
                break
            
            # Add the current node to results
            current_node = current_graph.get_node(current_node_id)
            result.append({
                "graph": graph_name,
                "nodeId": current_node_id,
                "node": current_node
            })
        
        return result
    
    def contextual_query(self, query_string: str, context_id: str = None) -> Dict[str, Any]:
        """Execute a query with context awareness"""
        # Parse the query
        parsed_query = self.parse_query(query_string)
        
        if not parsed_query:
            return {"status": "error", "message": "Failed to parse query", "results": []}
        
        context = None
        if context_id:
            context = self.context_graph.get_node(context_id)
            if not context:
                return {"status": "error", "message": f"Context {context_id} not found", "results": []}
        
        if parsed_query["type"] == "concept_instances":
            concept_id = parsed_query["conceptId"]
            
            # Check if concept exists
            concept = self.ontological_graph.get_node(concept_id)
            if not concept:
                return {"status": "error", "message": f"Concept {concept_id} not found", "results": []}
            
            # If context specified, check if concept is applicable
            if context and not self.is_concept_applicable_in_context(concept_id, context_id):
                return {
                    "status": "inapplicable",
                    "message": f"Concept {concept_id} is not applicable in context {context_id}",
                    "results": []
                }
            
            # Get instances of the concept
            instances = self.instance_graph.get_entities_of_concept(concept_id)
            
            # Filter by context relevance if context specified
            if context:
                relevant_instances = [
                    instance for instance in instances
                    if self.is_instance_relevant_in_context(instance.id, context_id)
                ]
            else:
                relevant_instances = instances
            
            return {
                "status": "success",
                "concept": concept,
                "context": context,
                "results": relevant_instances,
                "count": len(relevant_instances)
            }
        
        elif parsed_query["type"] == "relation_query":
            relation_type_id = parsed_query["relationTypeId"]
            
            # Check if relation type exists
            relation = self.ontological_graph.get_node(relation_type_id)
            if not relation:
                return {"status": "error", "message": f"Relation type {relation_type_id} not found", "results": []}
            
            # If context specified, check if relation is applicable
            if context and not self.is_concept_applicable_in_context(relation_type_id, context_id):
                return {
                    "status": "inapplicable",
                    "message": f"Relation {relation_type_id} is not applicable in context {context_id}",
                    "results": []
                }
            
            # Get relations of this type
            relations = self.instance_graph.get_relations_of_type(relation_type_id)
            
            # Filter by context if specified
            if context:
                relevant_relations = []
                for relation in relations:
                    # A relation is relevant if both its source and target are relevant
                    if (self.is_instance_relevant_in_context(relation.source.id, context_id) and
                        self.is_instance_relevant_in_context(relation.target.id, context_id)):
                        relevant_relations.append(relation)
            else:
                relevant_relations = relations
            
            return {
                "status": "success",
                "relation": relation,
                "context": context,
                "results": relevant_relations,
                "count": len(relevant_relations)
            }
        
        return {"status": "error", "message": "Unsupported query type", "results": []}
    
    def parse_query(self, query_string: str) -> Optional[Dict]:
        """Parse a query string into a structured query object"""
        # Simple pattern matching for demo purposes
        # In a real implementation, this would be much more sophisticated
        
        # Pattern: "FIND INSTANCES OF CONCEPT X [IN CONTEXT Y]"
        concept_pattern = r"FIND\s+INSTANCES\s+OF\s+CONCEPT\s+(\w+)(?:\s+IN\s+CONTEXT\s+(\w+))?"
        match = re.match(concept_pattern, query_string, re.IGNORECASE)
        
        if match:
            concept_id = match.group(1)
            context_id = match.group(2)
            return {
                "type": "concept_instances",
                "conceptId": concept_id,
                "contextId": context_id
            }
        
        # Pattern: "FIND RELATIONS OF TYPE X [IN CONTEXT Y]"
        relation_pattern = r"FIND\s+RELATIONS\s+OF\s+TYPE\s+(\w+)(?:\s+IN\s+CONTEXT\s+(\w+))?"
        match = re.match(relation_pattern, query_string, re.IGNORECASE)
        
        if match:
            relation_type_id = match.group(1)
            context_id = match.group(2)
            return {
                "type": "relation_query",
                "relationTypeId": relation_type_id,
                "contextId": context_id
            }
        
        return None


# =============================================================================
# 5. TKG API and Integration
# =============================================================================

class TKGApi:
    """API layer for the Trinitarian Knowledge Graph"""
    
    def __init__(self, tkg: TrinitarianKnowledgeGraph):
        self.tkg = tkg
    
    def create_ontological_concept(self, id: str, properties: Dict, parent_concepts: List[str] = None) -> Node:
        """Create a concept in the ontological graph"""
        concept = self.tkg.ontological_graph.add_concept(id, properties)
        
        if parent_concepts:
            for parent_id in parent_concepts:
                self.tkg.ontological_graph.define_is_a(id, parent_id)
        
        return concept
    
    def create_context(self, id: str, context_type: str, properties: Dict) -> Node:
        """Create a context in the context graph"""
        if context_type == "temporal":
            return self.tkg.context_graph.add_temporal_context(
                id,
                properties.get("startTime"),
                properties.get("endTime"),
                properties
            )
        elif context_type == "spatial":
            return self.tkg.context_graph.add_spatial_context(
                id,
                properties.get("location"),
                properties
            )
        elif context_type == "perspective":
            return self.tkg.context_graph.add_perspective_context(
                id,
                properties.get("perspective"),
                properties
            )
        else:
            return self.tkg.context_graph.add_context(id, context_type, properties)
    
    def create_entity(self, id: str, concept_id: str, properties: Dict) -> Node:
        """Create an entity in the instance graph"""
        return self.tkg.instance_graph.add_entity(id, concept_id, properties)
    
    def create_relation(self, id: str, source_id: str, relation_type_id: str, target_id: str, properties: Dict = None) -> Edge:
        """Create a relation between entities"""
        if properties is None:
            properties = {}
        
        return self.tkg.instance_graph.add_relation_instance(
            id, source_id, relation_type_id, target_id, properties
        )
    
    def query(self, query_string: str, context_id: str = None) -> Dict:
        """Execute a query with optional context"""
        return self.tkg.contextual_query(query_string, context_id)
    
    def get_entity(self, id: str) -> Optional[Node]:
        """Get an entity by ID"""
        return self.tkg.instance_graph.get_node(id)
    
    def get_concept(self, id: str) -> Optional[Node]:
        """Get a concept by ID"""
        return self.tkg.ontological_graph.get_node(id)
    
    def get_context(self, id: str) -> Optional[Node]:
        """Get a context by ID"""
        return self.tkg.context_graph.get_node(id)
    
    def get_entities_of_concept(self, concept_id: str, context_id: str = None) -> List[Node]:
        """Get all entities of a concept, optionally filtered by context"""
        entities = self.tkg.instance_graph.get_entities_of_concept(concept_id)
        
        if context_id:
            return [
                entity for entity in entities
                if self.tkg.is_instance_relevant_in_context(entity.id, context_id)
            ]
        
        return entities
    
    def export_knowledge(self, format: str = "json") -> Any:
        """Export all knowledge in the specified format"""
        export_data = {
            "ontological": {
                "concepts": [node.to_dict() for node in self.tkg.ontological_graph.get_nodes_of_type("Concept")],
                "relations": [node.to_dict() for node in self.tkg.ontological_graph.get_nodes_of_type("Relation")],
                "properties": [node.to_dict() for node in self.tkg.ontological_graph.get_nodes_of_type("Property")],
                "edges": [edge.to_dict() for edge in self.tkg.ontological_graph.edges.values()]
            },
            "instance": {
                "entities": [node.to_dict() for node in self.tkg.instance_graph.nodes.values()],
                "relations": [edge.to_dict() for edge in self.tkg.instance_graph.edges.values()]
            },
            "context": {
                "contexts": [node.to_dict() for node in self.tkg.context_graph.nodes.values()],
                "relations": [edge.to_dict() for edge in self.tkg.context_graph.edges.values()]
            }
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            return export_data


# =============================================================================
# 6. EXAMPLE USAGE
# =============================================================================

def example_tkg_usage():
    """Demonstrate the Trinitarian Knowledge Graph with a simple example"""
    print("Creating Trinitarian Knowledge Graph...")
    tkg = TrinitarianKnowledgeGraph("ExampleTKG")
    tkg.initialize_adjunctions()
    
    # Create an API interface
    api = TKGApi(tkg)
    
    print("\n1. Adding ontological knowledge...")
    # Add concepts
    api.create_ontological_concept("Person", {
        "name": "Person",
        "description": "A human being",
        "temporal": True,   # Relevant in temporal contexts
        "spatial": True     # Relevant in spatial contexts
    })
    
    api.create_ontological_concept("Author", {
        "name": "Author",
        "description": "Someone who writes books",
        "temporal": True
    }, ["Person"])
    
    api.create_ontological_concept("Book", {
        "name": "Book",
        "description": "A written work",
        "temporal": True
    })
    
    # Create a relation type
    api.create_ontological_concept("wrote", {
        "name": "wrote",
        "description": "Author wrote a book",
        "temporal": True
    })
    
    # Define relationship
    tkg.ontological_graph.define_relationship("Author", "wrote", "Book")
    
    print("\n2. Adding contextual knowledge...")
    # Add contexts
    api.create_context("medieval", "TemporalContext", {
        "startTime": 500,
        "endTime": 1500,
        "description": "Medieval period"
    })
    
    api.create_context("renaissance", "TemporalContext", {
        "startTime": 1300,
        "endTime": 1600,
        "description": "Renaissance period"
    })
    
    api.create_context("modern", "TemporalContext", {
        "startTime": 1500,
        "endTime": 2000,
        "description": "Modern period"
    })
    
    api.create_context("contemporary", "TemporalContext", {
        "startTime": 1900,
        "endTime": 2100,
        "description": "Contemporary period"
    })
    
    api.create_context("europe", "SpatialContext", {
        "location": "Europe",
        "description": "European continent"
    })
    
    api.create_context("america", "SpatialContext", {
        "location": "America",
        "description": "American continent"
    })
    
    # Create context relationships
    tkg.context_graph.refine_context("medieval", "renaissance", {
        "description": "Renaissance refines Medieval"
    })
    
    tkg.context_graph.relate_contexts("medieval", "contemporary", "INCOMPATIBLE_WITH", {
        "description": "Medieval and Contemporary are incompatible"
    })
    
    print("\n3. Adding instance knowledge...")
    # Add authors
    api.create_entity("shakespeare", "Author", {
        "name": "William Shakespeare",
        "birthYear": 1564,
        "deathYear": 1616,
        "location": "Europe",
        "timestamp": 1600  # Representative time for Shakespeare
    })
    
    api.create_entity("cervantes", "Author", {
        "name": "Miguel de Cervantes",
        "birthYear": 1547,
        "deathYear": 1616,
        "location": "Europe",
        "timestamp": 1605  # Representative time for Cervantes
    })
    
    api.create_entity("hemingway", "Author", {
        "name": "Ernest Hemingway",
        "birthYear": 1899,
        "deathYear": 1961,
        "location": "America",
        "timestamp": 1940  # Representative time for Hemingway
    })
    
    # Add books
    api.create_entity("hamlet", "Book", {
        "title": "Hamlet",
        "publicationYear": 1600,
        "location": "Europe",
        "timestamp": 1600
    })
    
    api.create_entity("don_quixote", "Book", {
        "title": "Don Quixote",
        "publicationYear": 1605,
        "location": "Europe",
        "timestamp": 1605
    })
    
    api.create_entity("old_man", "Book", {
        "title": "The Old Man and the Sea",
        "publicationYear": 1952,
        "location": "America",
        "timestamp": 1952
    })
    
    # Create relationships
    api.create_relation(
        "shakespeare_wrote_hamlet",
        "shakespeare",
        "wrote",
        "hamlet",
        {"year": 1600}
    )
    
    api.create_relation(
        "cervantes_wrote_quixote",
        "cervantes",
        "wrote",
        "don_quixote",
        {"year": 1605}
    )
    
    api.create_relation(
        "hemingway_wrote_oldman",
        "hemingway",
        "wrote",
        "old_man",
        {"year": 1952}
    )
    
    print("\n4. Querying with context awareness...")
    # Query for authors in different contexts
    print("\nAuthors in Renaissance period:")
    results = api.query("FIND INSTANCES OF CONCEPT Author IN CONTEXT renaissance")
    for entity in results["results"]:
        print(f"  - {entity.properties.get('name')}")
    
    print("\nAuthors in Contemporary period:")
    results = api.query("FIND INSTANCES OF CONCEPT Author IN CONTEXT contemporary")
    for entity in results["results"]:
        print(f"  - {entity.properties.get('name')}")
    
    print("\nAuthors in Europe:")
    results = api.query("FIND INSTANCES OF CONCEPT Author IN CONTEXT europe")
    for entity in results["results"]:
        print(f"  - {entity.properties.get('name')}")
    
    print("\nAuthors in America:")
    results = api.query("FIND INSTANCES OF CONCEPT Author IN CONTEXT america")
    for entity in results["results"]:
        print(f"  - {entity.properties.get('name')}")
    
    print("\n5. Traversing across graphs using adjunctions...")
    # Find the context for a book
    book_id = "hamlet"
    traversal_plan = [
        {"adjunction": "classification", "direction": "left"},  # Entity → Concept
        {"adjunction": "applicability", "direction": "left"}   # Concept → Context
    ]
    
    results = tkg.find_across_graphs("instance", book_id, traversal_plan)
    
    print(f"\nTraversal from book '{book_id}':")
    for step in results:
        if step["graph"] == "instance":
            print(f"  Entity: {step['node'].properties.get('title')}")
        elif step["graph"] == "ontological":
            print(f"  Concept: {step['node'].properties.get('name')}")
        elif step["graph"] == "context":
            print(f"  Context: {step['node'].properties.get('description')}")
    
    print("\n6. Checking context-specific applicability...")
    # Check if concepts are applicable in contexts
    print("\nConcept applicability in contexts:")
    for concept_id in ["Person", "Author", "Book"]:
        for context_id in ["medieval", "renaissance", "modern", "contemporary"]:
            applicable = tkg.is_concept_applicable_in_context(concept_id, context_id)
            print(f"  - '{concept_id}' applicable in '{context_id}': {applicable}")
    
    print("\n7. Examining entity relevance in contexts...")
    # Check if instances are relevant in contexts
    print("\nEntity relevance in contexts:")
    entities = [
        ("Shakespeare", "shakespeare"),
        ("Cervantes", "cervantes"),
        ("Hemingway", "hemingway")
    ]
    
    contexts = [
        ("Medieval", "medieval"),
        ("Renaissance", "renaissance"),
        ("Modern", "modern"),
        ("Contemporary", "contemporary")
    ]
    
    for entity_name, entity_id in entities:
        print(f"\n  {entity_name} relevance:")
        for context_name, context_id in contexts:
            relevant = tkg.is_instance_relevant_in_context(entity_id, context_id)
            print(f"    - In {context_name}: {relevant}")
    
    print("\nTrinitarian Knowledge Graph demonstration completed.")
    return tkg, api


if __name__ == "__main__":
    tkg, api = example_tkg_usage()
