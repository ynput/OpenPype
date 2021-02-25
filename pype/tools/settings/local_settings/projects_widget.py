import platform
import copy
from Qt import QtWidgets, QtCore
from pype.tools.settings.settings import ProjectListWidget
from pype.settings.constants import (
    PROJECT_ANATOMY_KEY,
    DEFAULT_PROJECT_KEY
)
from .widgets import SpacerWidget

LOCAL_ROOTS_KEY = "roots"


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
        )

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

        key_label = QtWidgets.QLabel(root_name, self)
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

        self.is_default_project = is_default_project
        self.studio_value = platform_root_entity.value
        self.default_value = default_input_value
        self.project_value = project_value

    @property
    def is_modified(self):
        return self.origin_value != self.value_input.text()

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


class RootsWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        super(RootsWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.widgts_by_root_name = {}
        self.local_project_settings = None
        self.local_project_settings_orig = None
        self._project_name = None
        self._site_name = None

        self.content_layout = QtWidgets.QVBoxLayout(self)

    def _clear_widgets(self):
        while self.content_layout.count():
            item = self.content_layout.itemAt(0)
            item.widget().hide()
            self.content_layout.removeItem(item)
        self.widgts_by_root_name.clear()

    def refresh(self):
        self._clear_widgets()

        if self._project_name is None or self._site_name is None:
            return

        # Site label
        self.content_layout.addWidget(QtWidgets.QLabel(self._site_name, self))

        # Root inputs
        roots_entity = (
            self.project_settings[PROJECT_ANATOMY_KEY][LOCAL_ROOTS_KEY]
        )
        for root_name, path_entity in roots_entity.items():
            platform_entity = path_entity[platform.system().lower()]
            root_widget = RootInputWidget(
                self.local_project_settings,
                self.local_project_settings_orig,
                platform_entity,
                root_name,
                self._project_name,
                self._site_name,
                self
            )

            self.content_layout.addWidget(root_widget)
            self.widgts_by_root_name[root_name] = root_widget

        # Add spacer so other widgets are squeezed to top
        self.content_layout.addWidget(SpacerWidget(self), 1)

    def set_value(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.local_project_settings_orig = copy.deepcopy(
            dict(local_project_settings)
        )

    def change_site(self, site_name):
        self._site_name = site_name
        self.refresh()

    def change_project(self, project_name):
        self._project_name = project_name
        self.refresh()


class _SiteCombobox(QtWidgets.QWidget):
    site_changed = QtCore.Signal(str)

    def __init__(self, project_settings, parent):
        super(_SiteCombobox, self).__init__(parent)
        self.project_settings = project_settings

        self.local_project_settings = None
        self.local_project_settings_orig = None
        self.project_name = None
        self.is_default_project = None

        self.default_override_value = None
        self.project_override_value = None

        label_widget = QtWidgets.QLabel(self)
        combobox_input = QtWidgets.QComboBox(self)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(label_widget)
        main_layout.addWidget(combobox_input)

        combobox_input.currentIndexChanged.connect(self._on_index_change)
        self.label_widget = label_widget
        self.combobox_input = combobox_input

        self._ui_tweaks()

    def set_value(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.local_project_settings_orig = copy.deepcopy(
            dict(local_project_settings)
        )

    def change_project(self, project_name):
        self.default_override_value = None
        self.project_override_value = None

        self.project_name = None
        self.combobox_input.clear()
        if project_name is None:
            return

        self.is_default_project = bool(project_name == DEFAULT_PROJECT_KEY)
        site_items = self._get_project_sites()
        self.combobox_input.addItems(site_items)

        default_item = self._get_local_settings_item(DEFAULT_PROJECT_KEY)
        if self.is_default_project:
            project_item = None
        else:
            project_item = self._get_local_settings_item(project_name)

        index = None
        if project_item:
            idx = self.combobox_input.findText(project_item)
            if idx >= 0:
                self.project_override_value = project_item
                index = self.combobox_input.model().index(idx, 0)

        if default_item:
            idx = self.combobox_input.findText(default_item)
            if idx >= 0:
                self.default_override_value = default_item
                if not index:
                    index = self.combobox_input.model().index(idx, 0)
        if index:
            self.combobox_input.setCurrentIndex(index)

        self.project_name = project_name
        self.site_changed.emit(self.combobox_input.currentText())

    def _on_index_change(self):
        if self.project_name is None:
            return
        self.site_changed.emit(self.combobox_input.currentText())
        print("here")

    def _ui_tweaks(self):
        raise NotImplementedError("_ui_tweaks not implemented {}".format(
            self.__class__.__name__
        ))

    def _get_project_sites(self):
        raise NotImplementedError("_ui_tweaks not implemented {}".format(
            self.__class__.__name__
        ))

    def _get_local_settings_item(self, project_name):
        raise NotImplementedError("_ui_tweaks not implemented {}".format(
            self.__class__.__name__
        ))


class AciveSiteCombo(_SiteCombobox):
    def _ui_tweaks(self):
        self.label_widget.setText("Active site")

    def _get_project_sites(self):
        global_entity = self.project_settings["project_settings"]["global"]
        sites_entity = global_entity["sync_server"]["sites"]
        return tuple(sites_entity.keys())

    def _get_local_settings_item(self, project_name):
        project_values = self.local_project_settings.get(project_name)
        value = None
        if project_values:
            value = project_values.get("active_site")
        return value


class RemoteSiteCombo(_SiteCombobox):
    def _ui_tweaks(self):
        self.label_widget.setText("Remote site")

    def _get_project_sites(self):
        global_entity = self.project_settings["project_settings"]["global"]
        sites_entity = global_entity["sync_server"]["sites"]
        return tuple(sites_entity.keys())

    def _get_local_settings_item(self, project_name):
        project_values = self.local_project_settings.get(project_name)
        value = None
        if project_values:
            value = project_values.get("remote_site")
        return value


class RootSiteWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        self._parent_widget = parent
        super(RootSiteWidget, self).__init__(parent)

        self.project_settings = project_settings
        self._project_name = None

        sites_widget = QtWidgets.QWidget(self)
        sites_layout = QtWidgets.QHBoxLayout(sites_widget)

        active_site_widget = AciveSiteCombo(project_settings, sites_widget)
        remote_site_widget = RemoteSiteCombo(project_settings, sites_widget)
        sites_layout.addWidget(active_site_widget)
        sites_layout.addWidget(remote_site_widget)

        roots_widget = RootsWidget(project_settings, self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(sites_widget)
        main_layout.addWidget(roots_widget)
        main_layout.addWidget(SpacerWidget(self), 1)

        active_site_widget.site_changed.connect(self._on_acite_site_change)
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

    def set_value(self, local_project_settings):
        self.local_project_settings = local_project_settings
        self.active_site_widget.set_value(local_project_settings)
        self.remote_site_widget.set_value(local_project_settings)
        self.roots_widget.set_value(local_project_settings)

    def _on_acite_site_change(self, site_name):
        self._change_active_site(site_name)

    def _change_active_site(self, site_name):
        self.roots_widget.change_site(site_name)

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

    def set_value(self, value):
        if not value:
            value = {}
        self.local_project_settings = ProjectValue(value)

        self.roos_site_widget.set_value(self.local_project_settings)

        self.projects_widget.refresh()

    def settings_value(self):
        output = {}
        for project_name, value in self.local_project_settings.items():
            if value:
                output[project_name] = value
        if not output:
            return None
        return output
