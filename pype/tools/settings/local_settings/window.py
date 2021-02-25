import logging
from Qt import QtWidgets, QtCore, QtGui

from ..settings import style

from pype.settings.lib import (
    get_local_settings,
    save_local_settings
)
from pype.api import (
    SystemSettings,
    ProjectSettings
)

from .widgets import (
    Separator,
    SpacerWidget,
    ExpandingWidget,
    CHILD_OFFSET
)
from .mongo_widget import PypeMongoWidget
from .apps_widget import LocalApplicationsWidgets
from .projects_widget import ProjectSettingsWidget

log = logging.getLogger(__name__)

LOCAL_GENERAL_KEY = "general"
LOCAL_PROJECTS_KEY = "projects"
LOCAL_APPS_KEY = "applications"


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

        local_site_name_input = QtWidgets.QLineEdit(self)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addRow("Local site label", local_site_name_input)

        self.local_site_name_input = local_site_name_input

    def set_value(self, value):
        site_label = ""
        if value:
            site_label = value.get("site_label", site_label)
        self.local_site_name_input.setText(site_label)

    def settings_value(self):
        # Add changed
        # If these have changed then
        output = {}
        local_site_name = self.local_site_name_input.text()
        if local_site_name:
            output["site_label"] = local_site_name
        # Do not return output yet since we don't have mechanism to save or
        #   load these data through api calls
        return output


class LocalSettingsWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWidget, self).__init__(parent)

        self.system_settings = SystemSettings()
        self.project_settings = ProjectSettings()

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.pype_mongo_widget = None
        self.general_widget = None
        self.apps_widget = None
        self.projects_widget = None

        self._create_pype_mongo_ui()
        self._create_general_ui()
        self._create_app_ui()
        self._create_project_ui()

        # Add spacer to main layout
        self.main_layout.addWidget(SpacerWidget(self), 1)

    def _create_pype_mongo_ui(self):
        pype_mongo_expand_widget = ExpandingWidget("Pype Mongo URL", self)
        pype_mongo_content = QtWidgets.QWidget(self)
        pype_mongo_layout = QtWidgets.QVBoxLayout(pype_mongo_content)
        pype_mongo_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        pype_mongo_expand_widget.set_content_widget(pype_mongo_content)

        pype_mongo_widget = PypeMongoWidget(self)
        pype_mongo_layout.addWidget(pype_mongo_widget)

        self.main_layout.addWidget(pype_mongo_expand_widget)

        self.pype_mongo_widget = pype_mongo_widget

    def _create_general_ui(self):
        # General
        general_expand_widget = ExpandingWidget("General", self)

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

        self.general_widget.set_value(value.get(LOCAL_GENERAL_KEY))
        self.app_widget.set_value(value.get(LOCAL_APPS_KEY))
        self.projects_widget.set_value(value.get(LOCAL_PROJECTS_KEY))

    def settings_value(self):
        output = {}
        general_value = self.general_widget.settings_value()
        if general_value:
            output[LOCAL_GENERAL_KEY] = general_value

        app_value = self.app_widget.settings_value()
        if app_value:
            output[LOCAL_APPS_KEY] = app_value

        projects_value = self.projects_widget.settings_value()
        if projects_value:
            output[LOCAL_PROJECTS_KEY] = projects_value
        return output


class LocalSettingsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWindow, self).__init__(parent)

        self.resize(1000, 600)

        self.setWindowTitle("Pype Local settings")

        stylesheet = style.load_stylesheet()
        self.setStyleSheet(stylesheet)
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

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

        self.reset()

    def reset(self):
        value = get_local_settings()
        self.settings_widget.set_value(value)

    def _on_save_clicked(self):
        try:
            value = self.settings_widget.settings_value()
        except Exception:
            log.warning("Failed to save", exc_info=True)
            return

        save_local_settings(value)
