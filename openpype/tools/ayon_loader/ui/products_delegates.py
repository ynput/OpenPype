import numbers
from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils.lib import format_version

from .products_model import (
    PRODUCT_ID_ROLE,
    VERSION_NAME_EDIT_ROLE,
    VERSION_ID_ROLE,
    PRODUCT_IN_SCENE_ROLE,
    ACTIVE_SITE_ICON_ROLE,
    REMOTE_SITE_ICON_ROLE,
    REPRESENTATIONS_COUNT_ROLE,
    SYNC_ACTIVE_SITE_AVAILABILITY,
    SYNC_REMOTE_SITE_AVAILABILITY,
)


class VersionComboBox(QtWidgets.QComboBox):
    value_changed = QtCore.Signal(str)

    def __init__(self, product_id, parent):
        super(VersionComboBox, self).__init__(parent)
        self._product_id = product_id
        self._items_by_id = {}

        self._current_id = None

        self.currentIndexChanged.connect(self._on_index_change)

    def update_versions(self, version_items, current_version_id):
        model = self.model()
        root_item = model.invisibleRootItem()
        version_items = list(reversed(version_items))
        version_ids = [
            version_item.version_id
            for version_item in version_items
        ]
        if current_version_id not in version_ids and version_ids:
            current_version_id = version_ids[0]
        self._current_id = current_version_id

        to_remove = set(self._items_by_id.keys()) - set(version_ids)
        for item_id in to_remove:
            item = self._items_by_id.pop(item_id)
            root_item.removeRow(item.row())

        for idx, version_item in enumerate(version_items):
            version_id = version_item.version_id

            item = self._items_by_id.get(version_id)
            if item is None:
                label = format_version(
                    abs(version_item.version), version_item.is_hero
                )
                item = QtGui.QStandardItem(label)
                item.setData(version_id, QtCore.Qt.UserRole)
                self._items_by_id[version_id] = item

            if item.row() != idx:
                root_item.insertRow(idx, item)

        index = version_ids.index(current_version_id)
        if self.currentIndex() != index:
            self.setCurrentIndex(index)

    def _on_index_change(self):
        idx = self.currentIndex()
        value = self.itemData(idx)
        if value == self._current_id:
            return
        self._current_id = value
        self.value_changed.emit(self._product_id)


class VersionDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that display version integer formatted as version string."""

    version_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(VersionDelegate, self).__init__(*args, **kwargs)
        self._editor_by_product_id = {}

    def displayText(self, value, locale):
        if not isinstance(value, numbers.Integral):
            return "N/A"
        return format_version(abs(value), value < 0)

    def paint(self, painter, option, index):
        fg_color = index.data(QtCore.Qt.ForegroundRole)
        if fg_color:
            if isinstance(fg_color, QtGui.QBrush):
                fg_color = fg_color.color()
            elif isinstance(fg_color, QtGui.QColor):
                pass
            else:
                fg_color = None

        if not fg_color:
            return super(VersionDelegate, self).paint(painter, option, index)

        if option.widget:
            style = option.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        style.drawControl(
            style.CE_ItemViewItem, option, painter, option.widget
        )

        painter.save()

        text = self.displayText(
            index.data(QtCore.Qt.DisplayRole), option.locale
        )
        pen = painter.pen()
        pen.setColor(fg_color)
        painter.setPen(pen)

        text_rect = style.subElementRect(style.SE_ItemViewItemText, option)
        text_margin = style.proxy().pixelMetric(
            style.PM_FocusFrameHMargin, option, option.widget
        ) + 1

        painter.drawText(
            text_rect.adjusted(text_margin, 0, - text_margin, 0),
            option.displayAlignment,
            text
        )

        painter.restore()

    def createEditor(self, parent, option, index):
        product_id = index.data(PRODUCT_ID_ROLE)
        if not product_id:
            return

        editor = VersionComboBox(product_id, parent)
        self._editor_by_product_id[product_id] = editor
        editor.value_changed.connect(self._on_editor_change)

        return editor

    def _on_editor_change(self, product_id):
        editor = self._editor_by_product_id[product_id]

        # Update model data
        self.commitData.emit(editor)
        # Display model data
        self.version_changed.emit()

    def setEditorData(self, editor, index):
        editor.clear()

        # Current value of the index
        versions = index.data(VERSION_NAME_EDIT_ROLE) or []
        version_id = index.data(VERSION_ID_ROLE)
        editor.update_versions(versions, version_id)

    def setModelData(self, editor, model, index):
        """Apply the integer version back in the model"""

        version_id = editor.itemData(editor.currentIndex())
        model.setData(index, version_id, VERSION_NAME_EDIT_ROLE)


class LoadedInSceneDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate for Loaded in Scene state columns.

    Shows "Yes" or "No" for 1 or 0 values, or "N/A" for other values.
    Colorizes green or dark grey based on values.
    """

    def __init__(self, *args, **kwargs):
        super(LoadedInSceneDelegate, self).__init__(*args, **kwargs)
        self._colors = {
            1: QtGui.QColor(80, 170, 80),
            0: QtGui.QColor(90, 90, 90),
        }
        self._default_color = QtGui.QColor(90, 90, 90)

    def displayText(self, value, locale):
        if value == 0:
            return "No"
        elif value == 1:
            return "Yes"
        return "N/A"

    def initStyleOption(self, option, index):
        super(LoadedInSceneDelegate, self).initStyleOption(option, index)

        # Colorize based on value
        value = index.data(PRODUCT_IN_SCENE_ROLE)
        color = self._colors.get(value, self._default_color)
        option.palette.setBrush(QtGui.QPalette.Text, color)


class SiteSyncDelegate(QtWidgets.QStyledItemDelegate):
    """Paints icons and downloaded representation ration for both sites."""

    def paint(self, painter, option, index):
        super(SiteSyncDelegate, self).paint(painter, option, index)
        option = QtWidgets.QStyleOptionViewItem(option)
        option.showDecorationSelected = True

        active_icon = index.data(ACTIVE_SITE_ICON_ROLE)
        remote_icon = index.data(REMOTE_SITE_ICON_ROLE)

        availability_active = "{}/{}".format(
            index.data(SYNC_ACTIVE_SITE_AVAILABILITY),
            index.data(REPRESENTATIONS_COUNT_ROLE)
        )
        availability_remote = "{}/{}".format(
            index.data(SYNC_REMOTE_SITE_AVAILABILITY),
            index.data(REPRESENTATIONS_COUNT_ROLE)
        )

        if availability_active is None or availability_remote is None:
            return

        items_to_draw = [
            (value, icon)
            for value, icon in (
                (availability_active, active_icon),
                (availability_remote, remote_icon),
            )
            if icon
        ]
        if not items_to_draw:
            return

        icon_size = QtCore.QSize(24, 24)
        padding = 10
        pos_x = option.rect.x()

        item_width = int(option.rect.width() / len(items_to_draw))
        if item_width < 1:
            item_width = 0

        for value, icon in items_to_draw:
            item_rect = QtCore.QRect(
                pos_x,
                option.rect.y(),
                item_width,
                option.rect.height()
            )
            # Prepare pos_x for next item
            pos_x = item_rect.x() + item_rect.width()

            pixmap = icon.pixmap(icon.actualSize(icon_size))
            point = QtCore.QPoint(
                item_rect.x() + padding,
                item_rect.y() + ((item_rect.height() - pixmap.height()) * 0.5)
            )
            painter.drawPixmap(point, pixmap)

            icon_offset = icon_size.width() + (padding * 2)
            text_rect = QtCore.QRect(item_rect)
            text_rect.setLeft(text_rect.left() + icon_offset)
            if text_rect.width() < 1:
                continue

            painter.drawText(
                text_rect,
                option.displayAlignment,
                value
            )

    def displayText(self, value, locale):
        pass
