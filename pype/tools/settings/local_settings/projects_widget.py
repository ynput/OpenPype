import platform
import copy
from Qt import QtWidgets, QtCore, QtGui
from pype.tools.settings.settings import ProjectListWidget
from pype.settings.constants import (
    PROJECT_ANATOMY_KEY,
    DEFAULT_PROJECT_KEY
)
from .widgets import (
    SpacerWidget,
    ProxyLabelWidget
)
from .constants import (
    LABEL_REMOVE_DEFAULT,
    LABEL_ADD_DEFAULT,
    LABEL_REMOVE_PROJECT,
    LABEL_ADD_PROJECT,
    LABEL_DISCARD_CHANGES,
    LOCAL_ROOTS_KEY
)

NOT_SET = type("NOT_SET", (), {})()


def get_active_sites(project_settings):
    global_entity = project_settings["project_settings"]["global"]
    sites_entity = global_entity["sync_server"]["sites"]
    return tuple(sites_entity.keys())


class _ProjectListWidget(ProjectListWidget):
    def on_item_clicked(self, new_index):
        new_project_name = new_index.data(QtCore.Qt.DisplayRole)
        if new_project_name is None:
            return

        if self.current_project == new_project_name:
            return

        self.select_project(new_project_name)
        self.current_project = new_project_name
        self.project_changed.emit()


