# -*- coding: utf-8 -*-
"""Public API for 3dsmax"""

from .pipeline import (
    MaxHost,
)


from .lib import (
    maintained_selection,
    lsattr,
    get_all_children
)

__all__ = [
    "MaxHost",
    "maintained_selection",
    "lsattr",
    "get_all_children"
]
