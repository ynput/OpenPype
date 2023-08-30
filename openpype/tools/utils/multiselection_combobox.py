from qtpy import QtCore, QtGui, QtWidgets

from .lib import (
    checkstate_int_to_enum,
    checkstate_enum_to_int,
)
from .constants import (
    CHECKED_INT,
    UNCHECKED_INT,
    ITEM_IS_USER_TRISTATE,
)


class ComboItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Helper styled delegate (mostly based on existing private Qt's
    delegate used by the QtWidgets.QComboBox). Used to style the popup like a
    list view (e.g windows style).
    """

    def paint(self, painter, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        option.showDecorationSelected = True

        # option.state &= (
        #     ~QtWidgets.QStyle.State_HasFocus
        #     & ~QtWidgets.QStyle.State_MouseOver
        # )
        super(ComboItemDelegate, self).paint(painter, option, index)


class MultiSelectionComboBox(QtWidgets.QComboBox):
    value_changed = QtCore.Signal()
    focused_in = QtCore.Signal()

    ignored_keys = {
        QtCore.Qt.Key_Up,
        QtCore.Qt.Key_Down,
        QtCore.Qt.Key_PageDown,
        QtCore.Qt.Key_PageUp,
        QtCore.Qt.Key_Home,
        QtCore.Qt.Key_End,
    }

    top_bottom_padding = 2
    left_right_padding = 3
    left_offset = 4
    top_bottom_margins = 2
    item_spacing = 5

    item_bg_color = QtGui.QColor("#31424e")

    def __init__(
        self, parent=None, placeholder="", separator=", ", **kwargs
    ):
        super(MultiSelectionComboBox, self).__init__(parent=parent, **kwargs)
        self.setObjectName("MultiSelectionComboBox")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._popup_is_shown = False
        self._block_mouse_release_timer = QtCore.QTimer(self, singleShot=True)
        self._initial_mouse_pos = None
        self._separator = separator
        self._placeholder_text = placeholder
        delegate = ComboItemDelegate(self)
        self.setItemDelegate(delegate)

        self._lines = {}
        self._item_height = None
        self._custom_text = None
        self._delegate = delegate

    def get_placeholder_text(self):
        return self._placeholder_text

    def set_placeholder_text(self, text):
        self._placeholder_text = text

    def set_custom_text(self, text):
        self._custom_text = text
        self.update()
        self.updateGeometry()

    def focusInEvent(self, event):
        self.focused_in.emit()
        return super(MultiSelectionComboBox, self).focusInEvent(event)

    def mousePressEvent(self, event):
        """Reimplemented."""
        self._popup_is_shown = False
        super(MultiSelectionComboBox, self).mousePressEvent(event)
        if self._popup_is_shown:
            self._initial_mouse_pos = self.mapToGlobal(event.pos())
            self._block_mouse_release_timer.start(
                QtWidgets.QApplication.doubleClickInterval()
            )

    def showPopup(self):
        """Reimplemented."""
        super(MultiSelectionComboBox, self).showPopup()
        view = self.view()
        view.installEventFilter(self)
        view.viewport().installEventFilter(self)
        self._popup_is_shown = True

    def hidePopup(self):
        """Reimplemented."""
        self.view().removeEventFilter(self)
        self.view().viewport().removeEventFilter(self)
        self._popup_is_shown = False
        self._initial_mouse_pos = None
        super(MultiSelectionComboBox, self).hidePopup()
        self.view().clearFocus()

    def _event_popup_shown(self, obj, event):
        if not self._popup_is_shown:
            return

        current_index = self.view().currentIndex()
        model = self.model()

        if event.type() == QtCore.QEvent.MouseMove:
            if (
                self.view().isVisible()
                and self._initial_mouse_pos is not None
                and self._block_mouse_release_timer.isActive()
            ):
                diff = obj.mapToGlobal(event.pos()) - self._initial_mouse_pos
                if diff.manhattanLength() > 9:
                    self._block_mouse_release_timer.stop()
            return

        index_flags = current_index.flags()
        state = checkstate_int_to_enum(
            current_index.data(QtCore.Qt.CheckStateRole)
        )
        new_state = None

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if (
                self._block_mouse_release_timer.isActive()
                or not current_index.isValid()
                or not self.view().isVisible()
                or not self.view().rect().contains(event.pos())
                or not index_flags & QtCore.Qt.ItemIsSelectable
                or not index_flags & QtCore.Qt.ItemIsEnabled
                or not index_flags & QtCore.Qt.ItemIsUserCheckable
            ):
                return

            if state == QtCore.Qt.Unchecked:
                new_state = CHECKED_INT
            else:
                new_state = UNCHECKED_INT

        elif event.type() == QtCore.QEvent.KeyPress:
            # TODO: handle QtCore.Qt.Key_Enter, Key_Return?
            if event.key() == QtCore.Qt.Key_Space:
                if (
                    index_flags & QtCore.Qt.ItemIsUserCheckable
                    and index_flags & ITEM_IS_USER_TRISTATE
                ):
                    new_state = (checkstate_enum_to_int(state) + 1) % 3

                elif index_flags & QtCore.Qt.ItemIsUserCheckable:
                    # toggle the current items check state
                    if state != QtCore.Qt.Checked:
                        new_state = CHECKED_INT
                    else:
                        new_state = UNCHECKED_INT

        if new_state is not None:
            model.setData(current_index, new_state, QtCore.Qt.CheckStateRole)
            self.view().update(current_index)
            self._update_size_hint()
            self.value_changed.emit()
            return True

    def eventFilter(self, obj, event):
        """Reimplemented."""
        result = self._event_popup_shown(obj, event)
        if result is not None:
            return result

        return super(MultiSelectionComboBox, self).eventFilter(obj, event)

    def addItem(self, *args, **kwargs):
        idx = self.count()
        super(MultiSelectionComboBox, self).addItem(*args, **kwargs)
        self.model().item(idx).setCheckable(True)

    def paintEvent(self, event):
        """Reimplemented."""
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, option)

        items = self.checked_items_text()
        # draw the icon and text
        draw_text = True
        combotext = None
        if self._custom_text is not None:
            combotext = self._custom_text
        elif not items:
            combotext = self._placeholder_text
        else:
            draw_text = False
        if draw_text:
            option.currentText = combotext
            option.palette.setCurrentColorGroup(QtGui.QPalette.Disabled)
            painter.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, option)
            return

        font_metricts = self.fontMetrics()

        if self._item_height is None:
            self.updateGeometry()
            self.update()
            return

        for line, items in self._lines.items():
            top_y = (
                option.rect.top()
                + (line * self._item_height)
                + self.top_bottom_margins
            )
            left_x = option.rect.left() + self.left_offset
            for item in items:
                label_rect = font_metricts.boundingRect(item)
                label_height = label_rect.height()

                label_rect.moveTop(top_y)
                label_rect.moveLeft(left_x)
                label_rect.setHeight(self._item_height)
                label_rect.setWidth(
                    label_rect.width() + self.left_right_padding
                )

                bg_rect = QtCore.QRectF(label_rect)
                bg_rect.setWidth(
                    label_rect.width() + self.left_right_padding
                )
                left_x = bg_rect.right() + self.item_spacing

                label_rect.moveLeft(label_rect.x() + self.left_right_padding)

                bg_rect.setHeight(label_height + (2 * self.top_bottom_padding))
                bg_rect.moveTop(bg_rect.top() + self.top_bottom_margins)

                path = QtGui.QPainterPath()
                path.addRoundedRect(bg_rect, 5, 5)

                painter.fillPath(path, self.item_bg_color)

                painter.drawText(
                    label_rect,
                    QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                    item
                )

    def resizeEvent(self, *args, **kwargs):
        super(MultiSelectionComboBox, self).resizeEvent(*args, **kwargs)
        self._update_size_hint()

    def _update_size_hint(self):
        if self._custom_text is not None:
            self.update()
            return
        self._lines = {}

        items = self.checked_items_text()
        if not items:
            self.update()
            return

        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        btn_rect = self.style().subControlRect(
            QtWidgets.QStyle.CC_ComboBox,
            option,
            QtWidgets.QStyle.SC_ComboBoxArrow
        )
        total_width = option.rect.width() - btn_rect.width()

        line = 0
        self._lines = {line: []}

        font_metricts = self.fontMetrics()
        default_left_x = 0 + self.left_offset
        left_x = int(default_left_x)
        for item in items:
            rect = font_metricts.boundingRect(item)
            width = rect.width() + (2 * self.left_right_padding)
            right_x = left_x + width
            if right_x > total_width:
                left_x = int(default_left_x)
                if self._lines.get(line):
                    line += 1
                    self._lines[line] = [item]
                    left_x += width
                else:
                    self._lines[line] = [item]
                    line += 1
            else:
                if line in self._lines:
                    self._lines[line].append(item)
                else:
                    self._lines[line] = [item]
                left_x = left_x + width + self.item_spacing

        self.update()
        self.updateGeometry()

    def sizeHint(self):
        value = super(MultiSelectionComboBox, self).sizeHint()
        lines = 1
        if self._custom_text is None:
            lines = len(self._lines)
            if lines == 0:
                lines = 1

        if self._item_height is None:
            self._item_height = (
                self.fontMetrics().height()
                + (2 * self.top_bottom_padding)
                + (2 * self.top_bottom_margins)
            )
        value.setHeight(
            (lines * self._item_height)
            + (2 * self.top_bottom_margins)
        )
        return value

    def setItemCheckState(self, index, state):
        self.setItemData(index, state, QtCore.Qt.CheckStateRole)

    def set_value(self, values):
        for idx in range(self.count()):
            value = self.itemData(idx, role=QtCore.Qt.UserRole)
            if value in values:
                check_state = CHECKED_INT
            else:
                check_state = UNCHECKED_INT
            self.setItemData(idx, check_state, QtCore.Qt.CheckStateRole)
        self._update_size_hint()

    def value(self):
        items = list()
        for idx in range(self.count()):
            state = checkstate_int_to_enum(
                self.itemData(idx, role=QtCore.Qt.CheckStateRole)
            )
            if state == QtCore.Qt.Checked:
                items.append(
                    self.itemData(idx, role=QtCore.Qt.UserRole)
                )
        return items

    def checked_items_text(self):
        items = list()
        for idx in range(self.count()):
            state = checkstate_int_to_enum(
                self.itemData(idx, role=QtCore.Qt.CheckStateRole)
            )
            if state == QtCore.Qt.Checked:
                items.append(self.itemText(idx))
        return items

    def wheelEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        if (
            event.key() == QtCore.Qt.Key_Down
            and event.modifiers() & QtCore.Qt.AltModifier
        ):
            return self.showPopup()

        if event.key() in self.ignored_keys:
            return event.ignore()

        return super(MultiSelectionComboBox, self).keyPressEvent(event)
