from qtpy import QtWidgets, QtCore


class FlowLayout(QtWidgets.QLayout):
    """Layout that organize widgets by minimum size into a flow layout.

    Layout is putting widget from left to right and top to bottom. When widget
    can't fit a row it is added to next line. Minimum size matches widget with
    biggest 'sizeHint' width and height using calculated geometry.

    Content margins are part of calculations. It is possible to define
    horizontal and vertical spacing.

    Layout does not support stretch and spacing items.

    Todos:
        Unified width concept -> use width of largest item so all of them are
            same. This could allow to have minimum columns option too.
    """

    def __init__(self, parent=None):
        super(FlowLayout, self).__init__(parent)

        # spaces between each item
        self._horizontal_spacing = 5
        self._vertical_spacing = 5

        self._items = []

    def __del__(self):
        while self.count():
            self.takeAt(0, False)

    def isEmpty(self):
        for item in self._items:
            if not item.isEmpty():
                return False
        return True

    def setSpacing(self, spacing):
        self._horizontal_spacing = spacing
        self._vertical_spacing = spacing
        self.invalidate()

    def setHorizontalSpacing(self, spacing):
        self._horizontal_spacing = spacing
        self.invalidate()

    def setVerticalSpacing(self, spacing):
        self._vertical_spacing = spacing
        self.invalidate()

    def addItem(self, item):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index, invalidate=True):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            if invalidate:
                self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientations(QtCore.Qt.Vertical)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._setup_geometry(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._setup_geometry(rect)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize(0, 0)
        for item in self._items:
            widget = item.widget()
            if widget is not None:
                parent = widget.parent()
                if not widget.isVisibleTo(parent):
                    continue
            size = size.expandedTo(item.minimumSize())

        if size.width() < 1 or size.height() < 1:
            return size
        l_margin, t_margin, r_margin, b_margin = self.getContentsMargins()
        size += QtCore.QSize(l_margin + r_margin, t_margin + b_margin)
        return size

    def _setup_geometry(self, rect, only_calculate=False):
        h_spacing = self._horizontal_spacing
        v_spacing = self._vertical_spacing
        l_margin, t_margin, r_margin, b_margin = self.getContentsMargins()

        left_x = rect.x() + l_margin
        top_y = rect.y() + t_margin
        pos_x = left_x
        pos_y = top_y
        row_height = 0
        for item in self._items:
            item_hint = item.sizeHint()
            item_width = item_hint.width()
            item_height = item_hint.height()
            if item_width < 1 or item_height < 1:
                continue

            end_x = pos_x + item_width

            wrap = (
                row_height > 0
                and (
                    end_x > rect.right()
                    or (end_x + r_margin) > rect.right()
                )
            )
            if not wrap:
                next_pos_x = end_x + h_spacing
            else:
                pos_x = left_x
                pos_y += row_height + v_spacing
                next_pos_x = pos_x + item_width + h_spacing
                row_height = 0

            if not only_calculate:
                item.setGeometry(
                    QtCore.QRect(pos_x, pos_y, item_width, item_height)
                )

            pos_x = next_pos_x
            row_height = max(row_height, item_height)

        height = (pos_y - top_y) + row_height
        if height > 0:
            height += b_margin
        return height
