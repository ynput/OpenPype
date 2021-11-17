import Qt
from Qt import QtWidgets, QtCore, QtGui

from openpype.style import get_objected_colors

from .views import (
    TreeViewSpinner,
    DeselectableTreeView
)

if Qt.__binding__ == "PySide":
    from PySide.QtGui import QStyleOptionViewItemV4
elif Qt.__binding__ == "PyQt4":
    from PyQt4.QtGui import QStyleOptionViewItemV4

ASSET_ID_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
ASSET_LABEL_ROLE = QtCore.Qt.UserRole + 3
ASSET_UNDERLINE_COLORS_ROLE = QtCore.Qt.UserRole + 4


class AssetsView(TreeViewSpinner, DeselectableTreeView):
    """Item view.
    This implements a context menu.
    """

    def __init__(self, parent=None):
        super(AssetsView, self).__init__(parent)
        self.setIndentation(15)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHeaderHidden(True)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                return
            elif modifiers == QtCore.Qt.ControlModifier:
                return

        super(AssetsView, self).mousePressEvent(event)

    def set_loading_state(self, loading, empty):
        if self.is_loading != loading:
            if loading:
                self.spinner.repaintNeeded.connect(
                    self.viewport().update
                )
            else:
                self.spinner.repaintNeeded.disconnect()
                self.viewport().update()

        self.is_loading = loading
        self.is_empty = empty


class UnderlinesAssetDelegate(QtWidgets.QItemDelegate):
    bar_height = 3

    def __init__(self, *args, **kwargs):
        super(UnderlinesAssetDelegate, self).__init__(*args, **kwargs)
        asset_view_colors = get_objected_colors()["loader"]["asset-view"]
        self._selected_color = (
            asset_view_colors["selected"].get_qcolor()
        )
        self._hover_color = (
            asset_view_colors["hover"].get_qcolor()
        )
        self._selected_hover_color = (
            asset_view_colors["selected-hover"].get_qcolor()
        )

    def sizeHint(self, option, index):
        result = super(UnderlinesAssetDelegate, self).sizeHint(option, index)
        height = result.height()
        result.setHeight(height + self.bar_height)

        return result

    def paint(self, painter, option, index):
        # Qt4 compat
        if Qt.__binding__ in ("PySide", "PyQt4"):
            option = QStyleOptionViewItemV4(option)

        painter.save()

        item_rect = QtCore.QRect(option.rect)
        item_rect.setHeight(option.rect.height() - self.bar_height)

        subset_colors = index.data(ASSET_UNDERLINE_COLORS_ROLE) or []
        subset_colors_width = 0
        if subset_colors:
            subset_colors_width = option.rect.width() / len(subset_colors)

        subset_rects = []
        counter = 0
        for subset_c in subset_colors:
            new_color = None
            new_rect = None
            if subset_c:
                new_color = QtGui.QColor(*subset_c)

                new_rect = QtCore.QRect(
                    option.rect.left() + (counter * subset_colors_width),
                    option.rect.top() + (
                        option.rect.height() - self.bar_height
                    ),
                    subset_colors_width,
                    self.bar_height
                )
            subset_rects.append((new_color, new_rect))
            counter += 1

        # Background
        if option.state & QtWidgets.QStyle.State_Selected:
            if len(subset_colors) == 0:
                item_rect.setTop(item_rect.top() + (self.bar_height / 2))

            if option.state & QtWidgets.QStyle.State_MouseOver:
                bg_color = self._selected_hover_color
            else:
                bg_color = self._selected_color
        else:
            item_rect.setTop(item_rect.top() + (self.bar_height / 2))
            if option.state & QtWidgets.QStyle.State_MouseOver:
                bg_color = self._hover_color
            else:
                bg_color = QtGui.QColor()
                bg_color.setAlpha(0)

        # When not needed to do a rounded corners (easier and without
        #   painter restore):
        # painter.fillRect(
        #     item_rect,
        #     QtGui.QBrush(bg_color)
        # )
        pen = painter.pen()
        pen.setStyle(QtCore.Qt.NoPen)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(bg_color))
        painter.drawRoundedRect(option.rect, 3, 3)

        if option.state & QtWidgets.QStyle.State_Selected:
            for color, subset_rect in subset_rects:
                if not color or not subset_rect:
                    continue
                painter.fillRect(subset_rect, QtGui.QBrush(color))

        painter.restore()
        painter.save()

        # Icon
        icon_index = index.model().index(
            index.row(), index.column(), index.parent()
        )
        # - Default icon_rect if not icon
        icon_rect = QtCore.QRect(
            item_rect.left(),
            item_rect.top(),
            # To make sure it's same size all the time
            option.rect.height() - self.bar_height,
            option.rect.height() - self.bar_height
        )
        icon = index.model().data(icon_index, QtCore.Qt.DecorationRole)

        if icon:
            mode = QtGui.QIcon.Normal
            if not (option.state & QtWidgets.QStyle.State_Enabled):
                mode = QtGui.QIcon.Disabled
            elif option.state & QtWidgets.QStyle.State_Selected:
                mode = QtGui.QIcon.Selected

            if isinstance(icon, QtGui.QPixmap):
                icon = QtGui.QIcon(icon)
                option.decorationSize = icon.size() / icon.devicePixelRatio()

            elif isinstance(icon, QtGui.QColor):
                pixmap = QtGui.QPixmap(option.decorationSize)
                pixmap.fill(icon)
                icon = QtGui.QIcon(pixmap)

            elif isinstance(icon, QtGui.QImage):
                icon = QtGui.QIcon(QtGui.QPixmap.fromImage(icon))
                option.decorationSize = icon.size() / icon.devicePixelRatio()

            elif isinstance(icon, QtGui.QIcon):
                state = QtGui.QIcon.Off
                if option.state & QtWidgets.QStyle.State_Open:
                    state = QtGui.QIcon.On
                actual_size = option.icon.actualSize(
                    option.decorationSize, mode, state
                )
                option.decorationSize = QtCore.QSize(
                    min(option.decorationSize.width(), actual_size.width()),
                    min(option.decorationSize.height(), actual_size.height())
                )

            state = QtGui.QIcon.Off
            if option.state & QtWidgets.QStyle.State_Open:
                state = QtGui.QIcon.On

            icon.paint(
                painter, icon_rect,
                QtCore.Qt.AlignLeft, mode, state
            )

        # Text
        text_rect = QtCore.QRect(
            icon_rect.left() + icon_rect.width() + 2,
            item_rect.top(),
            item_rect.width(),
            item_rect.height()
        )

        painter.drawText(
            text_rect, QtCore.Qt.AlignVCenter,
            index.data(QtCore.Qt.DisplayRole)
        )

        painter.restore()
