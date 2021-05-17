__all__ = (
    "IDENTIFIER_ROLE",

    "HierarchyView",

    "ProjectModel",
    "CreateProjectDialog",

    "HierarchyModel",
    "HierarchySelectionModel",
    "BaseItem",
    "RootItem",
    "ProjectItem",
    "AssetItem",
    "TaskItem",

    "ProjectManagerWindow",
    "main"
)


from .constants import (
    IDENTIFIER_ROLE
)
from .widgets import CreateProjectDialog
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
from .window import ProjectManagerWindow


def main():
    import sys
    from Qt import QtWidgets

    app = QtWidgets.QApplication([])

    window = ProjectManagerWindow()
    window.show()

    sys.exit(app.exec_())
