"""
Model interfaces for Connect 4 Vision Benchmark.

Use lazy imports so manual mode works without API libraries installed.
"""

# Only import base class and manual models eagerly
from .base import BaseModel
from .manual_model import ManualModel, ClipboardModel

# Lazy imports for API-based models
def get_openai_model():
    from .openai_model import OpenAIModel
    return OpenAIModel

def get_anthropic_model():
    from .anthropic_model import AnthropicModel
    return AnthropicModel

def get_google_model():
    from .google_model import GoogleModel
    return GoogleModel

__all__ = ['BaseModel', 'ManualModel', 'ClipboardModel', 
           'get_openai_model', 'get_anthropic_model', 'get_google_model']
