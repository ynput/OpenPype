import uuid
from ... import api
from ...vendor.Qt import QtCore
from ..models import TreeModel, Item

InstanceRole = QtCore.Qt.UserRole + 1
InstanceItemId = QtCore.Qt.UserRole + 2


class InstanceModel(TreeModel):
    column_label_mapping = {
        "label": "Instance"
    }
    Columns = list(column_label_mapping.keys())

    def __init__(self, *args, **kwargs):
        super(InstanceModel, self).__init__(*args, **kwargs)
        self.items_by_id = {}

    def refresh(self):
        self.clear()

        self.items_by_id.clear()

        instances = None
        host = api.registered_host()
        list_instances = getattr(host, "list_instances", None)
        if list_instances:
            instances = list_instances()

        if not instances:
            return

        self.beginResetModel()

        for instance_data in instances:
            item_id = str(uuid.uuid4())
            item = Item({
                "item_id": item_id,
                "label": instance_data.get("label") or instance_data["subset"],
                "instance": instance_data
            })
            self.items_by_id[item_id] = item
            self.add_child(item)

        self.endResetModel()

    def data(self, index, role):
        if not index.isValid():
            return

        if role == InstanceItemId:
            item = index.internalPointer()
            return item["item_id"]

        if role == InstanceRole:
            item = index.internalPointer()
            return item["instance"]

        return super(InstanceModel, self).data(index, role)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section < len(self.Columns):
                return self.column_label_mapping[self.Columns[section]]

        return super(InstanceModel, self).headerData(
            section, orientation, role
        )
