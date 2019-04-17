from . import QtWidgets
from . import ComponentWidget


class ComponentItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.parent_widget = parent
        self.in_data = data

    def set_context(self):
        self._widget = ComponentWidget(self)
        self._widget.set_context(self.in_data)
        self.treeWidget().setItemWidget(self, 0, self._widget)

    def is_thumbnail(self):
        return self._widget.thumbnail.checked

    def change_thumbnail(self, hover=True):
        self._widget.thumbnail.change_checked(hover)

    def is_preview(self):
        return self._widget.preview.checked

    def change_preview(self, hover=True):
        self._widget.preview.change_checked(hover)

    def double_clicked(*args):
        pass
