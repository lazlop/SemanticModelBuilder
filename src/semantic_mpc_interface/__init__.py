"""
Semantic MPC Interface

A Python package for creating and managing semantic building models using
Brick Schema and ASHRAE Standard 223P ontologies.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .conversion import UnitConverter
from .grafana import BrickToGrafana
from .metadata import MetadataProcessor, SurveyGenerator, SurveyReader

# Core imports
from .model_builder import BrickModelBuilder, SemanticModelBuilder

# Template and namespace imports
from .namespaces import *
from .points import PointManager
from .utils import bind_prefixes
from .validation import SHACLHandler

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
