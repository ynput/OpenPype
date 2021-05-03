import os
from Qt import QtCore, QtWidgets, QtGui
from avalon.vendor import qtawesome

from openpype.lib import PypeLogger
from openpype.modules.sync_server.tray import lib

log = PypeLogger().get_logger("SyncServer")


class PriorityDelegate(QtWidgets.QStyledItemDelegate):
    """Creates editable line edit to set priority on representation"""
    def paint(self, painter, option, index):
        super(PriorityDelegate, self).paint(painter, option, index)

        if option.widget.selectionModel().isSelected(index) or \
                option.state & QtWidgets.QStyle.State_MouseOver:
            edit_icon = qtawesome.icon("fa.edit", color="white")
            state = QtGui.QIcon.On
            mode = QtGui.QIcon.Selected

            icon_side = 16
            icon_rect = QtCore.QRect(
                option.rect.left() + option.rect.width() - icon_side - 4,
                option.rect.top() + ((option.rect.height() - icon_side) / 2),
                icon_side,
                icon_side
            )

            edit_icon.paint(
                painter, icon_rect,
                QtCore.Qt.AlignRight, mode, state
            )

    def createEditor(self, parent, option, index):
        editor = PriorityLineEdit(
            parent,
            option.widget.selectionModel().selectedRows())
        editor.setValidator(QtGui.QIntValidator(0, 1000, self))
        editor.setFocus(True)
        return editor

    def setModelData(self, editor, model, index):
        for index in editor.selected_idxs:
            model.set_priority_data(index, editor.text())


class PriorityLineEdit(QtWidgets.QLineEdit):
    """Special LineEdit to consume Enter and store selected indexes"""
    def __init__(self, parent=None, selected_idxs=None):
        self.selected_idxs = selected_idxs
        super(PriorityLineEdit, self).__init__(parent)

    def keyPressEvent(self, event):
        result = super(PriorityLineEdit, self).keyPressEvent(event)
        if (
            event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter)
        ):
            return event.accept()

        return result


class ImageDelegate(QtWidgets.QStyledItemDelegate):
    """
        Prints icon of site and progress of synchronization
    """

    def __init__(self, parent=None):
        super(ImageDelegate, self).__init__(parent)
        self.icons = {}

    def paint(self, painter, option, index):
        super(ImageDelegate, self).paint(painter, option, index)
        option = QtWidgets.QStyleOptionViewItem(option)
        option.showDecorationSelected = True

        provider = index.data(lib.ProviderRole)
        value = index.data(lib.ProgressRole)
        date_value = index.data(lib.DateRole)
        is_failed = index.data(lib.FailedRole)

        if not self.icons.get(provider):
            resource_path = os.path.dirname(__file__)
            resource_path = os.path.join(resource_path, "..",
                                         "providers", "resources")
            pix_url = "{}/{}.png".format(resource_path, provider)
            pixmap = QtGui.QPixmap(pix_url)
            self.icons[provider] = pixmap
        else:
            pixmap = self.icons[provider]

        padding = 10
        point = QtCore.QPoint(option.rect.x() + padding,
                              option.rect.y() +
                              (option.rect.height() - pixmap.height()) / 2)
        painter.drawPixmap(point, pixmap)

        overlay_rect = option.rect.translated(0, 0)
        overlay_rect.setHeight(overlay_rect.height() * (1.0 - float(value)))
        painter.fillRect(overlay_rect,
                         QtGui.QBrush(QtGui.QColor(0, 0, 0, 100)))
        text_rect = option.rect.translated(10, 0)
        painter.drawText(text_rect,
                         QtCore.Qt.AlignCenter,
                         date_value)

        if is_failed:
            overlay_rect = option.rect.translated(0, 0)
            painter.fillRect(overlay_rect,
                             QtGui.QBrush(QtGui.QColor(255, 0, 0, 35)))
