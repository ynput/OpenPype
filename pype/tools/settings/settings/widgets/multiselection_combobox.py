from Qt import QtCore, QtGui, QtWidgets


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


class ComboMenuDelegate(QtWidgets.QAbstractItemDelegate):
    """
    Helper styled delegate (mostly based on existing private Qt's
    delegate used by the QtWidgets.QComboBox). Used to style the popup like a
    menu. (e.g osx aqua style).
    """

    def paint(self, painter, option, index):
        menuopt = self._menu_style_option(option, index)
        if option.widget is not None:
            style = option.widget.style()
        else:
            style = QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_MenuItem, menuopt, painter,
                          option.widget)

    def sizeHint(self, option, index):
        menuopt = self._menu_style_option(option, index)
        if option.widget is not None:
            style = option.widget.style()
        else:
            style = QtWidgets.QApplication.style()
        return style.sizeFromContents(
            QtWidgets.QStyle.CT_MenuItem, menuopt, menuopt.rect.size(),
            option.widget
        )

    def _menu_style_option(self, option, index):
        menuoption = QtWidgets.QStyleOptionMenuItem()
        if option.widget:
            palette_source = option.widget.palette("QMenu")
        else:
            palette_source = QtWidgets.QApplication.palette("QMenu")

        palette = option.palette.resolve(palette_source)
        foreground = index.data(QtCore.Qt.ForegroundRole)
        if isinstance(foreground, (QtGui.QBrush, QtGui.QColor, QtGui.QPixmap)):
            foreground = QtGui.QBrush(foreground)
            palette.setBrush(QtGui.QPalette.Text, foreground)
            palette.setBrush(QtGui.QPalette.ButtonText, foreground)
            palette.setBrush(QtGui.QPalette.WindowText, foreground)

        background = index.data(QtCore.Qt.BackgroundRole)
        if isinstance(background, (QtGui.QBrush, QtGui.QColor, QtGui.QPixmap)):
            background = QtGui.QBrush(background)
            palette.setBrush(QtGui.QPalette.Background, background)

        menuoption.palette = palette

        decoration = index.data(QtCore.Qt.DecorationRole)
        if isinstance(decoration, QtGui.QIcon):
            menuoption.icon = decoration

        menuoption.menuItemType = QtWidgets.QStyleOptionMenuItem.Normal

        if index.flags() & QtCore.Qt.ItemIsUserCheckable:
            menuoption.checkType = QtWidgets.QStyleOptionMenuItem.NonExclusive
        else:
            menuoption.checkType = QtWidgets.QStyleOptionMenuItem.NotCheckable

        check = index.data(QtCore.Qt.CheckStateRole)
        menuoption.checked = check == QtCore.Qt.Checked

        if option.widget is not None:
            menuoption.font = option.widget.font()
        else:
            menuoption.font = QtWidgets.QApplication.font("QMenu")

        menuoption.maxIconWidth = option.decorationSize.width() + 4
        menuoption.rect = option.rect
        menuoption.menuRect = option.rect

        # menuoption.menuHasCheckableItems = True
        menuoption.tabWidth = 0
        # TODO: self.displayText(QVariant, QLocale)
        # TODO: Why is this not a QtWidgets.QStyledItemDelegate?
        menuoption.text = str(index.data(QtCore.Qt.DisplayRole))

        menuoption.fontMetrics = QtGui.QFontMetrics(menuoption.font)
        state = option.state & (
            QtWidgets.QStyle.State_MouseOver
            | QtWidgets.QStyle.State_Selected
            | QtWidgets.QStyle.State_Active
        )

        if index.flags() & QtCore.Qt.ItemIsEnabled:
            state = state | QtWidgets.QStyle.State_Enabled
            menuoption.palette.setCurrentColorGroup(QtGui.QPalette.Active)
        else:
            state = state & ~QtWidgets.QStyle.State_Enabled
            menuoption.palette.setCurrentColorGroup(QtGui.QPalette.Disabled)

        if menuoption.checked:
            state = state | QtWidgets.QStyle.State_On
        else:
            state = state | QtWidgets.QStyle.State_Off

        menuoption.state = state
        return menuoption


