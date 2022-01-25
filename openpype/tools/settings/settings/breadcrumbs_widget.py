from Qt import QtWidgets, QtGui, QtCore

PREFIX_ROLE = QtCore.Qt.UserRole + 1
LAST_SEGMENT_ROLE = QtCore.Qt.UserRole + 2


class BreadcrumbItem(QtGui.QStandardItem):
    def __init__(self, *args, **kwargs):
        self._display_value = None
        self._edit_value = None
        super(BreadcrumbItem, self).__init__(*args, **kwargs)

    def data(self, role=None):
        if role == QtCore.Qt.DisplayRole:
            return self._display_value

        if role == QtCore.Qt.EditRole:
            return self._edit_value

        if role is None:
            args = tuple()
        else:
            args = (role, )
        return super(BreadcrumbItem, self).data(*args)

    def setData(self, value, role):
        if role == QtCore.Qt.DisplayRole:
            self._display_value = value
            return True

        if role == QtCore.Qt.EditRole:
            self._edit_value = value
            return True

        if role is None:
            args = (value, )
        else:
            args = (value, role)
        return super(BreadcrumbItem, self).setData(*args)


class BreadcrumbsModel(QtGui.QStandardItemModel):
    def __init__(self):
        super(BreadcrumbsModel, self).__init__()
        self.current_path = ""

        self.reset()

    def reset(self):
        return


class SettingsBreadcrumbs(BreadcrumbsModel):
    def __init__(self):
        self.entity = None

        self.entities_by_path = {}
        self.dynamic_paths = set()

        super(SettingsBreadcrumbs, self).__init__()

    def set_entity(self, entity):
        self.entities_by_path = {}
        self.dynamic_paths = set()
        self.entity = entity
        self.reset()

    def has_children(self, path):
        for key in self.entities_by_path.keys():
            if key.startswith(path):
                return True
        return False

    def get_valid_path(self, path):
        if not path:
            return ""

        path_items = path.split("/")
        new_path_items = []
        entity = self.entity
        for item in path_items:
            if not entity.has_child_with_key(item):
                break

            new_path_items.append(item)
            entity = entity[item]

        return "/".join(new_path_items)

    def is_valid_path(self, path):
        if not path:
            return True

        path_items = path.split("/")

        entity = self.entity
        for item in path_items:
            if not entity.has_child_with_key(item):
                return False

            entity = entity[item]

        return True


class SystemSettingsBreadcrumbs(SettingsBreadcrumbs):
    def reset(self):
        root_item = self.invisibleRootItem()
        rows = root_item.rowCount()
        if rows > 0:
            root_item.removeRows(0, rows)

        if self.entity is None:
            return

        entities_by_path = self.entity.collect_static_entities_by_path()
        self.entities_by_path = entities_by_path
        items = []
        for path in entities_by_path.keys():
            if not path:
                continue
            path_items = path.split("/")
            value = path
            label = path_items.pop(-1)
            prefix = "/".join(path_items)
            if prefix:
                prefix += "/"

            item = QtGui.QStandardItem(value)
            item.setData(label, LAST_SEGMENT_ROLE)
            item.setData(prefix, PREFIX_ROLE)

            items.append(item)

        root_item.appendRows(items)


class ProjectSettingsBreadcrumbs(SettingsBreadcrumbs):
    def reset(self):
        root_item = self.invisibleRootItem()
        rows = root_item.rowCount()
        if rows > 0:
            root_item.removeRows(0, rows)

        if self.entity is None:
            return

        entities_by_path = self.entity.collect_static_entities_by_path()
        self.entities_by_path = entities_by_path
        items = []
        for path in entities_by_path.keys():
            if not path:
                continue
            path_items = path.split("/")
            value = path
            label = path_items.pop(-1)
            prefix = "/".join(path_items)
            if prefix:
                prefix += "/"

            item = QtGui.QStandardItem(value)
            item.setData(label, LAST_SEGMENT_ROLE)
            item.setData(prefix, PREFIX_ROLE)

            items.append(item)

        root_item.appendRows(items)


class BreadcrumbsProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(BreadcrumbsProxy, self).__init__(*args, **kwargs)

        self._current_path = ""

    def set_path_prefix(self, prefix):
        path = prefix
        if not prefix.endswith("/"):
            path_items = path.split("/")
            if len(path_items) == 1:
                path = ""
            else:
                path_items.pop(-1)
                path = "/".join(path_items) + "/"

        if path == self._current_path:
            return

        self._current_path = prefix

        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        index = self.sourceModel().index(row, 0, parent)
        prefix_path = index.data(PREFIX_ROLE)
        return prefix_path == self._current_path


class BreadcrumbsHintMenu(QtWidgets.QMenu):
    def __init__(self, model, path_prefix, parent):
        super(BreadcrumbsHintMenu, self).__init__(parent)

        self._path_prefix = path_prefix
        self._model = model

    def showEvent(self, event):
        self.clear()

        self._model.set_path_prefix(self._path_prefix)

        row_count = self._model.rowCount()
        if row_count == 0:
            action = self.addAction("* Nothing")
            action.setData(".")
        else:
            for row in range(self._model.rowCount()):
                index = self._model.index(row, 0)
                label = index.data(LAST_SEGMENT_ROLE)
                value = index.data(QtCore.Qt.EditRole)
                action = self.addAction(label)
                action.setData(value)

        super(BreadcrumbsHintMenu, self).showEvent(event)


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class BreadcrumbsPathInput(QtWidgets.QLineEdit):
    cancelled = QtCore.Signal()
    confirmed = QtCore.Signal()

    def __init__(self, model, proxy_model, parent):
        super(BreadcrumbsPathInput, self).__init__(parent)

        self.setObjectName("BreadcrumbsPathInput")

        self.setFrame(False)

        completer = QtWidgets.QCompleter(self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setModel(proxy_model)

        popup = completer.popup()
        popup.setUniformItemSizes(True)
        popup.setLayoutMode(QtWidgets.QListView.Batched)

        self.setCompleter(completer)

        completer.activated.connect(self._on_completer_activated)
        self.textEdited.connect(self._on_text_change)

        self._completer = completer
        self._model = model
        self._proxy_model = proxy_model

        self._context_menu_visible = False

    def set_model(self, model):
        self._model = model

    def event(self, event):
        if (
            event.type() == QtCore.QEvent.KeyPress
            and event.key() == QtCore.Qt.Key_Tab
        ):
            if self._model:
                find_value = self.text() + "/"
                if self._model.has_children(find_value):
                    self.insert("/")
                else:
                    self._completer.popup().hide()
                event.accept()
                return True

        return super(BreadcrumbsPathInput, self).event(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.cancelled.emit()
            return

        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.confirmed.emit()
            return

        super(BreadcrumbsPathInput, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        if not self._context_menu_visible:
            self.cancelled.emit()

        self._context_menu_visible = False
        super(BreadcrumbsPathInput, self).focusOutEvent(event)

    def contextMenuEvent(self, event):
        self._context_menu_visible = True
        super(BreadcrumbsPathInput, self).contextMenuEvent(event)

    def _on_completer_activated(self, path):
        self.confirmed.emit()

    def _on_text_change(self, path):
        self._proxy_model.set_path_prefix(path)


class BreadcrumbsButton(QtWidgets.QToolButton):
    path_selected = QtCore.Signal(str)

    def __init__(self, path, model, parent):
        super(BreadcrumbsButton, self).__init__(parent)

        self.setObjectName("BreadcrumbsButton")

        path_prefix = path
        if path:
            path_prefix += "/"

        self.setAutoRaise(True)
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        self.setMouseTracking(True)

        if path:
            self.setText(path.split("/")[-1])
        else:
            self.setProperty("empty", "1")

        menu = BreadcrumbsHintMenu(model, path_prefix, self)

        self.setMenu(menu)

        # fixed size breadcrumbs
        self.setMinimumSize(self.minimumSizeHint())
        size_policy = self.sizePolicy()
        size_policy.setVerticalPolicy(size_policy.Minimum)
        self.setSizePolicy(size_policy)

        menu.triggered.connect(self._on_menu_click)
        # Don't allow to go to root with mouse click
        if path:
            self.clicked.connect(self._on_click)

        self._path = path
        self._path_prefix = path_prefix
        self._model = model
        self._menu = menu

    def _on_click(self):
        self.path_selected.emit(self._path)

    def _on_menu_click(self, action):
        item = action.data()
        self.path_selected.emit(item)


class BreadcrumbsAddressBar(QtWidgets.QFrame):
    "Windows Explorer-like address bar"
    path_changed = QtCore.Signal(str)
    path_edited = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(BreadcrumbsAddressBar, self).__init__(parent)

        self.setAutoFillBackground(True)
        self.setFrameShape(self.StyledPanel)

        # Edit presented path textually
        proxy_model = BreadcrumbsProxy()
        path_input = BreadcrumbsPathInput(None, proxy_model, self)
        path_input.setVisible(False)

        path_input.cancelled.connect(self._on_input_cancel)
        path_input.confirmed.connect(self._on_input_confirm)

        # Container for `crumbs_panel`
        crumbs_container = QtWidgets.QWidget(self)

        # Container for breadcrumbs
        crumbs_panel = QtWidgets.QWidget(crumbs_container)
        crumbs_panel.setObjectName("BreadcrumbsPanel")

        crumbs_layout = QtWidgets.QHBoxLayout()
        crumbs_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_layout.setSpacing(0)

        crumbs_cont_layout = QtWidgets.QHBoxLayout(crumbs_container)
        crumbs_cont_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_cont_layout.setSpacing(0)
        crumbs_cont_layout.addWidget(crumbs_panel)

        # Clicking on empty space to the right puts the bar into edit mode
        switch_space = ClickableWidget(self)

        crumb_panel_layout = QtWidgets.QHBoxLayout(crumbs_panel)
        crumb_panel_layout.setContentsMargins(0, 0, 0, 0)
        crumb_panel_layout.setSpacing(0)
        crumb_panel_layout.addLayout(crumbs_layout, 0)
        crumb_panel_layout.addWidget(switch_space, 1)

        switch_space.clicked.connect(self.switch_space_mouse_up)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(path_input)
        layout.addWidget(crumbs_container)

        self.setMaximumHeight(path_input.height())

        self.crumbs_layout = crumbs_layout
        self.crumbs_panel = crumbs_panel
        self.switch_space = switch_space
        self.path_input = path_input
        self.crumbs_container = crumbs_container

        self._model = None
        self._proxy_model = proxy_model

        self._current_path = None

    def set_model(self, model):
        self._model = model
        self.path_input.set_model(model)
        self._proxy_model.setSourceModel(model)

    def _on_input_confirm(self):
        self.change_path(self.path_input.text())

    def _on_input_cancel(self):
        self._cancel_edit()

    def _clear_crumbs(self):
        while self.crumbs_layout.count():
            widget = self.crumbs_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

    def _insert_crumb(self, path):
        btn = BreadcrumbsButton(path, self._proxy_model, self.crumbs_panel)

        self.crumbs_layout.insertWidget(0, btn)

        btn.path_selected.connect(self._on_crumb_clicked)

    def _on_crumb_clicked(self, path):
        "Breadcrumb was clicked"
        self.change_path(path)

    def change_path(self, path):
        path = self._model.get_valid_path(path)
        if self._model and not self._model.is_valid_path(path):
            self._show_address_field()
        else:
            self.set_path(path)
            self.path_edited.emit(path)

    def set_path(self, path):
        if path is None or path == ".":
            path = self._current_path

        # exit edit mode
        self._cancel_edit()

        self._clear_crumbs()
        self._current_path = path
        self.path_input.setText(path)
        path_items = [
            item
            for item in path.split("/")
            if item
        ]
        while path_items:
            item = "/".join(path_items)
            self._insert_crumb(item)
            path_items.pop(-1)
        self._insert_crumb("")

        self.path_changed.emit(self._current_path)

    def _cancel_edit(self):
        "Set edit line text back to current path and switch to view mode"
        # revert path
        self.path_input.setText(self.path())
        # switch back to breadcrumbs view
        self._show_address_field(False)

    def path(self):
        "Get path displayed in this BreadcrumbsAddressBar"
        return self._current_path

    def switch_space_mouse_up(self):
        "EVENT: switch_space mouse clicked"
        self._show_address_field(True)

    def _show_address_field(self, show=True):
        "Show text address field"
        self.crumbs_container.setVisible(not show)
        self.path_input.setVisible(show)
        if show:
            self.path_input.setFocus()
            self.path_input.selectAll()

    def minimumSizeHint(self):
        result = super(BreadcrumbsAddressBar, self).minimumSizeHint()
        result.setHeight(self.path_input.minimumSizeHint().height())
        return result
