# this_file: stubs/fl.pyi
# Type stubs for FontLab's fl module
# These are minimal stubs to satisfy type checking outside FontLab

from typing import Any

# FontLab Application Interface
iface: Any

# Current font and glyph accessors
def CurrentFont() -> Any: ...
def CurrentGlyph() -> Any: ...

# Output function
def output(message: str) -> None: ...

# Font object (simplified)
font: Any
glyph: Any
