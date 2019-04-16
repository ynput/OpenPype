from . import QtWidgets
from . import ComponentWidget


class ComponentItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.in_data = data
        self._widget = ComponentWidget(self)
        self._widget.set_context(data)

        self.treeWidget().setItemWidget(self, 0, self._widget)

    def double_clicked(*args):
        pass
