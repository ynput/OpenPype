from Qt import QtCore
import qtawesome
from . import Node, TreeModel
from avalon import style


class TasksTemplateModel(TreeModel):
    """A model listing the tasks combined for a list of assets"""

    COLUMNS = ["Tasks"]

    def __init__(self, selectable=True):
        super(TasksTemplateModel, self).__init__()
        self.selectable = selectable
        self.icon = qtawesome.icon(
            'fa.calendar-check-o',
            color=style.colors.default
        )

    def set_tasks(self, tasks):
        """Set assets to track by their database id

        Arguments:
            asset_ids (list): List of asset ids.

        """

        self.clear()

        # let cleared task view if no tasks are available
        if len(tasks) == 0:
            return

        self.beginResetModel()

        for task in tasks:
            node = Node({
                "Tasks": task,
                "icon": self.icon
            })
            self.add_child(node)

        self.endResetModel()

    def flags(self, index):
        if self.selectable is False:
            return QtCore.Qt.ItemIsEnabled
        else:
            return (
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )

    def data(self, index, role):

        if not index.isValid():
            return

        # Add icon to the first column
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                return index.internalPointer()['icon']

        return super(TasksTemplateModel, self).data(index, role)
