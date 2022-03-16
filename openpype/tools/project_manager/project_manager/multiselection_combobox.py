from Qt import QtCore, QtWidgets


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
    ignored_keys = {
        QtCore.Qt.Key_Up,
        QtCore.Qt.Key_Down,
        QtCore.Qt.Key_PageDown,
        QtCore.Qt.Key_PageUp,
        QtCore.Qt.Key_Home,
        QtCore.Qt.Key_End
    }

    def __init__(self, parent=None, **kwargs):
        super(MultiSelectionComboBox, self).__init__(parent=parent, **kwargs)
        self.setObjectName("MultiSelectionComboBox")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._popup_is_shown = False
        self._block_mouse_release_timer = QtCore.QTimer(self, singleShot=True)
        self._initial_mouse_pos = None
        self._delegate = ComboItemDelegate(self)
        self.setItemDelegate(self._delegate)

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
        state = current_index.data(QtCore.Qt.CheckStateRole)
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
                new_state = QtCore.Qt.Checked
            else:
                new_state = QtCore.Qt.Unchecked

        elif event.type() == QtCore.QEvent.KeyPress:
            # TODO: handle QtCore.Qt.Key_Enter, Key_Return?
            if event.key() == QtCore.Qt.Key_Space:
                # toggle the current items check state
                if (
                    index_flags & QtCore.Qt.ItemIsUserCheckable
                    and index_flags & QtCore.Qt.ItemIsTristate
                ):
                    new_state = QtCore.Qt.CheckState((int(state) + 1) % 3)

                elif index_flags & QtCore.Qt.ItemIsUserCheckable:
                    if state != QtCore.Qt.Checked:
                        new_state = QtCore.Qt.Checked
                    else:
                        new_state = QtCore.Qt.Unchecked

        if new_state is not None:
            model.setData(current_index, new_state, QtCore.Qt.CheckStateRole)
            self.view().update(current_index)
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

        # draw the icon and text
        items = self.checked_items_text()
        if not items:
            return

        text_rect = self.style().subControlRect(
            QtWidgets.QStyle.CC_ComboBox,
            option,
            QtWidgets.QStyle.SC_ComboBoxEditField
        )
        text = ", ".join(items)
        new_text = self.fontMetrics().elidedText(
            text, QtCore.Qt.ElideRight, text_rect.width()
        )
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            new_text
        )

    def setItemCheckState(self, index, state):
        self.setItemData(index, state, QtCore.Qt.CheckStateRole)

    def set_value(self, values):
        for idx in range(self.count()):
            value = self.itemData(idx, role=QtCore.Qt.UserRole)
            if value in values:
                check_state = QtCore.Qt.Checked
            else:
                check_state = QtCore.Qt.Unchecked
            self.setItemData(idx, check_state, QtCore.Qt.CheckStateRole)

    def value(self):
        items = list()
        for idx in range(self.count()):
            state = self.itemData(idx, role=QtCore.Qt.CheckStateRole)
            if state == QtCore.Qt.Checked:
                items.append(
                    self.itemData(idx, role=QtCore.Qt.UserRole)
                )
        return items

    def checked_items_text(self):
        items = list()
        for idx in range(self.count()):
            state = self.itemData(idx, role=QtCore.Qt.CheckStateRole)
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
