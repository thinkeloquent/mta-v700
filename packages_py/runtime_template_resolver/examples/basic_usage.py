"""
Basic usage examples for runtime_template_resolver.
"""
from runtime_template_resolver import resolve

def example_basic_usage():
    print("--- Basic Usage ---")
    context = {
        "user": {
            "name": "Alice",
            "role": "admin"
        },
        "env": "production"
    }
    
    # Mustache style
    template1 = "Hello {{user.name}}, welcome to {{env}}."
    print(f"Template: {template1}")
    print(f"Result:   {resolve(template1, context)}")
    
    # Dot path style
    template2 = "Role: $.user.role"
    print(f"Template: {template2}")
    print(f"Result:   {resolve(template2, context)}")
    
def example_defaults():
    print("\n--- Defaults ---")
    context = {}
    
    # Default value
    template = "User: {{user.name|\"Guest\"}}"
    print(f"Template: {template}")
    print(f"Result:   {resolve(template, context)}")
    
def example_arrays():
    print("\n--- Arrays ---")
    context = {"items": ["apple", "banana"]}
    
    template = "First item: {{items[0]}}"
    print(f"Template: {template}")
    print(f"Result:   {resolve(template, context)}")

if __name__ == "__main__":
    example_basic_usage()
    example_defaults()
    example_arrays()
