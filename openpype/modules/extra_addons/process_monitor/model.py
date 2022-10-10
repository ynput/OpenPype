import os

from Qt import QtCore
import qtawesome

from openpype.style import get_default_entity_icon_color
from openpype.tools.utils.models import TreeModel, Item


class ProcessModel(TreeModel):
    """Model listing running processes"""
    #TODO: use dictionary instead of 'hardcoded' order everywhere (?)
    Columns = [
        "application",
        "project",
        "context",
        "task",
        "pid",
        "status"
    ]

    ApplicationRole = QtCore.Qt.UserRole + 2
    ProjectRole = QtCore.Qt.UserRole + 3
    ContextRole = QtCore.Qt.UserRole + 4
    TaskRole = QtCore.Qt.UserRole + 5
    PidRole = QtCore.Qt.UserRole + 6
    StatusRole = QtCore.Qt.UserRole + 7
    IsEnabled = QtCore.Qt.UserRole + 8

    def __init__(self, parent=None):
        super(ProcessModel, self).__init__(parent=parent)

        color = get_default_entity_icon_color()

        self._root = None
        self._icons = {
            "process": qtawesome.icon("fa.tasks", color=color),
            "running": qtawesome.icon("fa.clock-o", color=color)
        }

    '''
    def set_root(self, root):
        self._root = root
        self.refresh()
    '''

    def _add_empty(self):
        item = Item()
        item.update({
            "application": "No running process",
            "project": None,
            "context": None,
            "task": None,
            "pid": None,
            "status": None,
            # Not-selectable
            "enabled": False
        })

        self.add_child(item)


    def update(self, processes, current_pid=None):
        self.clear()
        self.beginResetModel()

        ########
        #TODO: 'merge' lines with same context, and add child for each PID
        # => Finish / make better
        # + handle changes elesewhere (selection, double click, context menu, etc.))
        """
        items = {}

        last_index = 0
        for pid in processes:
            application = processes[pid]["name"]

            data = processes[pid]["data"]

            for index in items:
                context = items[index]["context"]
                if (
                    application == context["name"]
                    and data == context["data"]
                ):
                    items[index]["pid"].append(pid)
                    break
            else:
                items[last_index] = {}
                items[last_index]["context"] = processes[pid]
                items[last_index]["pid"] = [ pid ]
                last_index += 1

        print("ITEMS: {}".format(items))

        # => then 'add_child' for each PID, with item as parent
        #...
        """
        ########

        for pid in processes:
            application = processes[pid]["name"]

            data = processes[pid]["data"]
            project = data["project_name"]
            task = data["task_name"]
            context = " / ".join(str(elem) for elem in data["hierarchy"])

            status = False
            if current_pid:
                status = current_pid == pid

            item = Item({
                "application": application,
                "project": project,
                "context": context,
                "task": task,
                "pid": pid,
                "status": status
            })

            self.add_child(item)

        if self.rowCount() == 0:
            self._add_empty()

        self.endResetModel()


    def rowCount(self, parent=None):
        if parent is None or not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.childCount()

    def data(self, index, role):
        if not index.isValid():
            return

        if role == QtCore.Qt.DecorationRole:
            # Add icon to 'application' column
            item = index.internalPointer()
            if index.column() == 0:
                if item["pid"]:
                    return self._icons["process"]
                return item.get("icon", None)

            # Add icon to 'status' column
            if index.column() == 5:
                if item["status"]:
                    return self._icons["running"]
                return item.get("icon", None)

        # Specific display for 'status' column
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 5:
                item = index.internalPointer()
                if item["status"]:
                    return "Running..."
                else:
                    return None

        if role == self.ApplicationRole:
            item = index.internalPointer()
            return item["application"]

        if role == self.ProjectRole:
            item = index.internalPointer()
            return item["project"]

        if role == self.ContextRole:
            item = index.internalPointer()
            return item["context"]

        if role == self.TaskRole:
            item = index.internalPointer()
            return item["task"]

        if role == self.PidRole:
            item = index.internalPointer()
            return item["pid"]

        if role == self.StatusRole:
            item = index.internalPointer()
            return item["status"]

        if role == self.IsEnabled:
            item = index.internalPointer()
            return item.get("enabled", True)

        return super(ProcessModel, self).data(index, role)

    def headerData(self, section, orientation, role):
        # Show nice labels in the header
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
        ):
            if section == 0:
                return "Application"
            elif section == 1:
                return "Project"
            elif section == 2:
                return "Context"
            elif section == 3:
                return "Task"
            elif section == 4:
                return "Process ID"
            elif section == 5:
                return "Timer Status"

        return super(ProcessModel, self).headerData(section,
                                                    orientation,
                                                    role)
