import os
from Qt import QtCore
from pype.api import Logger
from pypeapp.lib.log import _bootstrap_mongo_log

log = Logger().get_logger("LogModel", "LoggingModule")


class LogModel(QtCore.QAbstractItemModel):
    COLUMNS = [
        "user",
        "host",
        "lineNumber",
        "method",
        "module",
        "fileName",
        "loggerName",
        "message",
        "level",
        "timestamp",
    ]

    colums_mapping = {
        "user": "User",
        "host": "Host",
        "lineNumber": "Line n.",
        "method": "Method",
        "module": "Module",
        "fileName": "File name",
        "loggerName": "Logger name",
        "message": "Message",
        "level": "Level",
        "timestamp": "Timestamp",
    }

    NodeRole = QtCore.Qt.UserRole + 1

    def __init__(self, parent=None):
        super(LogModel, self).__init__(parent)
        self._root_node = Node()

        collection = os.environ.get('PYPE_LOG_MONGO_COL')
        database = _bootstrap_mongo_log()
        self.dbcon = None
        if collection in database.list_collection_names():
            self.dbcon = database[collection]

    def add_log(self, log):
        node = Node(log)
        self._root_node.add_child(node)

    def refresh(self):
        self.clear()
        self.beginResetModel()
        if self.dbcon:
            result = self.dbcon.find({})
            for item in result:
                self.add_log(item)
        self.endResetModel()


    def data(self, index, role):
        if not index.isValid():
            return None

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            node = index.internalPointer()
            column = index.column()

            key = self.COLUMNS[column]
            if key == "timestamp":
                return str(node.get(key, None))
            return node.get(key, None)

        if role == self.NodeRole:
            return index.internalPointer()

    def index(self, row, column, parent):
        """Return index for row/column under parent"""

        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        child_item = parent_node.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QtCore.QModelIndex()

    def rowCount(self, parent):
        node = self._root_node
        if parent.isValid():
            node = parent.internalPointer()
        return node.childCount()

    def columnCount(self, parent):
        return len(self.COLUMNS)

    def parent(self, index):
        return QtCore.QModelIndex()

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section < len(self.COLUMNS):
                key = self.COLUMNS[section]
                return self.colums_mapping.get(key, key)

        super(LogModel, self).headerData(section, orientation, role)

    def flags(self, index):
        return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

    def clear(self):
        self.beginResetModel()
        self._root_node = Node()
        self.endResetModel()


class Node(dict):
    """A node that can be represented in a tree view.

    The node can store data just like a dictionary.

    >>> data = {"name": "John", "score": 10}
    >>> node = Node(data)
    >>> assert node["name"] == "John"

    """

    def __init__(self, data=None):
        super(Node, self).__init__()

        self._children = list()
        self._parent = None

        if data is not None:
            assert isinstance(data, dict)
            self.update(data)

    def childCount(self):
        return len(self._children)

    def child(self, row):
        if row >= len(self._children):
            log.warning("Invalid row as child: {0}".format(row))
            return

        return self._children[row]

    def children(self):
        return self._children

    def parent(self):
        return self._parent

    def row(self):
        """
        Returns:
             int: Index of this node under parent"""
        if self._parent is not None:
            siblings = self.parent().children()
            return siblings.index(self)

    def add_child(self, child):
        """Add a child to this node"""
        child._parent = self
        self._children.append(child)
