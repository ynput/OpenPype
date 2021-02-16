from Qt import QtWidgets, QtCore, QtGui
from avalon.vendor import qtawesome


class ShadowWidget(QtWidgets.QWidget):
    def __init__(self, message, parent):
        super(ShadowWidget, self).__init__(parent)
        self.setObjectName("ShadowWidget")

        self.parent_widget = parent
        self.message = message

        def wrapper(func):
            def wrapped(*args, **kwarg):
                result = func(*args, **kwarg)
                self._update_geometry()
                return result
            return wrapped

        parent.resizeEvent = wrapper(parent.resizeEvent)
        parent.moveEvent = wrapper(parent.moveEvent)
        parent.showEvent = wrapper(parent.showEvent)

    def set_message(self, message):
        self.message = message
        if self.isVisible():
            self.repaint()

    def _update_geometry(self):
        self.setGeometry(self.parent_widget.rect())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(
            event.rect(), QtGui.QBrush(QtGui.QColor(0, 0, 0, 127))
        )
        if self.message:
            painter.drawText(
                event.rect(),
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter,
                self.message
            )
        painter.end()


class IconButton(QtWidgets.QPushButton):
    def __init__(self, icon_name, color, hover_color, *args, **kwargs):
        super(IconButton, self).__init__(*args, **kwargs)

        self.icon = qtawesome.icon(icon_name, color=color)
        self.hover_icon = qtawesome.icon(icon_name, color=hover_color)

        self.setIcon(self.icon)

    def enterEvent(self, event):
        self.setIcon(self.hover_icon)
        super(IconButton, self).enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self.icon)
        super(IconButton, self).leaveEvent(event)


class NumberSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        min_value = kwargs.pop("minimum", -99999)
        max_value = kwargs.pop("maximum", 99999)
        decimals = kwargs.pop("decimal", 0)
        super(NumberSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setDecimals(decimals)
        self.setMinimum(min_value)
        self.setMaximum(max_value)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(NumberSpinBox, self).wheelEvent(event)
        else:
            event.ignore()

    def value(self):
        output = super(NumberSpinBox, self).value()
        if self.decimals() == 0:
            output = int(output)
        return output


class ComboBox(QtWidgets.QComboBox):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(ComboBox, self).__init__(*args, **kwargs)

        self.currentIndexChanged.connect(self._on_change)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            return super(ComboBox, self).wheelEvent(event)

    def _on_change(self, *args, **kwargs):
        self.value_changed.emit()

    def set_value(self, value):
        for idx in range(self.count()):
            _value = self.itemData(idx, role=QtCore.Qt.UserRole)
            if _value == value:
                self.setCurrentIndex(idx)
                break

    def value(self):
        return self.itemData(self.currentIndex(), role=QtCore.Qt.UserRole)


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class ExpandingWidget(QtWidgets.QWidget):
    def __init__(self, label, parent):
        super(ExpandingWidget, self).__init__(parent)

        self.content_widget = None
        self.toolbox_hidden = False

        top_part = ClickableWidget(parent=self)

        side_line_widget = QtWidgets.QWidget(top_part)
        side_line_widget.setObjectName("SideLineWidget")

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=side_line_widget)
        button_toggle.setProperty("btn-type", "expand-toggle")
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        label_widget = QtWidgets.QLabel(label, parent=side_line_widget)
        label_widget.setObjectName("DictLabel")

        before_label_widget = QtWidgets.QWidget(side_line_widget)
        before_label_layout = QtWidgets.QHBoxLayout(before_label_widget)
        before_label_layout.setContentsMargins(0, 0, 0, 0)

        after_label_widget = QtWidgets.QWidget(side_line_widget)
        after_label_layout = QtWidgets.QHBoxLayout(after_label_widget)
        after_label_layout.setContentsMargins(0, 0, 0, 0)

        spacer_widget = QtWidgets.QWidget(side_line_widget)

        side_line_layout = QtWidgets.QHBoxLayout(side_line_widget)
        side_line_layout.setContentsMargins(5, 10, 0, 10)
        side_line_layout.addWidget(button_toggle)
        side_line_layout.addWidget(before_label_widget)
        side_line_layout.addWidget(label_widget)
        side_line_layout.addWidget(after_label_widget)
        side_line_layout.addWidget(spacer_widget, 1)

        top_part_layout = QtWidgets.QHBoxLayout(top_part)
        top_part_layout.setContentsMargins(0, 0, 0, 0)
        top_part_layout.addWidget(side_line_widget)

        before_label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        after_label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        spacer_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.top_part_ending = None
        self.after_label_layout = after_label_layout
        self.before_label_layout = before_label_layout

        self.side_line_widget = side_line_widget
        self.side_line_layout = side_line_layout
        self.button_toggle = button_toggle
        self.label_widget = label_widget

        top_part.clicked.connect(self._top_part_clicked)
        self.button_toggle.clicked.connect(self._btn_clicked)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(top_part)

    def hide_toolbox(self, hide_content=False):
        self.button_toggle.setArrowType(QtCore.Qt.NoArrow)
        self.toolbox_hidden = True
        if self.content_widget:
            self.content_widget.setVisible(not hide_content)
        self.parent().updateGeometry()

    def show_toolbox(self):
        self.toolbox_hidden = False
        self.toggle_content(self.button_toggle.isChecked())

        self.parent().updateGeometry()

    def set_content_widget(self, content_widget):
        content_widget.setVisible(False)
        self.main_layout.addWidget(content_widget)
        self.content_widget = content_widget

    def _btn_clicked(self):
        self.toggle_content(self.button_toggle.isChecked())

    def _top_part_clicked(self):
        self.toggle_content()

    def toggle_content(self, *args):
        if self.toolbox_hidden:
            return

        if len(args) > 0:
            checked = args[0]
        else:
            checked = not self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        if self.content_widget:
            self.content_widget.setVisible(checked)
        self.parent().updateGeometry()

    def add_widget_after_label(self, widget):
        self.after_label_layout.addWidget(widget)

    def add_widget_before_label(self, widget):
        self.before_label_layout.addWidget(widget)

    def resizeEvent(self, event):
        super(ExpandingWidget, self).resizeEvent(event)
        if self.content_widget:
            self.content_widget.updateGeometry()


