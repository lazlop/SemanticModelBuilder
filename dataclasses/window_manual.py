#%%
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional, Type
from rdflib import Graph, Namespace, Literal
from semantic_mpc_interface.namespaces import BRICK, HPF, QUDT, QK, UNIT, PARAM
import yaml

class Dependency(BaseModel):
    """Represents a template dependency with arguments."""
    template: str
    args: Dict[str, str]

class Entity(BaseModel):
    """Base Pydantic model for Brick schema templates."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    name: str
    ns: Optional[Namespace] = HPF
    graph: Graph = Graph()

    def to_rdf(self):
        pass 


class Template(Entity):
    """Base Pydantic model for Brick schema templates."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    dependencies: List[Dependency] = Field(default_factory=list)
    optional: List[str] = Field(default_factory=list)
    entity: Type[Entity]
    
    def generate_body(self) -> str:
        """Generate the RDF/Turtle body from the template configuration."""
        # Generate prefix declarations
        params = self.entity.model_fields['params'].default
        for param in params:
            setattr(self.entity, param, PARAM[param])
        
        body = self.entity.to_rdf().serialize(format='ttl')
        return body
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary format for YAML export."""
        result = {
            "body": self.generate_body()
        }
        
        if self.optional:
            result["optional"] = self.optional
            
        if self.dependencies:
            result["dependencies"] = [
                {"template": dep.template, "args": dep.args}
                for dep in self.dependencies
            ]
            
        return result
    
    def to_template(self) -> str:
        """Generate YAML representation of the template."""
        template_dict = {self.name: self.to_dict()}
        return yaml.dump(template_dict, default_flow_style=False, sort_keys=False)

class Value(Entity):
    pred: str = Field()
    value: float = Field()
    unit: str = Field()
    quantitykind: str = Field()
    params: List = ['name','value','unit','quantitykind']
    # def __init__(self):
    #     super().__init__()
    def to_rdf(self):
        self.graph.add((self.ns['name'], BRICK[self.pred], Literal(self.value)))
        self.graph.add((self.ns['name'], QUDT.hasUnit, UNIT[self.unit]))
        self.graph.add((self.ns['name'], QUDT.hasQuantityKind, QK[self.quantitykind]))
        return self.graph

class Area(Value):
    unit: str = Field(default='FT2')
    quantitykind: str = Field(default='Area')
    params: List = ['name','value','unit']
    def __init__(self,  **data):
        data.setdefault('unit', 'FT2')  # Square feet for Imperial
        data.setdefault('quantitykind', 'Area')
        data.setdefault('pred','area')
        super().__init__(**data)


class Window(Entity)

a = Area(name = 'a1', value = 3)
print(a.to_rdf().serialize(format = 'ttl'))
t = Template(name = 'area', entity = Area)
t.to_template()
# %%

