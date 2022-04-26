import logging
from Qt import QtWidgets, QtGui

from openpype import style

from openpype.settings.lib import (
    get_local_settings,
    save_local_settings
)
from openpype.tools.settings import CHILD_OFFSET
from openpype.api import (
    Logger,
    SystemSettings,
    ProjectSettings
)
from openpype.modules import ModulesManager

from .widgets import (
    ExpandingWidget
)
from .mongo_widget import OpenPypeMongoWidget
from .general_widget import LocalGeneralWidgets
from .experimental_widget import (
    LocalExperimentalToolsWidgets,
    LOCAL_EXPERIMENTAL_KEY
)
from .apps_widget import LocalApplicationsWidgets
from .environments_widget import LocalEnvironmentsWidgets
from .projects_widget import ProjectSettingsWidget

from .constants import (
    LOCAL_GENERAL_KEY,
    LOCAL_PROJECTS_KEY,
    LOCAL_ENV_KEY,
    LOCAL_APPS_KEY
)

log = Logger.get_logger(__name__)


class LocalSettingsWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWidget, self).__init__(parent)

        self.system_settings = SystemSettings()
        self.project_settings = ProjectSettings()
        self.modules_manager = ModulesManager()

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.pype_mongo_widget = None
        self.general_widget = None
        self.experimental_widget = None
        self.envs_widget = None
        self.apps_widget = None
        self.projects_widget = None

        self._create_mongo_url_ui()
        self._create_general_ui()
        self._create_experimental_ui()
        self._create_environments_ui()
        self._create_app_ui()
        self._create_project_ui()

        self.main_layout.addStretch(1)

    def _create_mongo_url_ui(self):
        pype_mongo_expand_widget = ExpandingWidget("OpenPype Mongo URL", self)
        pype_mongo_content = QtWidgets.QWidget(self)
        pype_mongo_layout = QtWidgets.QVBoxLayout(pype_mongo_content)
        pype_mongo_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        pype_mongo_expand_widget.set_content_widget(pype_mongo_content)

        pype_mongo_widget = OpenPypeMongoWidget(self)
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

    def _create_experimental_ui(self):
        # General
        experimental_expand_widget = ExpandingWidget(
            "Experimental tools", self
        )

        experimental_content = QtWidgets.QWidget(self)
        experimental_layout = QtWidgets.QVBoxLayout(experimental_content)
        experimental_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        experimental_expand_widget.set_content_widget(experimental_content)

        experimental_widget = LocalExperimentalToolsWidgets(
            experimental_content
        )
        experimental_layout.addWidget(experimental_widget)

        self.main_layout.addWidget(experimental_expand_widget)

        self.experimental_widget = experimental_widget

    def _create_environments_ui(self):
        envs_expand_widget = ExpandingWidget("Environments", self)
        envs_content = QtWidgets.QWidget(self)
        envs_layout = QtWidgets.QVBoxLayout(envs_content)
        envs_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)
        envs_expand_widget.set_content_widget(envs_content)

        envs_widget = LocalEnvironmentsWidgets(
            self.system_settings, envs_content
        )
        envs_layout.addWidget(envs_widget)

        self.main_layout.addWidget(envs_expand_widget)

        self.envs_widget = envs_widget

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

        projects_widget = ProjectSettingsWidget(
            self.modules_manager, self.project_settings, self
        )
        project_layout.addWidget(projects_widget)

        self.main_layout.addWidget(project_expand_widget)

        self.projects_widget = projects_widget

    def update_local_settings(self, value):
        if not value:
            value = {}

        self.system_settings.reset()
        self.project_settings.reset()

        self.general_widget.update_local_settings(
            value.get(LOCAL_GENERAL_KEY)
        )
        self.envs_widget.update_local_settings(
            value.get(LOCAL_ENV_KEY)
        )
        self.app_widget.update_local_settings(
            value.get(LOCAL_APPS_KEY)
        )
        self.projects_widget.update_local_settings(
            value.get(LOCAL_PROJECTS_KEY)
        )
        self.experimental_widget.update_local_settings(
            value.get(LOCAL_EXPERIMENTAL_KEY)
        )

    def settings_value(self):
        output = {}
        general_value = self.general_widget.settings_value()
        if general_value:
            output[LOCAL_GENERAL_KEY] = general_value

        envs_value = self.envs_widget.settings_value()
        if envs_value:
            output[LOCAL_ENV_KEY] = envs_value

        app_value = self.app_widget.settings_value()
        if app_value:
            output[LOCAL_APPS_KEY] = app_value

        projects_value = self.projects_widget.settings_value()
        if projects_value:
            output[LOCAL_PROJECTS_KEY] = projects_value

        experimental_value = self.experimental_widget.settings_value()
        if experimental_value:
            output[LOCAL_EXPERIMENTAL_KEY] = experimental_value
        return output


class LocalSettingsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocalSettingsWindow, self).__init__(parent)

        self._reset_on_show = True

        self.resize(1000, 600)

        self.setWindowTitle("OpenPype Local settings")

        stylesheet = style.load_stylesheet()
        self.setStyleSheet(stylesheet)
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("GroupWidget")
        scroll_widget.setWidgetResizable(True)

        footer = QtWidgets.QWidget(self)

        save_btn = QtWidgets.QPushButton("Save", footer)
        reset_btn = QtWidgets.QPushButton("Reset", footer)

        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.addWidget(reset_btn, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(save_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_widget, 1)
        main_layout.addWidget(footer, 0)

        save_btn.clicked.connect(self._on_save_clicked)
        reset_btn.clicked.connect(self._on_reset_clicked)

        # Do not create local settings widget in init phase as it's using
        #   settings objects that must be OK to be able create this widget
        #   - we want to show dialog if anything goes wrong
        #   - without resetting nothing is shown
        self._settings_widget = None
        self._scroll_widget = scroll_widget
        self.reset_btn = reset_btn
        self.save_btn = save_btn

    def showEvent(self, event):
        super(LocalSettingsWindow, self).showEvent(event)
        if self._reset_on_show:
            self.reset()

    def reset(self):
        if self._reset_on_show:
            self._reset_on_show = False

        error_msg = None
        try:
            # Create settings widget if is not created yet
            if self._settings_widget is None:
                self._settings_widget = LocalSettingsWidget(
                    self._scroll_widget
                )
                self._scroll_widget.setWidget(self._settings_widget)

            value = get_local_settings()
            self._settings_widget.update_local_settings(value)

        except Exception as exc:
            log.warning(
                "Failed to create local settings window", exc_info=True
            )
            error_msg = str(exc)

        crashed = error_msg is not None
        # Enable/Disable save button if crashed or not
        self.save_btn.setEnabled(not crashed)
        # Show/Hide settings widget if crashed or not
        if self._settings_widget:
            self._settings_widget.setVisible(not crashed)

        if not crashed:
            return

        # Show message with error
        title = "Something went wrong"
        msg = (
            "Bug: Loading of settings failed."
            " Please contact your project manager or OpenPype team."
            "\n\nError message:\n{}"
        ).format(error_msg)

        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Critical,
            title,
            msg,
            QtWidgets.QMessageBox.Ok,
            self
        )
        dialog.exec_()

    def _on_reset_clicked(self):
        self.reset()

    def _on_save_clicked(self):
        value = self._settings_widget.settings_value()
        save_local_settings(value)
        self.reset()