class RootInputWidget(QtWidgets.QWidget):
    def __init__(
        self,
        local_project_settings,
        local_project_settings_orig,
        platform_root_entity,
        root_name,
        project_name,
        site_name,
        parent
    ):
        super(RootInputWidget, self).__init__(parent)

        self.local_project_settings = local_project_settings
        self.local_project_settings_orig = local_project_settings_orig
        self.platform_root_entity = platform_root_entity
        self.root_name = root_name
        self.site_name = site_name
        self.project_name = project_name

        self.origin_value = self._get_site_value_for_project(
            self.project_name, self.local_project_settings_orig
        ) or ""

        is_default_project = bool(project_name == DEFAULT_PROJECT_KEY)

        default_input_value = self._get_site_value_for_project(
            DEFAULT_PROJECT_KEY
        )
        if is_default_project:
            input_value = default_input_value
            project_value = None
        else:
            input_value = self._get_site_value_for_project(self.project_name)
            project_value = input_value

        # Placeholder
        placeholder = None
        if not is_default_project:
            placeholder = default_input_value

        if not placeholder:
            placeholder = platform_root_entity.value

        key_label = ProxyLabelWidget(
            root_name,
            self._mouse_release_callback,
            self
        )
        value_input = QtWidgets.QLineEdit(self)
        value_input.setPlaceholderText("< {} >".format(placeholder))

        # Root value
        if input_value:
            value_input.setText(input_value)

        value_input.textChanged.connect(self._on_value_change)

        root_layout = QtWidgets.QHBoxLayout(self)
        root_layout.addWidget(key_label)
        root_layout.addWidget(value_input)

        self.value_input = value_input
        self.label_widget = key_label

        self.studio_value = platform_root_entity.value
        self.default_value = default_input_value
        self.project_value = project_value
        self.placeholder_value = placeholder

        self._update_style()

    def is_modified(self):
        return self.origin_value != self.value_input.text()

    def _mouse_release_callback(self, event):
        if event.button() != QtCore.Qt.RightButton:
            return
        self._show_actions()
        event.accept()

    def _get_style_state(self):
        if self.project_name is None:
            return ""

        if self.is_modified():
            return "modified"

        current_value = self.value_input.text()
        if self.project_name == DEFAULT_PROJECT_KEY:
            if current_value:
                return "studio"
        else:
            if current_value:
                return "overriden"

            studio_value = self._get_site_value_for_project(
                DEFAULT_PROJECT_KEY
            )
            if studio_value:
                return "studio"
        return ""

    def _update_style(self):
        state = self._get_style_state()

        self.value_input.setProperty("input-state", state)
        self.value_input.style().polish(self.value_input)

        self.label_widget.set_label_property("state", state)

    def _remove_from_local(self):
        self.value_input.setText("")
        self._update_style()

    def _add_to_local(self):
        self.value_input.setText(self.placeholder_value)
        self._update_style()

    def discard_changes(self):
        self.value_input.setText(self.origin_value)
        self._update_style()

    def _show_actions(self):
        if self.project_name is None:
            return

        menu = QtWidgets.QMenu(self)
        actions_mapping = {}

        if self.project_name == DEFAULT_PROJECT_KEY:
            remove_label = LABEL_REMOVE_DEFAULT
            add_label = LABEL_ADD_DEFAULT
        else:
            remove_label = LABEL_REMOVE_PROJECT
            add_label = LABEL_ADD_PROJECT

        if self.value_input.text():
            action = QtWidgets.QAction(remove_label)
            callback = self._remove_from_local
        else:
            action = QtWidgets.QAction(add_label)
            callback = self._add_to_local

        actions_mapping[action] = callback
        menu.addAction(action)

        if self.is_modified():
            discard_changes_action = QtWidgets.QAction(LABEL_DISCARD_CHANGES)
            actions_mapping[discard_changes_action] = self.discard_changes
            menu.addAction(discard_changes_action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def _get_site_value_for_project(self, project_name, data=None):
        if data is None:
            data = self.local_project_settings
        project_values = data.get(project_name)
        site_value = {}
        if project_values:
            root_value = project_values.get(LOCAL_ROOTS_KEY)
            if root_value:
                site_value = root_value.get(self.site_name) or {}
        return site_value.get(self.root_name)

    def _on_value_change(self):
        value = self.value_input.text()
        data = self.local_project_settings
        for key in (self.project_name, LOCAL_ROOTS_KEY, self.site_name):
            if key not in data:
                data[key] = {}
            data = data[key]
        data[self.root_name] = value
        self._update_style()


class RootsWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        super(RootsWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.site_widgets = []
        self.local_project_settings = None
        self.local_project_settings_orig = None
        self._project_name = None

        self.content_layout = QtWidgets.QVBoxLayout(self)

    def _clear_widgets(self):
        while self.content_layout.count():
            item = self.content_layout.itemAt(0)
            item.widget().hide()
            self.content_layout.removeItem(item)
        self.site_widgets = []

    def refresh(self):
        self._clear_widgets()

        if self._project_name is None:
            return

        roots_entity = (
            self.project_settings[PROJECT_ANATOMY_KEY][LOCAL_ROOTS_KEY]
        )
        # Site label
        for site_name in get_active_sites(self.project_settings):
            site_widget = QtWidgets.QWidget(self)
            site_layout = QtWidgets.QVBoxLayout(site_widget)

            site_label = QtWidgets.QLabel(site_name, site_widget)

            site_layout.addWidget(site_label)

            # Root inputs
            for root_name, path_entity in roots_entity.items():
                platform_entity = path_entity[platform.system().lower()]
                root_widget = RootInputWidget(
                    self.local_project_settings,
                    self.local_project_settings_orig,
                    platform_entity,
                    root_name,
                    self._project_name,
                    site_name,
                    site_widget
                )

                site_layout.addWidget(root_widget)

            self.site_widgets.append(site_widget)
            self.content_layout.addWidget(site_widget)

        # Add spacer so other widgets are squeezed to top
        self.content_layout.addWidget(SpacerWidget(self), 1)

    def update_local_settings(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.local_project_settings_orig = copy.deepcopy(
            dict(local_project_settings)
        )

    def change_project(self, project_name):
        self._project_name = project_name
        self.refresh()


class _SiteCombobox(QtWidgets.QWidget):
    input_label = None

    def __init__(self, project_settings, parent):
        super(_SiteCombobox, self).__init__(parent)
        self.project_settings = project_settings

        self.local_project_settings = None
        self.local_project_settings_orig = None
        self.project_name = None

        self.default_override_value = None
        self.project_override_value = None

        label_widget = ProxyLabelWidget(
            self.input_label,
            self._mouse_release_callback,
            self
        )
        combobox_input = QtWidgets.QComboBox(self)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(label_widget)
        main_layout.addWidget(combobox_input)

        combobox_input.currentIndexChanged.connect(self._on_index_change)
        self.label_widget = label_widget
        self.combobox_input = combobox_input

    def _set_current_text(self, text):
        index = None
        if text:
            idx = self.combobox_input.findText(text)
            if idx >= 0:
                index = idx

        if index is not None:
            self.combobox_input.setCurrentIndex(index)
            return True
        return False

    def is_modified(self, current_value=NOT_SET, orig_value=NOT_SET):
        if current_value is NOT_SET:
            current_value = self._get_local_settings_item(self.project_name)
        if orig_value is NOT_SET:
            orig_value = self._get_local_settings_item(
                self.project_name, self.local_project_settings_orig
            )
        if current_value and orig_value:
            modified = current_value != orig_value
        elif not current_value and not orig_value:
            modified = False
        else:
            modified = True
        return modified

    def _get_style_state(self):
        if self.project_name is None:
            return ""

        current_value = self._get_local_settings_item(self.project_name)
        orig_value = self._get_local_settings_item(
            self.project_name, self.local_project_settings_orig
        )

        if self.is_modified(current_value, orig_value):
            return "modified"

        if self.project_name == DEFAULT_PROJECT_KEY:
            if current_value:
                return "studio"
        else:
            if current_value:
                return "overriden"

            studio_value = self._get_local_settings_item(DEFAULT_PROJECT_KEY)
            if studio_value:
                return "studio"
        return ""

    def _update_style(self):
        state = self._get_style_state()

        self.combobox_input.setProperty("input-state", state)
        self.combobox_input.style().polish(self.combobox_input)

        self.label_widget.set_label_property("state", state)

    def _mouse_release_callback(self, event):
        if event.button() != QtCore.Qt.RightButton:
            return
        self._show_actions()

    def _remove_from_local(self):
        settings_value = self._get_value_from_project_settings()
        combobox_value = None
        if self.project_name == DEFAULT_PROJECT_KEY:
            combobox_value = self._get_local_settings_item(DEFAULT_PROJECT_KEY)
            if combobox_value:
                idx = self.combobox_input.findText(combobox_value)
                if idx < 0:
                    combobox_value = None

        if not combobox_value:
            combobox_value = settings_value

        if combobox_value:
            _project_name = self.project_name
            self.project_name = None
            self._set_current_text(combobox_value)
            self.project_name = _project_name

        self._set_local_settings_value("")
        self._update_style()

    def _add_to_local(self):
        self._set_local_settings_value(self.current_text())
        self._update_style()

    def discard_changes(self):
        orig_value = self._get_local_settings_item(
            self.project_name, self.local_project_settings_orig
        )
        self._set_current_text(orig_value)

    def _show_actions(self):
        if self.project_name is None:
            return

        menu = QtWidgets.QMenu(self)
        actions_mapping = {}

        if self.project_name == DEFAULT_PROJECT_KEY:
            remove_label = LABEL_REMOVE_DEFAULT
            add_label = LABEL_ADD_DEFAULT
        else:
            remove_label = LABEL_REMOVE_PROJECT
            add_label = LABEL_ADD_PROJECT

        has_value = self._get_local_settings_item(self.project_name)
        if has_value:
            action = QtWidgets.QAction(remove_label)
            callback = self._remove_from_local
        else:
            action = QtWidgets.QAction(add_label)
            callback = self._add_to_local

        actions_mapping[action] = callback
        menu.addAction(action)

        if self.is_modified():
            discard_changes_action = QtWidgets.QAction(LABEL_DISCARD_CHANGES)
            actions_mapping[discard_changes_action] = self.discard_changes
            menu.addAction(discard_changes_action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def update_local_settings(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.local_project_settings_orig = copy.deepcopy(
            dict(local_project_settings)
        )

    def current_text(self):
        return self.combobox_input.currentText()

    def change_project(self, project_name):
        self.default_override_value = None
        self.project_override_value = None

        self.project_name = None
        self.combobox_input.clear()
        if project_name is None:
            self._update_style()
            return

        is_default_project = bool(project_name == DEFAULT_PROJECT_KEY)
        site_items = self._get_project_sites()
        self.combobox_input.addItems(site_items)

        default_item = self._get_local_settings_item(DEFAULT_PROJECT_KEY)
        if is_default_project:
            project_item = None
        else:
            project_item = self._get_local_settings_item(project_name)

        index = None
        if project_item:
            idx = self.combobox_input.findText(project_item)
            if idx >= 0:
                self.project_override_value = project_item
                index = idx

        if default_item:
            idx = self.combobox_input.findText(default_item)
            if idx >= 0:
                self.default_override_value = default_item
                if index is None:
                    index = idx

        if index is None:
            settings_value = self._get_value_from_project_settings()
            idx = self.combobox_input.findText(settings_value)
            if idx >= 0:
                index = idx

        if index is not None:
            self.combobox_input.setCurrentIndex(index)

        self.project_name = project_name
        self._update_style()

    def _on_index_change(self):
        if self.project_name is None:
            return

        self._set_local_settings_value(self.current_text())
        self._update_style()

    def _set_local_settings_value(self, value):
        raise NotImplementedError(
            "{} `_set_local_settings_value` not implemented".format(
                self.__class__.__name__
            )
        )

    def _get_project_sites(self):
        raise NotImplementedError(
            "{} `_get_project_sites` not implemented".format(
                self.__class__.__name__
            )
        )

    def _get_local_settings_item(self, project_name=None, data=None):
        raise NotImplementedError(
            "{}`_get_local_settings_item` not implemented".format(
                self.__class__.__name__
            )
        )

    def _get_value_from_project_settings(self):
        raise NotImplementedError(
            "{}`_get_value_from_project_settings` not implemented".format(
                self.__class__.__name__
            )
        )


class AciveSiteCombo(_SiteCombobox):
    input_label = "Active site"

    def _get_project_sites(self):
        return get_active_sites(self.project_settings)

    def _get_local_settings_item(self, project_name=None, data=None):
        if project_name is None:
            project_name = self.project_name

        if data is None:
            data = self.local_project_settings
        project_values = data.get(project_name)
        value = None
        if project_values:
            value = project_values.get("active_site")
        return value

    def _get_value_from_project_settings(self):
        global_entity = self.project_settings["project_settings"]["global"]
        return global_entity["sync_server"]["config"]["active_site"].value

    def _set_local_settings_value(self, value):
        if self.project_name not in self.local_project_settings:
            self.local_project_settings[self.project_name] = {}
        self.local_project_settings[self.project_name]["active_site"] = value


class RemoteSiteCombo(_SiteCombobox):
    input_label = "Remote site"

    def _get_project_sites(self):
        global_entity = self.project_settings["project_settings"]["global"]
        sites_entity = global_entity["sync_server"]["sites"]
        return tuple(sites_entity.keys())

    def _get_local_settings_item(self, project_name=None, data=None):
        if project_name is None:
            project_name = self.project_name
        if data is None:
            data = self.local_project_settings
        project_values = data.get(project_name)
        value = None
        if project_values:
            value = project_values.get("remote_site")
        return value

    def _get_value_from_project_settings(self):
        global_entity = self.project_settings["project_settings"]["global"]
        return global_entity["sync_server"]["config"]["remote_site"].value

    def _set_local_settings_value(self, value):
        if self.project_name not in self.local_project_settings:
            self.local_project_settings[self.project_name] = {}
        self.local_project_settings[self.project_name]["remote_site"] = value


class RootSiteWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        self._parent_widget = parent
        super(RootSiteWidget, self).__init__(parent)

        self.project_settings = project_settings
        self._project_name = None

        sites_widget = QtWidgets.QWidget(self)

        active_site_widget = AciveSiteCombo(project_settings, sites_widget)
        remote_site_widget = RemoteSiteCombo(project_settings, sites_widget)

        sites_layout = QtWidgets.QHBoxLayout(sites_widget)
        sites_layout.setContentsMargins(0, 0, 0, 0)
        sites_layout.addWidget(active_site_widget)
        sites_layout.addWidget(remote_site_widget)
        sites_layout.addWidget(SpacerWidget(self), 1)

        roots_widget = RootsWidget(project_settings, self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(sites_widget)
        main_layout.addWidget(roots_widget)
        main_layout.addWidget(SpacerWidget(self), 1)

        self.active_site_widget = active_site_widget
        self.remote_site_widget = remote_site_widget
        self.roots_widget = roots_widget

    def _active_site_values(self):
        global_entity = self.project_settings["project_settings"]["global"]
        sites_entity = global_entity["sync_server"]["sites"]
        return tuple(sites_entity.keys())

    def _remote_site_values(self):
        global_entity = self.project_settings["project_settings"]["global"]
        sites_entity = global_entity["sync_server"]["sites"]
        return tuple(sites_entity.keys())

    def update_local_settings(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.active_site_widget.update_local_settings(local_project_settings)
        self.remote_site_widget.update_local_settings(local_project_settings)
        self.roots_widget.update_local_settings(local_project_settings)
        project_name = self._project_name
        if project_name is None:
            project_name = DEFAULT_PROJECT_KEY

        self.change_project(project_name)

    def change_project(self, project_name):
        self._project_name = project_name
        # Set roots project to None so all changes below are ignored
        self.roots_widget.change_project(None)

        # Aply changes in site comboboxes
        self.active_site_widget.change_project(project_name)
        self.remote_site_widget.change_project(project_name)

        # Change project name in roots widget
        self.roots_widget.change_project(project_name)


class ProjectValue(dict):
    pass


class ProjectSettingsWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        super(ProjectSettingsWidget, self).__init__(parent)

        self.local_project_settings = {}

        projects_widget = _ProjectListWidget(self)
        roos_site_widget = RootSiteWidget(project_settings, self)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(projects_widget, 0)
        main_layout.addWidget(roos_site_widget, 1)

        projects_widget.project_changed.connect(self._on_project_change)

        self.project_settings = project_settings

        self.projects_widget = projects_widget
        self.roos_site_widget = roos_site_widget

    def project_name(self):
        return self.projects_widget.project_name()

    def _on_project_change(self):
        project_name = self.project_name()
        self.project_settings.change_project(project_name)
        if project_name is None:
            project_name = DEFAULT_PROJECT_KEY
        self.roos_site_widget.change_project(project_name)

    def update_local_settings(self, value):
        if not value:
            value = {}
        self.local_project_settings = ProjectValue(value)

        self.roos_site_widget.update_local_settings(
            self.local_project_settings
        )

        self.projects_widget.refresh()

    def _clear_value(self, value):
        if not value:
            return None

        if not isinstance(value, dict):
            return value

        output = {}
        for _key, _value in value.items():
            _modified_value = self._clear_value(_value)
            if _modified_value:
                output[_key] = _modified_value
        return output

    def settings_value(self):
        output = self._clear_value(self.local_project_settings)
        if not output:
            return None
        return output
