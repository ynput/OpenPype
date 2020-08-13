from Qt import QtWidgets, QtCore


class ModifiedIntSpinBox(QtWidgets.QSpinBox):
    def __init__(self, *args, **kwargs):
        super(ModifiedIntSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(ModifiedIntSpinBox, self).wheelEvent(event)
        else:
            event.ignore()


class ModifiedFloatSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super(ModifiedFloatSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(ModifiedFloatSpinBox, self).wheelEvent(event)
        else:
            event.ignore()


class ClickableWidget(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(ClickableWidget, self).__init__(*args, **kwargs)
        self.setObjectName("ExpandLabel")

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class ExpandingWidget(QtWidgets.QWidget):
    def __init__(self, label, parent):
        super(ExpandingWidget, self).__init__(parent)
        self.setObjectName("ExpandingWidget")

        top_part = ClickableWidget(parent=self)

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=top_part)
        button_toggle.setProperty("btn-type", "expand-toggle")
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        label_widget = QtWidgets.QLabel(label, parent=top_part)
        label_widget.setObjectName("ExpandLabel")

        layout = QtWidgets.QHBoxLayout(top_part)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(button_toggle)
        layout.addWidget(label_widget)
        top_part.setLayout(layout)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        self.top_part = top_part
        self.button_toggle = button_toggle
        self.label_widget = label_widget

        self.top_part.clicked.connect(self._top_part_clicked)
        self.button_toggle.clicked.connect(self.toggle_content)

    def set_content_widget(self, content_widget):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(9, 9, 9, 9)

        content_widget.setVisible(False)

        main_layout.addWidget(self.top_part)
        main_layout.addWidget(content_widget)
        self.setLayout(main_layout)

        self.content_widget = content_widget

    def _top_part_clicked(self):
        self.toggle_content(not self.button_toggle.isChecked())

    def toggle_content(self, *args):
        if len(args) > 0:
            checked = args[0]
        else:
            checked = self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        self.content_widget.setVisible(checked)
        self.parent().updateGeometry()

    def resizeEvent(self, event):
        super(ExpandingWidget, self).resizeEvent(event)
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
