#!/usr/bin/env python3
"""
Migration Script for Semantic MPC Interface Refactoring

This script helps migrate from the old BrickModelInterface structure
to the new semantic_mpc_interface package structure.
"""

import os
import shutil
from pathlib import Path

def migrate_old_imports():
    """Update import statements in Python files."""
    
    # Mapping of old imports to new imports
    import_mapping = {
        "from BrickModelInterface.model_builder import BrickModelBuilder": 
            "from semantic_mpc_interface import SemanticModelBuilder as BrickModelBuilder",
        "from BrickModelInterface import": 
            "from semantic_mpc_interface import",
        "import BrickModelInterface": 
            "import semantic_mpc_interface",
        "BrickModelInterface.": 
            "semantic_mpc_interface.",
    }
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk("."):
        # Skip the new src directory and other directories we don't want to modify
        if "src" in root or ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to check for imports")
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Apply import mappings
            for old_import, new_import in import_mapping.items():
                content = content.replace(old_import, new_import)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"Updated imports in: {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

def create_compatibility_module():
    """Create a compatibility module for backward compatibility."""
    
    compat_content = '''"""
Backward Compatibility Module

This module provides backward compatibility for the old BrickModelInterface.
"""

import warnings
from semantic_mpc_interface import *

# Issue deprecation warning
warnings.warn(
    "BrickModelInterface is deprecated. Please use semantic_mpc_interface instead.",
    DeprecationWarning,
    stacklevel=2
)

# Backward compatibility aliases
BrickModelBuilder = SemanticModelBuilder
'''
    
    # Create BrickModelInterface directory if it doesn't exist
    if not os.path.exists("BrickModelInterface"):
        os.makedirs("BrickModelInterface")
    
    # Write compatibility __init__.py
    with open("BrickModelInterface/__init__.py", "w") as f:
        f.write(compat_content)
    
    print("Created backward compatibility module at BrickModelInterface/__init__.py")

def update_notebooks():
    """Update Jupyter notebooks to use new imports."""
    
    import_replacements = {
        "from BrickModelInterface": "from semantic_mpc_interface",
        "import BrickModelInterface": "import semantic_mpc_interface",
        "BrickModelInterface.": "semantic_mpc_interface.",
    }
    
    # Find all notebook files
    notebook_files = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".ipynb"):
                notebook_files.append(os.path.join(root, file))
    
    print(f"Found {len(notebook_files)} notebook files to update")
    
    for notebook_path in notebook_files:
        try:
            import json
            
            with open(notebook_path, 'r') as f:
                notebook = json.load(f)
            
            modified = False
            
            # Update code cells
            for cell in notebook.get('cells', []):
                if cell.get('cell_type') == 'code':
                    source = cell.get('source', [])
                    if isinstance(source, list):
                        for i, line in enumerate(source):
                            original_line = line
                            for old, new in import_replacements.items():
                                line = line.replace(old, new)
                            if line != original_line:
                                source[i] = line
                                modified = True
            
            if modified:
                with open(notebook_path, 'w') as f:
                    json.dump(notebook, f, indent=2)
                print(f"Updated notebook: {notebook_path}")
                
        except Exception as e:
            print(f"Error processing notebook {notebook_path}: {e}")

def main():
    """Run the migration."""
    
    print("Starting migration to new semantic_mpc_interface structure...")
    print("=" * 60)
    
    # Step 1: Update Python imports
    print("\n1. Updating Python import statements...")
    migrate_old_imports()
    
    # Step 2: Create compatibility module
    print("\n2. Creating backward compatibility module...")
    create_compatibility_module()
    
    # Step 3: Update notebooks
    print("\n3. Updating Jupyter notebooks...")
    update_notebooks()
    
    print("\n" + "=" * 60)
    print("Migration completed!")
    print("\nNext steps:")
    print("1. Install the new package: pip install -e .")
    print("2. Test your code with the new imports")
    print("3. Update any remaining manual references")
    print("4. Consider removing the old BrickModelInterface directory when ready")
    print("\nNote: The old BrickModelInterface will still work via the compatibility module,")
    print("but you should migrate to semantic_mpc_interface for future development.")

if __name__ == "__main__":
    main()