from Qt import QtWidgets, QtCore


class FlameLabel(QtWidgets.QLabel):
    """
    Custom Qt Flame Label Widget

    For different label looks set label_type as:
        'normal', 'background', or 'outline'

    To use:

    label = FlameLabel('Label Name', 'normal', window)
    """

    def __init__(self, label_name, label_type, parent_window, *args, **kwargs):
        super(FlameLabel, self).__init__(*args, **kwargs)

        self.setText(label_name)
        self.setParent(parent_window)
        self.setMinimumSize(130, 28)
        self.setMaximumHeight(28)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        # Set label stylesheet based on label_type

        if label_type == 'normal':
            self.setStyleSheet(
                'QLabel {color: #9a9a9a; border-bottom: 1px inset #282828; font: 14px "Discreet"}'  # noqa
                'QLabel:disabled {color: #6a6a6a}'
            )
        elif label_type == 'background':
            self.setAlignment(QtCore.Qt.AlignCenter)
            self.setStyleSheet(
                'color: #9a9a9a; background-color: #393939; font: 14px "Discreet"'  # noqa
            )
        elif label_type == 'outline':
            self.setAlignment(QtCore.Qt.AlignCenter)
            self.setStyleSheet(
                'color: #9a9a9a; background-color: #212121; border: 1px solid #404040; font: 14px "Discreet"'  # noqa
            )


class FlameLineEdit(QtWidgets.QLineEdit):
    """
    Custom Qt Flame Line Edit Widget

    Main window should include this:
        window.setFocusPolicy(QtCore.Qt.StrongFocus)

    To use:

    line_edit = FlameLineEdit('Some text here', window)
    """

    def __init__(self, text, parent_window, *args, **kwargs):
        super(FlameLineEdit, self).__init__(*args, **kwargs)

        self.setText(text)
        self.setParent(parent_window)
        self.setMinimumHeight(28)
        self.setMinimumWidth(110)
        self.setStyleSheet(
            'QLineEdit {color: #9a9a9a; background-color: #373e47; selection-color: #262626; selection-background-color: #b8b1a7; font: 14px "Discreet"}'  # noqa
            'QLineEdit:focus {background-color: #474e58}'  # noqa
            'QLineEdit:disabled {color: #6a6a6a; background-color: #373737}'
        )


