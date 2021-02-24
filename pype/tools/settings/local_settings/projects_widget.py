import platform
from Qt import QtWidgets, QtCore
from pype.tools.settings.settings import ProjectListWidget
from pype.settings.constants import PROJECT_ANATOMY_KEY
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


class RootsWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, project_settings, parent):
        super(RootsWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.local_project_settings = {}
        self.widgts_by_root_name = {}
        self._project_name = None
        self._site_name = None

        self.content_layout = QtWidgets.QVBoxLayout(self)

    def _on_root_value_change(self, root_key):
        print("root value or key {} changed".format(root_key))

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

        default_root_values = self.local_default_project_values() or {}

        roots_entity = (
            self.project_settings[PROJECT_ANATOMY_KEY][LOCAL_ROOTS_KEY]
        )
        is_in_default = self.project_settings.project_name is None
        for root_name, path_entity in roots_entity.items():
            platform_entity = path_entity[platform.system().lower()]
            root_widget = QtWidgets.QWidget(self)

            key_label = QtWidgets.QLabel(root_name, root_widget)

            root_input_widget = QtWidgets.QWidget(root_widget)
            root_input_layout = QtWidgets.QVBoxLayout(root_input_widget)

            value_input = QtWidgets.QLineEdit(root_input_widget)
            placeholder = None
            if not is_in_default:
                placeholder = default_root_values.get(root_name)
                if placeholder:
                    placeholder = "< {} >".format(placeholder)

            if not placeholder:
                placeholder = platform_entity.value
            value_input.setPlaceholderText(placeholder)

            def _on_root_change():
                self._on_root_value_change(root_name)

            value_input.textChanged.connect(_on_root_change)

            root_input_layout.addWidget(value_input)

            root_layout = QtWidgets.QHBoxLayout(root_widget)
            root_layout.addWidget(key_label)
            root_layout.addWidget(root_input_widget)

            self.content_layout.addWidget(root_widget)
            self.widgts_by_root_name[root_name] = value_input

        self.content_layout.addWidget(SpacerWidget(self), 1)

    def local_default_project_values(self):
        default_project = self.local_project_settings.get(None)
        if default_project:
            return default_project.get(LOCAL_ROOTS_KEY)
        return None

    def set_value(self, local_project_settings):
        self.local_project_settings = local_project_settings

    def change_site(self, site_name):
        self._site_name = site_name
        self.refresh()

    def change_project(self, project_name):
        self._project_name = project_name
        self.refresh()


class RootSiteWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, project_settings, parent):
        self._parent_widget = parent
        super(RootSiteWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.widgts_by_root_name = {}
        self._project_name = None

        sites_widget = QtWidgets.QWidget(self)
        sites_layout = QtWidgets.QHBoxLayout(sites_widget)
        active_site_combo = QtWidgets.QComboBox(sites_widget)
        remote_site_combo = QtWidgets.QComboBox(sites_widget)
        sites_layout.addWidget(QtWidgets.QLabel("Active Site", sites_widget))
        sites_layout.addWidget(active_site_combo)
        sites_layout.addWidget(QtWidgets.QLabel("Remote Site", sites_widget))
        sites_layout.addWidget(remote_site_combo)

        roots_widget = RootsWidget(project_settings, self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(sites_widget)
        main_layout.addWidget(roots_widget)
        main_layout.addWidget(SpacerWidget(self), 1)

        self.active_site_combo = active_site_combo
        self.remote_site_combo = remote_site_combo
        self.roots_widget = roots_widget

    def _fill_active_site_combo(self):
        if self._project_name is None:
            return

    def _fill_remote_site_combo(self):
        if self._project_name is None:
            return

    def _change_combobox_values(self):
        # Set sites from local settings in comboboxes
        pass

    def set_value(self, local_project_settings):
        self.local_project_settings = local_project_settings

    def _change_active_site(self, site_name):
        self.roots_widget.change_site(site_name)

    def change_project(self, project_name):
        self._project_name = project_name
        # Set roots project to None so all changes below are ignored
        self.roots_widget.change_project(None)

        self._fill_active_site_combo()
        self._fill_remote_site_combo()
        self._change_combobox_values()

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
