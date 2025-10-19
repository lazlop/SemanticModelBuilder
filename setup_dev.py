#!/usr/bin/env python3
"""
Development Setup Script

This script sets up the development environment for the Semantic MPC Interface package.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False


def main():
    """Set up the development environment."""
    
    print("🚀 Setting up Semantic MPC Interface development environment...")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Install the package in editable mode with all dependencies
    success = run_command(
        'pip install -e ".[dev,grafana,docs,jupyter]"',
        "Installing package in editable mode with all dependencies"
    )
    
    if not success:
        print("❌ Failed to install package. Please check the error above.")
        sys.exit(1)
    
    # Install pre-commit hooks if available
    if Path(".pre-commit-config.yaml").exists():
        run_command("pre-commit install", "Installing pre-commit hooks")
    
    # Test the installation
    success = run_command(
        'python -c "import semantic_mpc_interface; print(f\'Package version: {semantic_mpc_interface.__version__}\')"',
        "Testing package import"
    )
    
    if not success:
        print("❌ Package import test failed.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Development environment setup completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run tests: make test")
    print("   2. Format code: make format")
    print("   3. Run linting: make lint")
    print("   4. Try examples: python examples/basic_building_model.py")
    print("   5. Build docs: make docs")
    print("\n💡 Available make commands:")
    print("   make help    - Show all available commands")
    print("   make test    - Run tests")
    print("   make format  - Format code")
    print("   make lint    - Run linting")
    print("   make docs    - Build documentation")
    print("   make clean   - Clean build artifacts")


if __name__ == "__main__":
    main()