class UnsavedChangesDialog(QtWidgets.QDialog):
    message = "You have unsaved changes. What do you want to do with them?"

    def __init__(self, parent=None):
        super().__init__(parent)
        message_label = QtWidgets.QLabel(self.message)

        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        btn_ok = QtWidgets.QPushButton("Save")
        btn_ok.clicked.connect(self.on_ok_pressed)
        btn_discard = QtWidgets.QPushButton("Discard")
        btn_discard.clicked.connect(self.on_discard_pressed)
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.on_cancel_pressed)

        btns_layout.addWidget(btn_ok)
        btns_layout.addWidget(btn_discard)
        btns_layout.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(message_label)
        layout.addWidget(btns_widget)

        self.state = None

    def on_cancel_pressed(self):
        self.done(0)

    def on_ok_pressed(self):
        self.done(1)

    def on_discard_pressed(self):
        self.done(2)


class SpacerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SpacerWidget, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)


class GridLabelWidget(QtWidgets.QWidget):
    def __init__(self, label, parent=None):
        super(GridLabelWidget, self).__init__(parent)

        self.input_field = None

        self.properties = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)

        label_proxy = QtWidgets.QWidget(self)

        label_proxy_layout = QtWidgets.QHBoxLayout(label_proxy)
        label_proxy_layout.setContentsMargins(0, 0, 0, 0)
        label_proxy_layout.setSpacing(0)

        label_widget = QtWidgets.QLabel(label, label_proxy)
        spacer_widget_h = SpacerWidget(label_proxy)
        label_proxy_layout.addWidget(
            spacer_widget_h, 0, alignment=QtCore.Qt.AlignRight
        )
        label_proxy_layout.addWidget(
            label_widget, 0, alignment=QtCore.Qt.AlignRight
        )

        spacer_widget_v = SpacerWidget(self)

        layout.addWidget(label_proxy, 0)
        layout.addWidget(spacer_widget_v, 1)

        label_proxy.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.label_widget = label_widget

    def setProperty(self, name, value):
        cur_value = self.properties.get(name)
        if cur_value == value:
            return

        self.label_widget.setProperty(name, value)
        self.label_widget.style().polish(self.label_widget)

    def mouseReleaseEvent(self, event):
        if self.input_field:
            return self.input_field.show_actions_menu(event)
        return super(GridLabelWidget, self).mouseReleaseEvent(event)


