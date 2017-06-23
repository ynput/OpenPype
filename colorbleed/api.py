from collections import OrderedDict

from .plugin import (

    Extractor,

    ValidatePipelineOrder,
    ValidateContentsOrder,
    ValidateSceneOrder,
    ValidateMeshOrder
)

# temporary fix, might
from .action import (
    SelectInvalidAction,
    GenerateUUIDsOnInvalidAction,
    RepairAction
)


def merge(*args):
    """Helper to merge OrderedDict instances"""
    data = OrderedDict()
    for arg in args:
        for key, value in arg.items():
            data.pop(key, None)
            data[key] = value
    return data


all = [
    "Extractor",
    "ValidatePipelineOrder",
    "ValidateContentsOrder",
    "ValidateSceneOrder",
    "ValidateMeshOrder",

    "SelectInvalidAction",
    "GenerateUUIDsOnInvalidAction",
    "RepairAction"
]
