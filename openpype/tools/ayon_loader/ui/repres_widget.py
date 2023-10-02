from qtpy import QtWidgets


class RepresentationsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(RepresentationsWidget, self).__init__(parent)

        self._controller = controller

        repre_view = QtWidgets.QTreeView(self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(repre_view, 1)

        self._repre_view = repre_view
