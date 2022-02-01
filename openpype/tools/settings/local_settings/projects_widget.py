import platform
import copy
from Qt import QtWidgets, QtCore, QtGui
from openpype.tools.settings.settings import ProjectListWidget
from openpype.tools.utils import PlaceholderLineEdit
from openpype.settings.constants import (
    PROJECT_ANATOMY_KEY,
    DEFAULT_PROJECT_KEY
)
from .widgets import ProxyLabelWidget
from .constants import (
    LABEL_REMOVE_DEFAULT,
    LABEL_ADD_DEFAULT,
    LABEL_REMOVE_PROJECT,
    LABEL_ADD_PROJECT,
    LABEL_DISCARD_CHANGES,
    LOCAL_ROOTS_KEY
)

NOT_SET = type("NOT_SET", (), {})()


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


class DynamicInputItem(QtCore.QObject):
    value_changed = QtCore.Signal(str, str)

    def __init__(
        self,
        input_def,
        site_name,
        value_item,
        label_widget,
        parent
    ):
        super(DynamicInputItem, self).__init__()
        input_widget = PlaceholderLineEdit(parent)

        settings_value = input_def.get("value")
        placeholder = input_def.get("placeholder")

        value_placeholder_template = "< {} >"
        if (
            not placeholder
            and value_item.project_name != DEFAULT_PROJECT_KEY
            and value_item.default_value
        ):
            placeholder = value_placeholder_template.format(
                value_item.default_value
            )

        if not placeholder and settings_value:
            placeholder = value_placeholder_template.format(settings_value)

        if placeholder:
            input_widget.setPlaceholderText(placeholder)

        if value_item.value:
            input_widget.setText(value_item.value)

        input_widget.textChanged.connect(self._on_str_change)

        self.value_item = value_item
        self.site_name = site_name
        self.key = input_def["key"]

        self.settings_value = settings_value

        self.current_value = input_widget.text()

        self.input_widget = input_widget
        self.label_widget = label_widget

        self.parent_widget = parent

        label_widget.set_mouse_release_callback(self._mouse_release_callback)
        self._update_style()

    @property
    def origin_value(self):
        return self.value_item.orig_value

    @property
    def project_name(self):
        return self.value_item.project_name

    def _on_str_change(self, value):
        if self.current_value == value:
            return

        self.current_value = value
        self.value_changed.emit(self.site_name, self.key)
        self._update_style()

    def is_modified(self):
        return self.origin_value != self.input_widget.text()

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

        current_value = self.input_widget.text()
        if self.project_name == DEFAULT_PROJECT_KEY:
            if current_value:
                return "studio"
        else:
            if current_value:
                return "overridden"

            if self.value_item.default_value:
                return "studio"
        return ""

    def _update_style(self):
        state = self._get_style_state()

        self.input_widget.setProperty("input-state", state)
        self.input_widget.style().polish(self.input_widget)

        self.label_widget.set_label_property("state", state)

    def _remove_from_local(self):
        self.input_widget.setText("")

    def _add_to_local(self):
        value = self.value_item.default_value
        if self.project_name == DEFAULT_PROJECT_KEY or not value:
            value = self.settings_value

        self.input_widget.setText(value)

    def discard_changes(self):
        self.input_widget.setText(self.origin_value)

    def _show_actions(self):
        if self.project_name is None:
            return

        menu = QtWidgets.QMenu(self.parent_widget)
        actions_mapping = {}

        if self.project_name == DEFAULT_PROJECT_KEY:
            remove_label = LABEL_REMOVE_DEFAULT
            add_label = LABEL_ADD_DEFAULT
        else:
            remove_label = LABEL_REMOVE_PROJECT
            add_label = LABEL_ADD_PROJECT

        if self.input_widget.text():
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


class SiteValueItem:
    def __init__(
        self,
        project_name,
        value,
        default_value,
        orig_value,
        orig_default_value
    ):
        self.project_name = project_name
        self.value = value or ""
        self.default_value = default_value or ""
        self.orig_value = orig_value or ""
        self.orig_default_value = orig_default_value or ""

    def __repr__(self):
        return "\n".join((
            "Project: {}".format(self.project_name),
            "Value: {}".format(self.value),
            "Default value: {}".format(self.default_value),
            "Orig value: {}".format(self.orig_value),
            "Orig default value: {}".format(self.orig_default_value),
        ))


