import uuid
from Qt import QtGui, QtCore

from openpype.pipeline import discover_legacy_creator_plugins

from . constants import (
    FAMILY_ROLE,
    ITEM_ID_ROLE
)


class CreatorsModel(QtGui.QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(CreatorsModel, self).__init__(*args, **kwargs)

        self._creators_by_id = {}

    def reset(self):
        # TODO change to refresh when clearing is not needed
        self.clear()
        self._creators_by_id = {}

        items = []
        creators = discover_legacy_creator_plugins()
        for creator in creators:
            item_id = str(uuid.uuid4())
            self._creators_by_id[item_id] = creator

            label = creator.label or creator.family
            item = QtGui.QStandardItem(label)
            item.setEditable(False)
            item.setData(item_id, ITEM_ID_ROLE)
            item.setData(creator.family, FAMILY_ROLE)
            items.append(item)

        if not items:
            item = QtGui.QStandardItem("No registered families")
            item.setEnabled(False)
            item.setData(QtCore.Qt.ItemIsEnabled, False)
            items.append(item)

        self.invisibleRootItem().appendRows(items)

    def get_creator_by_id(self, item_id):
        return self._creators_by_id.get(item_id)

    def get_indexes_by_family(self, family):
        indexes = []
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            item_id = index.data(ITEM_ID_ROLE)
            creator_plugin = self._creators_by_id.get(item_id)
            if creator_plugin and creator_plugin.family == family:
                indexes.append(index)
        return indexes
