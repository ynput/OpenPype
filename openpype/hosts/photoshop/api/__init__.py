"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .launch_logic import stub

from .pipeline import (
    PhotoshopHost,
    ls,
    containerise
)
from .plugin import (
    PhotoshopLoader,
    get_unique_layer_name
)


from .lib import (
    maintained_selection,
    maintained_visibility
)

__all__ = [
    # launch_logic
    "stub",

    # pipeline
    "PhotoshopHost",
    "ls",
    "containerise",

    # Plugin
    "PhotoshopLoader",
    "get_unique_layer_name",

    # lib
    "maintained_selection",
    "maintained_visibility",
]
