import platform
import logging
from Qt import QtWidgets, QtCore
from .widgets import (
    ExpandingWidget,
    SpacerWidget,
    ProjectListWidget
)
from .. import style
from .lib import CHILD_OFFSET
from pype.api import (
    SystemSettings,
    ProjectSettings
)

log = logging.getLogger(__name__)


class Separator(QtWidgets.QFrame):
    def __init__(self, height=None, parent=None):
        super(Separator, self).__init__(parent)
        if height is None:
            height = 2

        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setStyleSheet("background-color: #21252B;")
        splitter_item.setMinimumHeight(height)
        splitter_item.setMaximumHeight(height)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter_item)


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

        mongo_url_label = QtWidgets.QLabel("Pype Mongo URL", self)
        mongo_url_input = QtWidgets.QLineEdit(self)
        local_site_name_label = QtWidgets.QLabel("Local site name", self)
        local_site_name_input = QtWidgets.QLineEdit(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        row = 0
        layout.addWidget(mongo_url_label, row, 0)
        layout.addWidget(mongo_url_input, row, 1)
        row += 1
        layout.addWidget(local_site_name_label, row, 0)
        layout.addWidget(local_site_name_input, row, 1)

        self.mongo_url_input = mongo_url_input
        self.local_site_name_input = local_site_name_input

    def set_value(self, value):
        mongo_url = ""
        site_name = ""
        if value:
            mongo_url = value.get("mongo_url", mongo_url)
            site_name = value.get("site_name", site_name)
        self.mongo_url_input.setText(mongo_url)
        self.local_site_name_input.setText(site_name)

    def settings_value(self):
        # Add changed
        # If these have changed then
        output = {}
        mongo_url = self.mongo_url_input.text()
        if mongo_url:
            output["mongo_url"] = mongo_url

        local_site_name = self.local_site_name_input.text()
        if local_site_name:
            output["site_name"] = local_site_name
        # Do not return output yet since we don't have mechanism to save or
        #   load these data through api calls
        return None


class PathInput(QtWidgets.QWidget):
    def __init__(
        self,
        parent,
        executable_placeholder=None,
        argument_placeholder=None
    ):
        super(PathInput, self).__init__(parent)

        executable_input = QtWidgets.QLineEdit(self)
        if executable_placeholder:
            executable_input.setPlaceholderText(executable_placeholder)

        arguments_input = QtWidgets.QLineEdit(self)
        if argument_placeholder:
            arguments_input.setPlaceholderText(argument_placeholder)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(executable_input)
        layout.addWidget(arguments_input)

        self.executable_input = executable_input
        self.arguments_input = arguments_input

    def set_read_only(self, readonly=True):
        self.executable_input.setReadOnly(readonly)
        self.arguments_input.setReadOnly(readonly)

    def set_value(self, arguments):
        executable = ""
        args = ""
        if arguments:
            if isinstance(arguments, str):
                executable = arguments
            elif isinstance(arguments, list):
                executable = arguments[0]
                if len(arguments) > 1:
                    args = " ".join(arguments[1:])
        self.executable_input.setText(executable)
        self.arguments_input.setText(args)

    def settings_value(self):
        executable = self.executable_input.text()
        if not executable:
            return None

        output = [executable]
        args = self.arguments_input.text()
        if args:
            output.append(args)
        return output


class AppVariantWidget(QtWidgets.QWidget):
    exec_placeholder = "< Specific path for this machine >"
    args_placeholder = "< Launch arguments >"

    def __init__(self, group_label, variant_entity, parent):
        super(AppVariantWidget, self).__init__(parent)

        self.input_widget = None

        label = " ".join([group_label, variant_entity.label])

        expading_widget = ExpandingWidget(label, self)
        content_widget = QtWidgets.QWidget(expading_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)

        expading_widget.set_content_widget(content_widget)

        # Add expanding widget to main layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(expading_widget)

        # TODO For celaction - not sure what is "Celaction publish" for
        if not variant_entity["executables"].multiplatform:
            warn_label = QtWidgets.QLabel(
                "Application without multiplatform paths"
            )
            content_layout.addWidget(warn_label)
            return

        input_widget = PathInput(
            content_widget, self.exec_placeholder, self.args_placeholder
        )
        content_layout.addWidget(input_widget)

        studio_executables = (
            variant_entity["executables"][platform.system().lower()]
        )
        if len(studio_executables) > 0:
            content_layout.addWidget(Separator(parent=self))

        for item in studio_executables:
            path_widget = PathInput(content_widget)
            path_widget.set_read_only()
            path_widget.set_value(item.value)
            content_layout.addWidget(path_widget)

        self.input_widget = input_widget

    def set_value(self, value):
        if not self.input_widget:
            return

        if not value:
            value = []
        self.input_widget.set_value(value)

    def settings_value(self):
        if not self.input_widget:
            return None
        return self.input_widget.settings_value()


class AppGroupWidget(QtWidgets.QWidget):
    def __init__(self, group_entity, parent):
        super(AppGroupWidget, self).__init__(parent)

        valid_variants = {}
        for key, entity in group_entity["variants"].items():
            if entity["enabled"]:
                valid_variants[key] = entity

        group_label = group_entity.label
        expading_widget = ExpandingWidget(group_label, self)
        content_widget = QtWidgets.QWidget(expading_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)

        widgets_by_variant_name = {}
        for variant_name, variant_entity in valid_variants.items():
            variant_widget = AppVariantWidget(
                group_label, variant_entity, content_widget
            )
            widgets_by_variant_name[variant_name] = variant_widget
            content_layout.addWidget(variant_widget)

        expading_widget.set_content_widget(content_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(expading_widget)

        self.widgets_by_variant_name = widgets_by_variant_name

    def set_value(self, value):
        if not value:
            value = {}

        for variant_name, widget in self.widgets_by_variant_name.items():
            widget.set_value(value.get(variant_name))

    def settings_value(self):
        output = {}
        for variant_name, widget in self.widgets_by_variant_name.items():
            value = widget.settings_value()
            if value:
                output[variant_name] = value

        if not output:
            return None
        return output


class LocalApplicationsWidgets(QtWidgets.QWidget):
    def __init__(self, system_settings_entity, parent):
        super(LocalApplicationsWidgets, self).__init__(parent)

        widgets_by_group_name = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for key, entity in system_settings_entity["applications"].items():
            # Filter not enabled app groups
            if not entity["enabled"]:
                continue

            # Check if has enabled any variant
            enabled_variant = False
            for variant_entity in entity["variants"].values():
                if variant_entity["enabled"]:
                    enabled_variant = True
                    break

            if not enabled_variant:
                continue

            # Create App group specific widget and store it by the key
            group_widget = AppGroupWidget(entity, self)
            widgets_by_group_name[key] = group_widget
            layout.addWidget(group_widget)

        self.widgets_by_group_name = widgets_by_group_name

    def set_value(self, value):
        if not value:
            value = {}

        for group_name, widget in self.widgets_by_group_name.items():
            widget.set_value(value.get(group_name))

    def settings_value(self):
        output = {}
        for group_name, widget in self.widgets_by_group_name.items():
            value = widget.settings_value()
            if value:
                output[group_name] = value
        if not output:
            return None
        return output


class RootsWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, project_settings, parent):
        self._parent_widget = parent
        super(RootsWidget, self).__init__(parent)

        self.project_settings = project_settings
        self.widgts_by_root_name = {}

        main_layout = QtWidgets.QVBoxLayout(self)

        self.content_layout = main_layout

    def refresh(self):
        while self.content_layout.count():
            item = self.content_layout.itemAt(0)
            item.widget().hide()
            self.content_layout.removeItem(item)

        self.widgts_by_root_name.clear()

        default_placeholder = "< Root overrides for this machine >"
        default_root_values = self.local_default_project_values() or {}

        roots_entity = self.project_settings["project_anatomy"]["roots"]
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
                placeholder = default_placeholder
            value_input.setPlaceholderText(placeholder)
            value_input.textChanged.connect(self._on_root_value_change)

            studio_input = QtWidgets.QLineEdit(root_input_widget)
            studio_input.setText(platform_entity.value)
            studio_input.setReadOnly(True)

            root_input_layout.addWidget(value_input)
            root_input_layout.addWidget(Separator(parent=self))
            root_input_layout.addWidget(studio_input)

            root_layout = QtWidgets.QHBoxLayout(root_widget)
            root_layout.addWidget(key_label)
            root_layout.addWidget(root_input_widget)

            self.content_layout.addWidget(root_widget)
            self.widgts_by_root_name[root_name] = value_input

        self.content_layout.addWidget(SpacerWidget(self), 1)

    def _on_root_value_change(self):
        self.value_changed.emit()

    def local_default_project_values(self):
        default_project = self._parent_widget.per_project_settings.get(None)
        if default_project:
            return default_project.get("roots")
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


class ProjectSettingsWidget(QtWidgets.QWidget):
    def __init__(self, project_settings, parent):
        super(ProjectSettingsWidget, self).__init__(parent)

        self.per_project_settings = {}

        projects_widget = _ProjectListWidget(self)
        roots_widget = RootsWidget(project_settings, self)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(projects_widget, 0)
        main_layout.addWidget(roots_widget, 1)

        projects_widget.refresh()

        projects_widget.project_changed.connect(self._on_project_change)
        roots_widget.value_changed.connect(self._on_root_value_change)

        roots_widget.refresh()

        self.project_settings = project_settings

        self.projects_widget = projects_widget
        self.roots_widget = roots_widget

    def _current_value(self):
        roots_value = self.roots_widget.settings_value()
        current_value = {}
        if roots_value:
            current_value["roots"] = roots_value
        return current_value

    def project_name(self):
        return self.projects_widget.project_name()

    def _on_project_change(self):
        project_name = self.project_name()

        self.project_settings.change_project(project_name)
        self.roots_widget.refresh()

        project_value = self.per_project_settings.get(project_name) or {}
        self.roots_widget.set_value(project_value.get("roots"))

    def _on_root_value_change(self):
        self.per_project_settings[self.project_name()] = (
            self._current_value()
        )

    def set_value(self, value):
        if not value:
            value = {}
        self.per_project_settings = value

    def settings_value(self):
        output = {}
        for project_name, value in self.per_project_settings.items():
            if value:
                output[project_name] = value
        if not output:
            return None
        return output


class LocalSettingsWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWidget, self).__init__(parent)

        self.system_settings = SystemSettings()
        self.project_settings = ProjectSettings()
        user_settings = {}

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.general_widget = None
        self.apps_widget = None
        self.projects_widget = None

        self._create_general_ui()
        self._create_app_ui()
        self._create_project_ui()

        # Add spacer to main layout
        self.main_layout.addWidget(SpacerWidget(self), 1)

        self.set_value(user_settings)

    def _create_general_ui(self):
        # General
        general_expand_widget = ExpandingWidget(
            "General (Does nothing!)", self
        )

        general_content = QtWidgets.QWidget(self)
        general_layout = QtWidgets.QVBoxLayout(general_content)
        general_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        general_expand_widget.set_content_widget(general_content)

        general_widget = LocalGeneralWidgets(general_content)
        general_layout.addWidget(general_widget)

        self.main_layout.addWidget(general_expand_widget)

        self.general_widget = general_widget

    def _create_app_ui(self):
        # Applications
        app_expand_widget = ExpandingWidget("Applications", self)

        app_content = QtWidgets.QWidget(self)
        app_layout = QtWidgets.QVBoxLayout(app_content)
        app_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        app_expand_widget.set_content_widget(app_content)

        app_widget = LocalApplicationsWidgets(
            self.system_settings, app_content
        )
        app_layout.addWidget(app_widget)

        self.main_layout.addWidget(app_expand_widget)

        self.app_widget = app_widget

    def _create_project_ui(self):
        project_expand_widget = ExpandingWidget("Project settings", self)
        project_content = QtWidgets.QWidget(self)
        project_layout = QtWidgets.QVBoxLayout(project_content)
        project_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        project_expand_widget.set_content_widget(project_content)

        projects_widget = ProjectSettingsWidget(self.project_settings, self)
        project_layout.addWidget(projects_widget)

        self.main_layout.addWidget(project_expand_widget)

        self.projects_widget = projects_widget

    def set_value(self, value):
        if not value:
            value = {}

        self.general_widget.set_value(value.get("general"))
        self.app_widget.set_value(value.get("applications"))
        self.projects_widget.set_value(value.get("projects"))

    def settings_value(self):
        output = {}
        general_value = self.general_widget.settings_value()
        if general_value:
            output["general"] = general_value

        app_value = self.app_widget.settings_value()
        if app_value:
            output["applications"] = app_value

        projects_value = self.projects_widget.settings_value()
        if projects_value:
            output["projects"] = projects_value
        return output


class LocalSettingsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWindow, self).__init__(parent)

        self.resize(1000, 600)

        stylesheet = style.load_stylesheet()
        self.setStyleSheet(stylesheet)

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("GroupWidget")
        settings_widget = LocalSettingsWidget(scroll_widget)

        scroll_widget.setWidget(settings_widget)
        scroll_widget.setWidgetResizable(True)

        footer = QtWidgets.QWidget(self)
        save_btn = QtWidgets.QPushButton("Save", footer)
        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.addWidget(SpacerWidget(footer), 1)
        footer_layout.addWidget(save_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_widget, 1)
        main_layout.addWidget(footer, 0)

        save_btn.clicked.connect(self._on_save_clicked)

        self.settings_widget = settings_widget
        self.save_btn = save_btn

    def _on_save_clicked(self):
        try:
            value = self.settings_widget.settings_value()
            print(value)
        except Exception:
            log.warning("Failed to save", exc_info=True)
