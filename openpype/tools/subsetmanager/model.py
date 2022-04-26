import uuid

from Qt import QtCore, QtGui

from openpype.pipeline import registered_host

ITEM_ID_ROLE = QtCore.Qt.UserRole + 1


class InstanceModel(QtGui.QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(InstanceModel, self).__init__(*args, **kwargs)
        self._instances_by_item_id = {}

    def get_instance_by_id(self, item_id):
        return self._instances_by_item_id.get(item_id)

    def refresh(self):
        self.clear()

        self._instances_by_item_id = {}

        instances = None
        host = registered_host()
        list_instances = getattr(host, "list_instances", None)
        if list_instances:
            instances = list_instances()

        if not instances:
            return

        items = []
        for instance_data in instances:
            item_id = str(uuid.uuid4())
            label = instance_data.get("label") or instance_data["subset"]
            item = QtGui.QStandardItem(label)
            item.setEnabled(True)
            item.setEditable(False)
            item.setData(item_id, ITEM_ID_ROLE)
            items.append(item)
            self._instances_by_item_id[item_id] = instance_data

        if items:
            self.invisibleRootItem().appendRows(items)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole and section == 0:
            return "Instance"

        return super(InstanceModel, self).headerData(
            section, orientation, role
        )
