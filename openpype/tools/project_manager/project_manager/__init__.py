__all__ = (
    "IDENTIFIER_ROLE",
    "PROJECT_NAME_ROLE",

    "HierarchyView",

    "ProjectModel",
    "ProjectProxyFilter",
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
    IDENTIFIER_ROLE,
    PROJECT_NAME_ROLE
)
from .widgets import CreateProjectDialog
from .view import HierarchyView
from .model import (
    ProjectModel,
    ProjectProxyFilter,

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