class NiceCheckboxMoveWidget(QtWidgets.QFrame):
    def __init__(self, height, border_width, parent):
        super(NiceCheckboxMoveWidget, self).__init__(parent=parent)

        self.checkstate = False

        self.half_size = int(height / 2)
        self.full_size = self.half_size * 2
        self.border_width = border_width
        self.setFixedHeight(self.full_size)
        self.setFixedWidth(self.full_size)

        self.setStyleSheet((
            "background: #444444;border-style: none;"
            "border-radius: {};border-width:{}px;"
        ).format(self.half_size, self.border_width))

    def update_position(self):
        parent_rect = self.parent().rect()
        if self.checkstate is True:
            pos_x = (
                parent_rect.x()
                + parent_rect.width()
                - self.full_size
                - self.border_width
            )
        else:
            pos_x = parent_rect.x() + self.border_width

        pos_y = parent_rect.y() + int(
            parent_rect.height() / 2 - self.half_size
        )
        self.setGeometry(pos_x, pos_y, self.width(), self.height())

    def state_offset(self):
        diff_x = (
            self.parent().rect().width()
            - self.full_size
            - (2 * self.border_width)
        )
        return QtCore.QPoint(diff_x, 0)

    def change_position(self, checkstate):
        self.checkstate = checkstate

        self.update_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_position()


class NiceCheckbox(QtWidgets.QFrame):
    stateChanged = QtCore.Signal(int)
    checked_bg_color = QtGui.QColor(69, 128, 86)
    unchecked_bg_color = QtGui.QColor(170, 80, 80)

    def set_bg_color(self, color):
        self._bg_color = color
        self.setStyleSheet(self._stylesheet_template.format(
            color.red(), color.green(), color.blue()
        ))

    def bg_color(self):
        return self._bg_color

    bgcolor = QtCore.Property(QtGui.QColor, bg_color, set_bg_color)

    def __init__(self, checked=True, height=30, *args, **kwargs):
        super(NiceCheckbox, self).__init__(*args, **kwargs)

        self._checkstate = checked
        if checked:
            bg_color = self.checked_bg_color
        else:
            bg_color = self.unchecked_bg_color

        self.half_height = int(height / 2)
        height = self.half_height * 2
        tenth_height = int(height / 10)

        self.setFixedHeight(height)
        self.setFixedWidth((height - tenth_height) * 2)

        move_item_size = height - (2 * tenth_height)

        self.move_item = NiceCheckboxMoveWidget(
            move_item_size, tenth_height, self
        )
        self.move_item.change_position(self._checkstate)

        self._stylesheet_template = (
            "border-radius: {}px;"
            "border-width: {}px;"
            "background: #333333;"
            "border-style: solid;"
            "border-color: #555555;"
        ).format(self.half_height, tenth_height)
        self._stylesheet_template += "background: rgb({},{},{});"

        self.set_bg_color(bg_color)

    def resizeEvent(self, event):
        super(NiceCheckbox, self).resizeEvent(event)
        self.move_item.update_position()

    def show(self, *args, **kwargs):
        super(NiceCheckbox, self).show(*args, **kwargs)
        self.move_item.update_position()

    def checkState(self):
        if self._checkstate:
            return QtCore.Qt.Checked
        else:
            return QtCore.Qt.Unchecked

    def _on_checkstate_change(self):
        self.stateChanged.emit(self.checkState())

        move_start_value = self.move_item.pos()
        offset = self.move_item.state_offset()
        if self._checkstate is True:
            move_end_value = move_start_value + offset
        else:
            move_end_value = move_start_value - offset
        move_animation = QtCore.QPropertyAnimation(
            self.move_item, b"pos", self
        )
        move_animation.setDuration(150)
        move_animation.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        move_animation.setStartValue(move_start_value)
        move_animation.setEndValue(move_end_value)

        color_animation = QtCore.QPropertyAnimation(
            self, b"bgcolor"
        )
        color_animation.setDuration(150)
        if self._checkstate is True:
            color_animation.setStartValue(self.unchecked_bg_color)
            color_animation.setEndValue(self.checked_bg_color)
        else:
            color_animation.setStartValue(self.checked_bg_color)
            color_animation.setEndValue(self.unchecked_bg_color)

        anim_group = QtCore.QParallelAnimationGroup(self)
        anim_group.addAnimation(move_animation)
        anim_group.addAnimation(color_animation)

        def _finished():
            self.move_item.change_position(self._checkstate)

        anim_group.finished.connect(_finished)
        anim_group.start()

    def isChecked(self):
        return self._checkstate

    def setChecked(self, checked):
        if checked == self._checkstate:
            return
        self._checkstate = checked
        self._on_checkstate_change()

    def setCheckState(self, state=None):
        if state is None:
            checkstate = not self._checkstate
        elif state == QtCore.Qt.Checked:
            checkstate = True
        elif state == QtCore.Qt.Unchecked:
            checkstate = False
        else:
            return

        if checkstate == self._checkstate:
            return

        self._checkstate = checkstate

        self._on_checkstate_change()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setCheckState()
            event.accept()
            return
        return super(NiceCheckbox, self).mouseReleaseEvent(event)
