"""
Semantic MPC Interface

A Python package for creating and managing semantic building models using 
Brick Schema and ASHRAE Standard 223P ontologies.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Core imports
from .model_builder import SemanticModelBuilder, BrickModelBuilder
from .metadata import SurveyGenerator, SurveyReader, MetadataProcessor
from .validation import SHACLHandler
from .points import PointManager
from .grafana import BrickToGrafana
from .conversion import UnitConverter
from .utils import bind_prefixes

# Template and namespace imports
from .namespaces import *

__all__ = [
    # Core classes
    "SemanticModelBuilder",
    "BrickModelBuilder", 
    "SurveyGenerator",
    "SurveyReader",
    "MetadataProcessor",
    "SHACLHandler",
    "BrickToGrafana",
    "UnitConverter",
    "PointManager",
    # Utilities
    "bind_prefixes",
    # Version info
    "__version__",
]