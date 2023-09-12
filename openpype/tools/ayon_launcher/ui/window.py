from qtpy import QtWidgets, QtCore, QtGui

from openpype import style
from openpype import resources

from openpype.tools.ayon_launcher.control import BaseLauncherController

from .projects_widget import ProjectsWidget
from .hierarchy_page import HierarchyPage
from .actions_widget import ActionsWidget


class LauncherWindow(QtWidgets.QWidget):
    """Launcher interface"""
    message_interval = 5000
    refresh_interval = 10000

    def __init__(self, controller=None, parent=None):
        super(LauncherWindow, self).__init__(parent)

        if controller is None:
            controller = BaseLauncherController()

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Launcher")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.setStyleSheet(style.load_stylesheet())

        # Allow minimize
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        self._controller = controller

        # Main content - Pages & Actions
        content_body = QtWidgets.QSplitter(self)

        # Pages
        pages_widget = QtWidgets.QWidget(content_body)

        # - First page - Projects
        projects_page = ProjectsWidget(controller, pages_widget)

        # - Second page - Hierarchy (folders & tasks)
        hierarchy_page = HierarchyPage(controller, pages_widget)

        pages_layout = QtWidgets.QStackedLayout(pages_widget)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.addWidget(projects_page)
        pages_layout.addWidget(hierarchy_page)

        # Actions
        actions_widget = ActionsWidget(controller, content_body)

        # Vertically split Pages and Actions
        content_body.setContentsMargins(0, 0, 0, 0)
        content_body.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        content_body.setOrientation(QtCore.Qt.Vertical)
        content_body.addWidget(pages_widget)
        content_body.addWidget(actions_widget)

        # Set useful default sizes and set stretch
        # for the pages so that is the only one that
        # stretches on UI resize.
        content_body.setStretchFactor(0, 10)
        content_body.setSizes([580, 160])

        # Footer
        footer_widget = QtWidgets.QWidget(self)

        # - Message label
        message_label = QtWidgets.QLabel(footer_widget)

        # action_history = ActionHistory(footer_widget)
        # action_history.setStatusTip("Show Action History")

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(message_label, 1)
        # footer_layout.addWidget(action_history, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(content_body, 1)
        layout.addWidget(footer_widget, 0)

        message_timer = QtCore.QTimer()
        message_timer.setInterval(self.message_interval)
        message_timer.setSingleShot(True)

        refresh_timer = QtCore.QTimer()
        refresh_timer.setInterval(self.refresh_interval)

        message_timer.timeout.connect(self._on_message_timeout)
        refresh_timer.timeout.connect(self._on_refresh_timeout)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_selection_change,
        )

        self._controller = controller

        self._is_on_projects_page = True
        self._window_is_active = False

        self._pages_layout = pages_layout
        self._projects_page = projects_page
        self._hierarchy_page = hierarchy_page
        self._actions_widget = actions_widget

        self._message_label = message_label
        # self._action_history = action_history

        self._message_timer = message_timer
        self._refresh_timer = refresh_timer

        self.resize(520, 740)

    def showEvent(self, event):
        super(LauncherWindow, self).showEvent(event)
        self._window_is_active = True
        self._refresh_timer.start()
        self._controller.refresh()

    def closeEvent(self, event):
        super(LauncherWindow, self).closeEvent(event)
        self._window_is_active = False
        self._refresh_timer.stop()

    def changeEvent(self, event):
        if event.type() in (
            QtCore.QEvent.Type.WindowStateChange,
            QtCore.QEvent.ActivationChange,
        ):
            is_active = self.isActiveWindow() and not self.isMinimized()
            self._window_is_active = is_active
            if is_active:
                self._on_refresh_timeout()
                self._refresh_timer.start()
            else:
                self._refresh_timer.stop()

        super(LauncherWindow, self).changeEvent(event)

    def _on_refresh_timeout(self):
        # Stop timer if widget is not visible
        if self._window_is_active:
            self._controller.refresh()
        else:
            self._refresh_timer.stop()

    def _on_message_timeout(self):
        self._message_label.setText("")

    def _echo(self, message):
        self._message_label.setText(str(message))
        self._message_timer.start()

    # def on_history_action(self, history_data):
    #     action, session = history_data
    #     app = QtWidgets.QApplication.instance()
    #     modifiers = app.keyboardModifiers()
    #
    #     is_control_down = QtCore.Qt.ControlModifier & modifiers
    #     if is_control_down:
    #         # Revert to that "session" location
    #         self.set_session(session)
    #     else:
    #         # User is holding control, rerun the action
    #         self.run_action(action, session=session)

    def _go_to_projects_page(self):
        if self._is_on_projects_page:
            return
        self._hierarchy_page.set_page_visible(False)
        self._pages_layout.setCurrentWidget(self._projects_page)
        self._is_on_projects_page = True

    def _go_to_hierarchy_page(self, project_name):
        if not self._is_on_projects_page:
            return
        self._hierarchy_page.set_page_visible(True, project_name)
        self._pages_layout.setCurrentWidget(self._hierarchy_page)
        self._is_on_projects_page = False

    def _on_project_selection_change(self, event):
        project_name = event["project_name"]
        if not project_name:
            self._go_to_projects_page()

        elif self._is_on_projects_page:
            self._go_to_hierarchy_page(project_name)
