from Qt import QtWidgets, QtCore
from pype.tools.settings.settings import ProjectListWidget
from .widgets import SpacerWidget
from pype.settings.constants import PROJECT_ANATOMY_KEY


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
        self._parent_widget = parent
        super(RootsWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.widgts_by_root_name = {}

        main_layout = QtWidgets.QVBoxLayout(self)

        self.content_layout = main_layout

    def _on_root_value_change(self):
        self.value_changed.emit()

    def refresh(self):
        while self.content_layout.count():
            item = self.content_layout.itemAt(0)
            item.widget().hide()
            self.content_layout.removeItem(item)

        self.widgts_by_root_name.clear()

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
            value_input.textChanged.connect(self._on_root_value_change)

            root_input_layout.addWidget(value_input)

            root_layout = QtWidgets.QHBoxLayout(root_widget)
            root_layout.addWidget(key_label)
            root_layout.addWidget(root_input_widget)

            self.content_layout.addWidget(root_widget)
            self.widgts_by_root_name[root_name] = value_input

        self.content_layout.addWidget(SpacerWidget(self), 1)

    def local_default_project_values(self):
        default_project = self._parent_widget.per_project_settings.get(None)
        if default_project:
            return default_project.get(LOCAL_ROOTS_KEY)
        return None

    def set_value(self, value):
        if not value:
            value = {}

        for root_name, widget in self.widgts_by_root_name.items():
            root_value = value.get(root_name) or ""
            widget.setText(root_value)

    def settings_value(self):
        output = {}
        for root_name, widget in self.widgts_by_root_name.items():
            value = widget.text()
            if value:
                output[root_name] = value
        if not output:
            return None
        return output


class ProjectSpecificWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, project_settings, parent):
        self._parent_widget = parent
        super(ProjectSpecificWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.widgts_by_root_name = {}

        sites_widget = QtWidgets.QWidget(self)
        sites_layout = QtWidgets.QHBoxLayout(sites_widget)
        active_site_combo = QtWidgets.QComboBox(sites_widget)
        remote_site_combo = QtWidgets.QComboBox(sites_widget)
        sites_layout.addWidget(QtWidgets.QLabel("Active Site", sites_widget))
        sites_layout.addWidget(active_site_combo)
        sites_layout.addWidget(QtWidgets.QLabel("Remote Site", sites_widget))
        sites_layout.addWidget(remote_site_combo)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(sites_widget)
        main_layout.addWidget(SpacerWidget(self), 1)

    def set_value(self, value):
        pass
        # if not value:
        #     value = {}
        #
        # for root_name, widget in self.widgts_by_root_name.items():
        #     root_value = value.get(root_name) or ""
        #     widget.setText(root_value)

    def settings_value(self):
        return {}
        # output = {}
        # for root_name, widget in self.widgts_by_root_name.items():
        #     value = widget.text()
        #     if value:
        #         output[root_name] = value
        # if not output:
        #     return None
        # return output

    def change_project(self, project_name):
        pass


class ProjectSettingsWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        super(ProjectSettingsWidget, self).__init__(parent)

        self.per_project_settings = {}

        projects_widget = _ProjectListWidget(self)
        project_specific_widget = ProjectSpecificWidget(project_settings, self)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(projects_widget, 0)
        main_layout.addWidget(project_specific_widget, 1)

        projects_widget.project_changed.connect(self._on_project_change)
        # project_specific_widget.value_changed.connect(
        #     self._on_root_value_change
        # )

        self.project_settings = project_settings

        self.projects_widget = projects_widget
        self.project_specific_widget = project_specific_widget

    def _current_value(self):
        roots_value = self.project_specific_widget.settings_value()
        current_value = {}
        if roots_value:
            current_value[LOCAL_ROOTS_KEY] = roots_value
        return current_value

    def project_name(self):
        return self.projects_widget.project_name()

    def _on_project_change(self):
        project_name = self.project_name()

        self.project_settings.change_project(project_name)
        self.project_specific_widget.change_project(project_name)

    def _on_root_value_change(self):
        self.per_project_settings[self.project_name()] = (
            self._current_value()
        )

    def set_value(self, value):
        if not value:
            value = {}
        self.per_project_settings = value

        self.projects_widget.refresh()

        self.project_specific_widget.set_value(self.per_project_settings)

    def settings_value(self):
        output = {}
        for project_name, value in self.per_project_settings.items():
            if value:
                output[project_name] = value
        if not output:
            return None
        return output
