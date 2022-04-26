from Qt import QtWidgets, QtCore


class View(QtWidgets.QTreeView):
    data_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(View, self).__init__(parent=parent)

        # view settings
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def get_indices(self):
        """Get the selected rows"""
        selection_model = self.selectionModel()
        return selection_model.selectedRows()

    def extend_to_children(self, indices):
        """Extend the indices to the children indices.

        Top-level indices are extended to its children indices. Sub-items
        are kept as is.

        :param indices: The indices to extend.
        :type indices: list

        :return: The children indices
        :rtype: list
        """

        subitems = set()
        for i in indices:
            valid_parent = i.parent().isValid()
            if valid_parent and i not in subitems:
                subitems.add(i)
            else:
                # is top level node
                model = i.model()
                rows = model.rowCount(parent=i)
                for row in range(rows):
                    child = model.index(row, 0, parent=i)
                    subitems.add(child)

        return list(subitems)
