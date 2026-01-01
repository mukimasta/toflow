"""
Renderer package.

Public surface:
- Renderer: prompt-toolkit formatted text rendering + viewport (implicit scroll)
- LayoutManager: prompt-toolkit layout construction
"""

from .renderer import Renderer
from .layout_manager import LayoutManager

__all__ = ["Renderer", "LayoutManager"]


