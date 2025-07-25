"""
Test script for the WindowTemplate Pydantic model.
"""

from window_template import WindowTemplate, create_window_template

def test_window_template():
    """Test the WindowTemplate functionality."""
    
    print("=== Testing WindowTemplate ===\n")
    
    # Test 1: Standard window template
    print("1. Standard Window Template:")
    window = WindowTemplate()
    yaml_output = window.to_yaml()
    print(yaml_output)
    
    # Test 2: Simple window template
    print("2. Simple Window Template:")
    simple_window = create_window_template("simple")
    print(simple_window.to_yaml())
    
    # Test 3: Custom window template
    print("3. Custom Window Template:")
    custom_window = WindowTemplate(
        name="custom_window",
        properties=[],
        dependencies=[]
    )
    custom_window.add_property(
        "brick:area", 
        "area_name",
        "area",
        {"name": "area_name", "value": "area_value", "unit": "area_unit"}
    )
    custom_window.add_property(
        "brick:azimuth", 
        "azimuth_name",
        "azimuth",
        {"name": "azimuth_name", "value": "azimuth_value"}
    )
    print(custom_window.to_yaml())
    
    # Test 4: Verify the generated body matches expected format
    print("4. Generated RDF/Turtle body:")
    print(window.generate_body())
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    test_window_template()
