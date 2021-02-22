import platform
import logging
from Qt import QtWidgets, QtCore
from .widgets import (
    ExpandingWidget,
    SpacerWidget
)
from .. import style
from .lib import CHILD_OFFSET
from pype.api import SystemSettings

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


class LocalSettingsWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWidget, self).__init__(parent)

        self.system_settings = SystemSettings()
        # self.project_settings = SystemSettings()
        user_settings = {}

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.general_widget = None
        self.apps_widget = None

        self._create_general_ui()
        self._create_app_ui()

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

    def set_value(self, value):
        if not value:
            value = {}

        self.general_widget.set_value(value.get("general"))
        self.app_widget.set_value(value.get("applications"))

    def settings_value(self):
        output = {}
        general_value = self.general_widget.settings_value()
        if general_value:
            output["general"] = general_value

        app_value = self.app_widget.settings_value()
        if app_value:
            output["applications"] = app_value
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
