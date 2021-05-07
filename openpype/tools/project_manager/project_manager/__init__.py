__all__ = (
    "IDENTIFIER_ROLE",

    "HierarchyView",

    "ProjectModel",

    "HierarchyModel",
    "HierarchySelectionModel",
    "BaseItem",
    "RootItem",
    "ProjectItem",
    "AssetItem",
    "TaskItem",

    "Window",
    "main"
)


from .constants import (
    IDENTIFIER_ROLE
)
from .view import HierarchyView
from .model import (
    ProjectModel,

    HierarchyModel,
    HierarchySelectionModel,
    BaseItem,
    RootItem,
    ProjectItem,
    AssetItem,
    TaskItem
)
from .window import Window


def main():
    import sys
    from Qt import QtWidgets

    app = QtWidgets.QApplication([])

    window = Window()
    window.show()

    sys.exit(app.exec_())