class SitesWidget(QtWidgets.QWidget):
    def __init__(self, modules_manager, project_settings, parent):
        super(SitesWidget, self).__init__(parent)

        self.modules_manager = modules_manager
        self.project_settings = project_settings
        self.input_objects = {}
        self.local_project_settings = None
        self.local_project_settings_orig = None
        self._project_name = None

        comboboxes_widget = QtWidgets.QWidget(self)

        active_site_widget = AciveSiteCombo(
            modules_manager, project_settings, comboboxes_widget
        )
        remote_site_widget = RemoteSiteCombo(
            modules_manager, project_settings, comboboxes_widget
        )

        comboboxes_layout = QtWidgets.QHBoxLayout(comboboxes_widget)
        comboboxes_layout.setContentsMargins(0, 0, 0, 0)
        comboboxes_layout.addWidget(active_site_widget, 0)
        comboboxes_layout.addWidget(remote_site_widget, 0)
        comboboxes_layout.addStretch(1)

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(comboboxes_widget, 0)
        main_layout.addWidget(content_widget, 1)

        self.active_site_widget = active_site_widget
        self.remote_site_widget = remote_site_widget

        self.content_widget = content_widget
        self.content_layout = content_layout

    def _clear_widgets(self):
        while self.content_layout.count():
            item = self.content_layout.itemAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(False)
            self.content_layout.removeItem(item)
        self.input_objects = {}

    def _get_sites_inputs(self):
        sync_server_module = (
            self.modules_manager.modules_by_name["sync_server"]
        )

        # This is temporary modification
        # - whole logic here should be in sync module's providers
        site_names = sync_server_module.get_active_sites_from_settings(
            self.project_settings["project_settings"].value
        )

        roots_entity = (
            self.project_settings[PROJECT_ANATOMY_KEY][LOCAL_ROOTS_KEY]
        )

        output = []
        for site_name in site_names:
            site_inputs = []
            for root_name, path_entity in roots_entity.items():
                platform_entity = path_entity[platform.system().lower()]
                site_inputs.append({
                    "label": root_name,
                    "key": root_name,
                    "value": platform_entity.value
                })

            output.append(
                (site_name, site_inputs)
            )
        return output

    @staticmethod
    def _extract_value_from_data(data, project_name, site_name, key):
        _s_value = data
        for _key in (project_name, site_name, key):
            if _key not in _s_value:
                return None
            _s_value = _s_value[_key]
        return _s_value

    def _prepare_value_item(self, site_name, key):
        value = self._extract_value_from_data(
            self.local_project_settings,
            self._project_name,
            site_name,
            key
        )
        orig_value = self._extract_value_from_data(
            self.local_project_settings_orig,
            self._project_name,
            site_name,
            key
        )
        orig_default_value = None
        default_value = None
        if self._project_name != DEFAULT_PROJECT_KEY:
            default_value = self._extract_value_from_data(
                self.local_project_settings,
                DEFAULT_PROJECT_KEY,
                site_name,
                key
            )
            orig_default_value = self._extract_value_from_data(
                self.local_project_settings_orig,
                DEFAULT_PROJECT_KEY,
                site_name,
                key
            )

        return SiteValueItem(
            self._project_name,
            value,
            default_value,
            orig_value,
            orig_default_value
        )

    def refresh(self):
        self._clear_widgets()

        if self._project_name is None:
            return

        # Site label
        for site_name, site_inputs in self._get_sites_inputs():
            site_widget = QtWidgets.QWidget(self.content_widget)
            site_layout = QtWidgets.QVBoxLayout(site_widget)

            site_label = QtWidgets.QLabel(site_name, site_widget)

            inputs_widget = QtWidgets.QWidget(site_widget)
            inputs_layout = QtWidgets.QGridLayout(inputs_widget)

            site_input_objects = {}
            for idx, input_def in enumerate(site_inputs):
                key = input_def["key"]
                label = input_def.get("label") or key
                label_widget = ProxyLabelWidget(label, None, inputs_widget)

                value_item = self._prepare_value_item(site_name, key)

                input_obj = DynamicInputItem(
                    input_def,
                    site_name,
                    value_item,
                    label_widget,
                    inputs_widget
                )
                input_obj.value_changed.connect(self._on_input_value_change)
                site_input_objects[key] = input_obj
                inputs_layout.addWidget(label_widget, idx, 0)
                inputs_layout.addWidget(input_obj.input_widget, idx, 1)

            site_layout.addWidget(site_label)
            site_layout.addWidget(inputs_widget)

            self.content_layout.addWidget(site_widget)
            self.input_objects[site_name] = site_input_objects

        # Add spacer so other widgets are squeezed to top
        self.content_layout.addStretch(1)

    def _on_input_value_change(self, site_name, key):
        if (
            site_name not in self.input_objects
            or key not in self.input_objects[site_name]
        ):
            return

        input_obj = self.input_objects[site_name][key]
        value = input_obj.current_value

        if not value:
            if self._project_name not in self.local_project_settings:
                return

            project_values = self.local_project_settings[self._project_name]
            if site_name not in project_values:
                return

            project_values[site_name][key] = None

        else:
            if self._project_name not in self.local_project_settings:
                self.local_project_settings[self._project_name] = {}

            project_values = self.local_project_settings[self._project_name]
            if site_name not in project_values:
                project_values[site_name] = {}

            project_values[site_name][key] = value

    def update_local_settings(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.local_project_settings_orig = copy.deepcopy(
            dict(local_project_settings)
        )
        self.active_site_widget.update_local_settings(local_project_settings)
        self.remote_site_widget.update_local_settings(local_project_settings)

    def change_project(self, project_name):
        self._project_name = None
        self.refresh()

        self.active_site_widget.change_project(project_name)
        self.remote_site_widget.change_project(project_name)

        self._project_name = project_name
        self.refresh()


class _SiteCombobox(QtWidgets.QWidget):
    input_label = None

    def __init__(self, modules_manager, project_settings, parent):
        super(_SiteCombobox, self).__init__(parent)
        self.project_settings = project_settings

        self.modules_manager = modules_manager

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
        combobox_delegate = QtWidgets.QStyledItemDelegate()
        combobox_input.setItemDelegate(combobox_delegate)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(label_widget)
        main_layout.addWidget(combobox_input)

        combobox_input.currentIndexChanged.connect(self._on_index_change)
        self.label_widget = label_widget
        self.combobox_input = combobox_input
        self._combobox_delegate = combobox_delegate

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
                return "overridden"

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
        sync_server_module = (
            self.modules_manager.modules_by_name["sync_server"]
        )
        if self.project_name is None:
            return sync_server_module.get_active_sites_from_settings(
                self.project_settings["project_settings"].value
            )
        return sync_server_module.get_active_sites(self.project_name)

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

    def change_project(self, *args, **kwargs):
        super(RemoteSiteCombo, self).change_project(*args, **kwargs)

        self.setVisible(self.combobox_input.count() > 0)
        if not self.isVisible():
            self._set_local_settings_value("")

    def _get_project_sites(self):
        sync_server_module = (
            self.modules_manager.modules_by_name["sync_server"]
        )
        if self.project_name is None:
            return sync_server_module.get_remote_sites_from_settings(
                self.project_settings["project_settings"].value
            )
        return sync_server_module.get_remote_sites(self.project_name)

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
    def __init__(self, modules_manager, project_settings, parent):
        self._parent_widget = parent
        super(RootSiteWidget, self).__init__(parent)

        self.modules_manager = modules_manager
        self.project_settings = project_settings
        self._project_name = None

        sites_widget = SitesWidget(modules_manager, project_settings, self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(sites_widget)
        main_layout.addStretch(1)

        self.sites_widget = sites_widget

    def update_local_settings(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.sites_widget.update_local_settings(local_project_settings)
        project_name = self._project_name
        if project_name is None:
            project_name = DEFAULT_PROJECT_KEY

        self.change_project(project_name)

    def change_project(self, project_name):
        self._project_name = project_name

        # Change project name in roots widget
        self.sites_widget.change_project(project_name)


class ProjectValue(dict):
    pass


class ProjectSettingsWidget(QtWidgets.QWidget):
    def __init__(self, modules_manager, project_settings, parent):
        super(ProjectSettingsWidget, self).__init__(parent)

        self.local_project_settings = {}

        self.modules_manager = modules_manager

        projects_widget = _ProjectListWidget(self, only_active=True)
        roos_site_widget = RootSiteWidget(
            modules_manager, project_settings, self
        )

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
