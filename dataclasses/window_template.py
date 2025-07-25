"""
Pydantic-based Window template for generating Brick schema YAML templates.

This module provides a flexible Pydantic model that can generate YAML templates
for window entities following the Brick schema with minimal hardcoding.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import yaml


class TemplateDependency(BaseModel):
    """Represents a template dependency with arguments."""
    template: str
    args: Dict[str, str]


class BrickProperty(BaseModel):
    """Represents a Brick property with its parameter name."""
    name: str
    param_name: str


class BrickTemplate(BaseModel):
    """Base Pydantic model for Brick schema templates."""
    name: str
    brick_type: str
    prefixes: Dict[str, str] = Field(default_factory=dict)
    properties: List[BrickProperty] = Field(default_factory=list)
    dependencies: List[TemplateDependency] = Field(default_factory=list)
    optional: List[str] = Field(default_factory=list)
    
    def generate_body(self) -> str:
        """Generate the RDF/Turtle body from the template configuration."""
        # Generate prefix declarations
        prefix_lines = []
        for prefix, uri in self.prefixes.items():
            prefix_lines.append(f"@prefix {prefix}: <{uri}> .")
        
        # Generate main declaration
        main_line = f"p:name a {self.brick_type}"
        
        # Generate property lines
        property_lines = []
        for prop in self.properties:
            property_lines.append(f"    {prop.name} p:{prop.param_name}")
        
        # Combine all parts
        body_parts = prefix_lines + [main_line]
        if property_lines:
            body_parts[-1] += " ;"
            body_parts.extend(property_lines[:-1])
            body_parts.append(property_lines[-1] + " .")
        else:
            body_parts[-1] += " ."
        
        return "\n".join(body_parts)
    
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
    
    def to_yaml(self) -> str:
        """Generate YAML representation of the template."""
        template_dict = {self.name: self.to_dict()}
        return yaml.dump(template_dict, default_flow_style=False, sort_keys=False)


class WindowTemplate(BrickTemplate):
    """Pydantic model for Window Brick schema templates."""
    
    def __init__(self, **data):
        # Set default values for window template
        defaults = {
            "name": "window",
            "brick_type": "brick:Window",
            "prefixes": {
                "p": "urn:___param___#",
                "brick": "https://brickschema.org/schema/Brick#",
                "qudt": "http://qudt.org/schema/qudt/"
            },
            "properties": [
                BrickProperty(name="brick:area", param_name="area_name"),
                BrickProperty(name="brick:azimuth", param_name="azimuth_name"),
                BrickProperty(name="brick:tilt", param_name="tilt_name")
            ],
            "dependencies": [
                TemplateDependency(
                    template="area",
                    args={"name": "area_name", "value": "area_value", "unit": "area_unit"}
                ),
                TemplateDependency(
                    template="azimuth",
                    args={"name": "azimuth_name", "value": "azimuth_value"}
                ),
                TemplateDependency(
                    template="tilt",
                    args={"name": "tilt_name", "value": "tilt_value"}
                )
            ]
        }
        
        # Merge user data with defaults
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        
        super().__init__(**data)
    
    def add_property(self, brick_property: str, param_name: str, 
                    dependency_template: Optional[str] = None, 
                    dependency_args: Optional[Dict[str, str]] = None):
        """Add a new property to the window template."""
        self.properties.append(BrickProperty(name=brick_property, param_name=param_name))
        
        if dependency_template and dependency_args:
            self.dependencies.append(
                TemplateDependency(template=dependency_template, args=dependency_args)
            )
    
    def remove_property(self, brick_property: str):
        """Remove a property from the window template."""
        self.properties = [p for p in self.properties if p.name != brick_property]
    
    def save_yaml(self, filepath: str):
        """Save the window template as a YAML file."""
        with open(filepath, 'w') as f:
            f.write(self.to_yaml())


# Factory function for creating different window types
def create_window_template(window_type: str = "standard") -> WindowTemplate:
    """Factory function to create different types of window templates."""
    
    if window_type == "simple":
        # Simple window with just area
        return WindowTemplate(
            properties=[
                BrickProperty(name="brick:area", param_name="area_name")
            ],
            dependencies=[
                TemplateDependency(
                    template="area",
                    args={"name": "area_name", "value": "area_value", "unit": "area_unit"}
                )
            ]
        )
    
    elif window_type == "detailed":
        # Detailed window with additional properties
        window = WindowTemplate()
        window.add_property(
            "brick:glazingType", 
            "glazing_type_name",
            "glazing_type",
            {"name": "glazing_type_name", "value": "glazing_type_value"}
        )
        return window
    
    else:  # standard
        return WindowTemplate()


# Example usage and testing
if __name__ == "__main__":
    # Create standard window template
    window = WindowTemplate()
    
    print("Standard Window template YAML:")
    print(window.to_yaml())
    
    # Create simple window template
    simple_window = create_window_template("simple")
    print("\nSimple Window template YAML:")
    print(simple_window.to_yaml())
    
    # Create custom window template
    custom_window = WindowTemplate(
        name="custom_window",
        properties=[
            BrickProperty(name="brick:area", param_name="window_area"),
            BrickProperty(name="brick:orientation", param_name="window_orientation")
        ],
        dependencies=[
            TemplateDependency(
                template="area",
                args={"name": "window_area", "value": "area_val", "unit": "m2"}
            ),
            TemplateDependency(
                template="orientation",
                args={"name": "window_orientation", "value": "orientation_val"}
            )
        ]
    )
    
    print("\nCustom Window template YAML:")
    print(custom_window.to_yaml())
    
    # Demonstrate adding properties dynamically
    window.add_property(
        "brick:transmittance", 
        "transmittance_name",
        "transmittance",
        {"name": "transmittance_name", "value": "transmittance_value"}
    )
    
    print("\nWindow with added transmittance property:")
    print(window.to_yaml())