class CheckComboBox(QtWidgets.QComboBox):
    ignored_keys = {
        QtCore.Qt.Key_Up,
        QtCore.Qt.Key_Down,
        QtCore.Qt.Key_PageDown,
        QtCore.Qt.Key_PageUp,
        QtCore.Qt.Key_Home,
        QtCore.Qt.Key_End
    }

    def __init__(
        self, parent=None, placeholder_text="", separator=", ", **kwargs
    ):
        super(CheckComboBox, self).__init__(parent=parent, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._popup_is_shown = False
        # self.__supressPopupHide = False
        self._block_mouse_release_timer = QtCore.QTimer(self, singleShot=True)
        self._initial_mouse_pos = None
        self._separator = separator
        self._placeholder_text = placeholder_text
        self._update_item_delegate()

    def mousePressEvent(self, event):
        """Reimplemented."""
        self._popup_is_shown = False
        super(CheckComboBox, self).mousePressEvent(event)
        if self._popup_is_shown:
            self._initial_mouse_pos = self.mapToGlobal(event.pos())
            self._block_mouse_release_timer.start(
                QtWidgets.QApplication.doubleClickInterval()
            )

    def changeEvent(self, event):
        """Reimplemented."""
        if event.type() == QtCore.QEvent.StyleChange:
            self._update_item_delegate()
        super(CheckComboBox, self).changeEvent(event)

    def showPopup(self):
        """Reimplemented."""
        super(CheckComboBox, self).showPopup()
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
        super(CheckComboBox, self).hidePopup()
        self.view().clearFocus()

    def eventFilter(self, obj, event):
        """Reimplemented."""
        if (
            self._popup_is_shown
            and event.type() == QtCore.QEvent.MouseMove
            and self.view().isVisible()
            and self._initial_mouse_pos is not None
        ):
            diff = obj.mapToGlobal(event.pos()) - self._initial_mouse_pos
            if (
                diff.manhattanLength() > 9
                and self._block_mouse_release_timer.isActive()
            ):
                self._block_mouse_release_timer.stop()

        current_index = self.view().currentIndex()
        if (
            self._popup_is_shown
            and event.type() == QtCore.QEvent.MouseButtonRelease
            and self.view().isVisible()
            and self.view().rect().contains(event.pos())
            and current_index.isValid()
            and current_index.flags() & QtCore.Qt.ItemIsSelectable
            and current_index.flags() & QtCore.Qt.ItemIsEnabled
            and current_index.flags() & QtCore.Qt.ItemIsUserCheckable
            and self.view().visualRect(current_index).contains(event.pos())
            and not self._block_mouse_release_timer.isActive()
        ):
            model = self.model()
            index = self.view().currentIndex()
            state = model.data(index, QtCore.Qt.CheckStateRole)
            if state == QtCore.Qt.Unchecked:
                check_state = QtCore.Qt.Checked
            else:
                check_state = QtCore.Qt.Unchecked

            model.setData(index, check_state, QtCore.Qt.CheckStateRole)
            self.view().update(index)
            self.update()
            return True

        if self._popup_is_shown and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Space:
                # toogle the current items check state
                model = self.model()
                index = self.view().currentIndex()
                flags = model.flags(index)
                state = model.data(index, QtCore.Qt.CheckStateRole)
                if flags & QtCore.Qt.ItemIsUserCheckable and \
                        flags & QtCore.Qt.ItemIsTristate:
                    state = QtCore.Qt.CheckState((int(state) + 1) % 3)
                elif flags & QtCore.Qt.ItemIsUserCheckable:
                    state = (
                        QtCore.Qt.Checked
                        if state != QtCore.Qt.Checked
                        else QtCore.Qt.Unchecked
                    )
                model.setData(index, state, QtCore.Qt.CheckStateRole)
                self.view().update(index)
                self.update()
                return True
            # TODO: handle QtCore.Qt.Key_Enter, Key_Return?

        return super(CheckComboBox, self).eventFilter(obj, event)

    def paintEvent(self, event):
        """Reimplemented."""
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, option)
        # draw the icon and text
        items = self.checked_items_text()
        if not items:
            option.currentText = self._placeholder_text
            option.palette.setCurrentColorGroup(QtGui.QPalette.Disabled)
            painter.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, option)
            return

        # body_rect = QtCore.QRectF(option.rect)

        side_padding = 3
        item_spacing = 5
        font_metricts = self.fontMetrics()
        left_x = option.rect.left() + 2
        for item in items:
            rect = font_metricts.boundingRect(item)
            rect.moveTop(option.rect.y())

            label_height = rect.height()

            rect.moveLeft(left_x)
            rect.setHeight(option.rect.height())

            bg_rect = QtCore.QRect(rect)
            bg_rect.setWidth(rect.width() + (2 * side_padding))
            left_x = bg_rect.right() + item_spacing

            rect.moveLeft(rect.x() + side_padding)

            remainder_half = (option.rect.height() - label_height) / 2
            remainder_quarter = int(remainder_half / 2) + 1
            bg_rect.setHeight(label_height + remainder_half)
            bg_rect.moveTop(bg_rect.top() + remainder_quarter)

            path = QtGui.QPainterPath()
            path.addRoundedRect(bg_rect, 5, 5)

            painter.fillPath(path, QtGui.QColor("#38d39f"))

            painter.drawText(
                rect,
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                item
            )
        option.currentText = self._separator.join(items)
        # option.currentIcon = QtGui.QIcon()

    def setItemCheckState(self, index, state):
        self.setItemData(index, state, QtCore.Qt.CheckStateRole)

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
            self.showPopup()
            return

        if event.key() in self.ignored_keys:
            event.ignore()
            return

        return super(CheckComboBox, self).keyPressEvent(event)

    def _update_item_delegate(self):
        opt = QtWidgets.QStyleOptionComboBox()
        opt.initFrom(self)
        if self.style().styleHint(
            QtWidgets.QStyle.SH_ComboBox_Popup, opt, self
        ):
            delegate = ComboMenuDelegate(self)
        else:
            delegate = ComboItemDelegate(self)
        self.setItemDelegate(delegate)