class FlameTreeWidget(QtWidgets.QTreeWidget):
    """
    Custom Qt Flame Tree Widget

    To use:

    tree_headers = ['Header1', 'Header2', 'Header3', 'Header4']
    tree = FlameTreeWidget(tree_headers, window)
    """

    def __init__(self, tree_headers, parent_window, *args, **kwargs):
        super(FlameTreeWidget, self).__init__(*args, **kwargs)

        self.setMinimumWidth(1000)
        self.setMinimumHeight(300)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.setAlternatingRowColors(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet(
            'QTreeWidget {color: #9a9a9a; background-color: #2a2a2a; alternate-background-color: #2d2d2d; font: 14px "Discreet"}'  # noqa
            'QTreeWidget::item:selected {color: #d9d9d9; background-color: #474747; border: 1px solid #111111}'  # noqa
            'QHeaderView {color: #9a9a9a; background-color: #393939; font: 14px "Discreet"}'  # noqa
            'QTreeWidget::item:selected {selection-background-color: #111111}'
            'QMenu {color: #9a9a9a; background-color: #24303d; font: 14px "Discreet"}'  # noqa
            'QMenu::item:selected {color: #d9d9d9; background-color: #3a4551}'
        )
        self.verticalScrollBar().setStyleSheet('color: #818181')
        self.horizontalScrollBar().setStyleSheet('color: #818181')
        self.setHeaderLabels(tree_headers)


class FlameButton(QtWidgets.QPushButton):
    """
    Custom Qt Flame Button Widget

    To use:

    button = FlameButton('Button Name', do_this_when_pressed, window)
    """

    def __init__(self, button_name, do_when_pressed, parent_window,
                 *args, **kwargs):
        super(FlameButton, self).__init__(*args, **kwargs)

        self.setText(button_name)
        self.setParent(parent_window)
        self.setMinimumSize(QtCore.QSize(110, 28))
        self.setMaximumSize(QtCore.QSize(110, 28))
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.clicked.connect(do_when_pressed)
        self.setStyleSheet(
            'QPushButton {color: #9a9a9a; background-color: #424142; border-top: 1px inset #555555; border-bottom: 1px inset black; font: 14px "Discreet"}'  # noqa
            'QPushButton:pressed {color: #d9d9d9; background-color: #4f4f4f; border-top: 1px inset #666666; font: italic}'  # noqa
           'QPushButton:disabled {color: #747474; background-color: #353535; border-top: 1px solid #444444; border-bottom: 1px solid #242424}'  # noqa
        )


class FlamePushButton(QtWidgets.QPushButton):
    """
    Custom Qt Flame Push Button Widget

    To use:

    pushbutton = FlamePushButton(' Button Name', True_or_False, window)
    """

    def __init__(self, button_name, button_checked, parent_window,
                 *args, **kwargs):
        super(FlamePushButton, self).__init__(*args, **kwargs)

        self.setText(button_name)
        self.setParent(parent_window)
        self.setCheckable(True)
        self.setChecked(button_checked)
        self.setMinimumSize(155, 28)
        self.setMaximumSize(155, 28)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet(
            'QPushButton {color: #9a9a9a; background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: .93 #424142, stop: .94 #2e3b48); text-align: left; border-top: 1px inset #555555; border-bottom: 1px inset black; font: 14px "Discreet"}'  # noqa
            'QPushButton:checked {color: #d9d9d9; background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: .93 #4f4f4f, stop: .94 #5a7fb4); font: italic; border: 1px inset black; border-bottom: 1px inset #404040; border-right: 1px inset #404040}'  # noqa
            'QPushButton:disabled {color: #6a6a6a; background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: .93 #383838, stop: .94 #353535); font: light; border-top: 1px solid #575757; border-bottom: 1px solid #242424; border-right: 1px solid #353535; border-left: 1px solid #353535}'  # noqa
            'QToolTip {color: black; background-color: #ffffde; border: black solid 1px}'  # noqa
        )


class FlamePushButtonMenu(QtWidgets.QPushButton):
    """
    Custom Qt Flame Menu Push Button Widget

    To use:

    push_button_menu_options = ['Item 1', 'Item 2', 'Item 3', 'Item 4']
    menu_push_button = FlamePushButtonMenu('push_button_name',
    push_button_menu_options, window)

    or

    push_button_menu_options = ['Item 1', 'Item 2', 'Item 3', 'Item 4']
    menu_push_button = FlamePushButtonMenu(push_button_menu_options[0],
    push_button_menu_options, window)
    """
    selection_changed = QtCore.Signal(str)

    def __init__(self, button_name, menu_options, parent_window,
                 *args, **kwargs):
        super(FlamePushButtonMenu, self).__init__(*args, **kwargs)

        self.setParent(parent_window)
        self.setMinimumHeight(28)
        self.setMinimumWidth(110)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet(
            'QPushButton {color: #9a9a9a; background-color: #24303d; font: 14px "Discreet"}'  # noqa
            'QPushButton:disabled {color: #747474; background-color: #353535; border-top: 1px solid #444444; border-bottom: 1px solid #242424}'  # noqa
        )

        pushbutton_menu = QtWidgets.QMenu(parent_window)
        pushbutton_menu.setFocusPolicy(QtCore.Qt.NoFocus)
        pushbutton_menu.setStyleSheet(
            'QMenu {color: #9a9a9a; background-color:#24303d; font: 14px "Discreet"}'  # noqa
            'QMenu::item:selected {color: #d9d9d9; background-color: #3a4551}'
        )

        self._pushbutton_menu = pushbutton_menu
        self.setMenu(pushbutton_menu)
        self.set_menu_options(menu_options, button_name)

    def set_menu_options(self, menu_options, current_option=None):
        self._pushbutton_menu.clear()
        current_option = current_option or menu_options[0]

        for option in menu_options:
            action = self._pushbutton_menu.addAction(option)
            action.triggered.connect(self._on_action_trigger)

        if current_option is not None:
            self.setText(current_option)

    def _on_action_trigger(self):
        action = self.sender()
        self.setText(action.text())
        self.selection_changed.emit(action.text())
