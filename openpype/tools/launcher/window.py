import copy
import logging

from Qt import QtWidgets, QtCore, QtGui

from avalon.api import AvalonMongoDB

from openpype import style
from openpype.api import resources

import qtawesome
from .models import (
    LauncherModel,
    ProjectModel
)
from .lib import get_action_label
from .widgets import (
    ProjectBar,
    ActionBar,
    ActionHistory,
    SlidePageWidget,
    LauncherAssetsWidget,
    LauncherTaskWidget
)

from openpype.tools.flickcharm import FlickCharm


class ProjectIconView(QtWidgets.QListView):
    """Styled ListView that allows to toggle between icon and list mode.

    Toggling between the two modes is done by Right Mouse Click.

    """

    IconMode = 0
    ListMode = 1

    def __init__(self, parent=None, mode=ListMode):
        super(ProjectIconView, self).__init__(parent=parent)

        # Workaround for scrolling being super slow or fast when
        # toggling between the two visual modes
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.setObjectName("IconView")

        self._mode = None
        self.set_mode(mode)

    def set_mode(self, mode):
        if mode == self._mode:
            return

        self._mode = mode

        if mode == self.IconMode:
            self.setViewMode(QtWidgets.QListView.IconMode)
            self.setResizeMode(QtWidgets.QListView.Adjust)
            self.setWrapping(True)
            self.setWordWrap(True)
            self.setGridSize(QtCore.QSize(151, 90))
            self.setIconSize(QtCore.QSize(50, 50))
            self.setSpacing(0)
            self.setAlternatingRowColors(False)

            self.setProperty("mode", "icon")
            self.style().polish(self)

            self.verticalScrollBar().setSingleStep(30)

        elif self.ListMode:
            self.setProperty("mode", "list")
            self.style().polish(self)

            self.setViewMode(QtWidgets.QListView.ListMode)
            self.setResizeMode(QtWidgets.QListView.Adjust)
            self.setWrapping(False)
            self.setWordWrap(False)
            self.setIconSize(QtCore.QSize(20, 20))
            self.setGridSize(QtCore.QSize(100, 25))
            self.setSpacing(0)
            self.setAlternatingRowColors(False)

            self.verticalScrollBar().setSingleStep(33.33)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.set_mode(int(not self._mode))
        return super(ProjectIconView, self).mousePressEvent(event)


class ProjectsPanel(QtWidgets.QWidget):
    """Projects Page"""
    def __init__(self, launcher_model, parent=None):
        super(ProjectsPanel, self).__init__(parent=parent)

        view = ProjectIconView(parent=self)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        flick = FlickCharm(parent=self)
        flick.activateOn(view)
        model = ProjectModel(launcher_model)
        view.setModel(model)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)

        view.clicked.connect(self.on_clicked)

        self._model = model
        self.view = view
        self._launcher_model = launcher_model

    def on_clicked(self, index):
        if index.isValid():
            project_name = index.data(QtCore.Qt.DisplayRole)
            self._launcher_model.set_project_name(project_name)


class AssetsPanel(QtWidgets.QWidget):
    """Assets page"""
    back_clicked = QtCore.Signal()
    session_changed = QtCore.Signal()

    def __init__(self, launcher_model, dbcon, parent=None):
        super(AssetsPanel, self).__init__(parent=parent)

        self.dbcon = dbcon

        # Project bar
        btn_back_icon = qtawesome.icon("fa.angle-left", color="white")
        btn_back = QtWidgets.QPushButton(self)
        btn_back.setIcon(btn_back_icon)

        project_bar = ProjectBar(launcher_model, self)

        project_bar_layout = QtWidgets.QHBoxLayout()
        project_bar_layout.setContentsMargins(0, 0, 0, 0)
        project_bar_layout.setSpacing(4)
        project_bar_layout.addWidget(btn_back)
        project_bar_layout.addWidget(project_bar)

        # Assets widget
        assets_widget = LauncherAssetsWidget(
            launcher_model, dbcon=self.dbcon, parent=self
        )
        # Make assets view flickable
        assets_widget.activate_flick_charm()

        # Tasks widget
        tasks_widget = LauncherTaskWidget(launcher_model, self.dbcon, self)

        # Body
        body = QtWidgets.QSplitter(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_widget)
        body.addWidget(tasks_widget)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 65)

        # main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(project_bar_layout)
        layout.addWidget(body)

        # signals
        launcher_model.project_changed.connect(self._on_project_changed)
        assets_widget.selection_changed.connect(self._on_asset_changed)
        assets_widget.refreshed.connect(self._on_asset_changed)
        tasks_widget.task_changed.connect(self._on_task_change)

        btn_back.clicked.connect(self.back_clicked)

        self.project_bar = project_bar
        self.assets_widget = assets_widget
        self._tasks_widget = tasks_widget
        self._btn_back = btn_back

        self._launcher_model = launcher_model

    def select_asset(self, asset_name):
        self.assets_widget.select_asset_by_name(asset_name)

    def showEvent(self, event):
        super(AssetsPanel, self).showEvent(event)

        # Change size of a btn
        # WARNING does not handle situation if combobox is bigger
        btn_size = self.project_bar.height()
        self._btn_back.setFixedSize(QtCore.QSize(btn_size, btn_size))

    def select_task_name(self, task_name):
        self._on_asset_changed()
        self._tasks_widget.select_task_name(task_name)

    def _on_project_changed(self):
        self.session_changed.emit()

    def _on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.
        """

        # Check asset on current index and selected assets
        asset_id = self.assets_widget.get_selected_asset_id()
        asset_name = self.assets_widget.get_selected_asset_name()

        self.dbcon.Session["AVALON_TASK"] = None
        self.dbcon.Session["AVALON_ASSET"] = asset_name

        self.session_changed.emit()

        self._tasks_widget.set_asset_id(asset_id)

    def _on_task_change(self):
        task_name = self._tasks_widget.get_selected_task_name()
        self.dbcon.Session["AVALON_TASK"] = task_name
        self.session_changed.emit()


class LauncherWindow(QtWidgets.QDialog):
    """Launcher interface"""
    message_timeout = 5000

    def __init__(self, parent=None):
        super(LauncherWindow, self).__init__(parent)

        self.log = logging.getLogger(
            ".".join([__name__, self.__class__.__name__])
        )
        self.dbcon = AvalonMongoDB()

        self.setWindowTitle("Launcher")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setStyleSheet(style.load_stylesheet())

        # Allow minimize
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        launcher_model = LauncherModel(self.dbcon)

        project_panel = ProjectsPanel(launcher_model)
        asset_panel = AssetsPanel(launcher_model, self.dbcon)

        page_slider = SlidePageWidget()
        page_slider.addWidget(project_panel)
        page_slider.addWidget(asset_panel)

        # actions
        actions_bar = ActionBar(launcher_model, self.dbcon, self)

        # statusbar
        message_label = QtWidgets.QLabel(self)

        action_history = ActionHistory(self)
        action_history.setStatusTip("Show Action History")

        status_layout = QtWidgets.QHBoxLayout()
        status_layout.addWidget(message_label, 1)
        status_layout.addWidget(action_history, 0)

        # Vertically split Pages and Actions
        body = QtWidgets.QSplitter(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        body.setOrientation(QtCore.Qt.Vertical)
        body.addWidget(page_slider)
        body.addWidget(actions_bar)

        # Set useful default sizes and set stretch
        # for the pages so that is the only one that
        # stretches on UI resize.
        body.setStretchFactor(0, 10)
        body.setSizes([580, 160])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addLayout(status_layout)

        message_timer = QtCore.QTimer()
        message_timer.setInterval(self.message_timeout)
        message_timer.setSingleShot(True)

        message_timer.timeout.connect(self._on_message_timeout)

        # signals
        actions_bar.action_clicked.connect(self.on_action_clicked)
        action_history.trigger_history.connect(self.on_history_action)
        launcher_model.project_changed.connect(self.on_project_change)
        launcher_model.timer_timeout.connect(self._on_refresh_timeout)
        asset_panel.back_clicked.connect(self.on_back_clicked)
        asset_panel.session_changed.connect(self.on_session_changed)

        self.resize(520, 740)

        self._page = 0

        self._message_timer = message_timer

        self._launcher_model = launcher_model

        self._message_label = message_label
        self.project_panel = project_panel
        self.asset_panel = asset_panel
        self.actions_bar = actions_bar
        self.action_history = action_history
        self.page_slider = page_slider

    def showEvent(self, event):
        self._launcher_model.set_active(True)
        self._launcher_model.start_refresh_timer(True)

        super(LauncherWindow, self).showEvent(event)

    def _on_refresh_timeout(self):
        # Stop timer if widget is not visible
        if not self.isVisible():
            self._launcher_model.stop_refresh_timer()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            self._launcher_model.set_active(self.isActiveWindow())
        super(LauncherWindow, self).changeEvent(event)

    def set_page(self, page):
        current = self.page_slider.currentIndex()
        if current == page and self._page == page:
            return

        direction = "right" if page > current else "left"
        self._page = page
        self.page_slider.slide_view(page, direction=direction)

    def _on_message_timeout(self):
        self._message_label.setText("")

    def echo(self, message):
        self._message_label.setText(str(message))
        self._message_timer.start()
        self.log.debug(message)

    def on_session_changed(self):
        self.filter_actions()

    def discover_actions(self):
        self.actions_bar.discover_actions()

    def filter_actions(self):
        self.actions_bar.filter_actions()

    def on_project_change(self, project_name):
        # Update the Action plug-ins available for the current project
        self.set_page(1)
        self.discover_actions()

    def on_back_clicked(self):
        self._launcher_model.set_project_name(None)
        self.set_page(0)
        self.discover_actions()

    def on_action_clicked(self, action):
        self.echo("Running action: {}".format(get_action_label(action)))
        self.run_action(action)

    def on_history_action(self, history_data):
        action, session = history_data
        app = QtWidgets.QApplication.instance()
        modifiers = app.keyboardModifiers()

        is_control_down = QtCore.Qt.ControlModifier & modifiers
        if is_control_down:
            # Revert to that "session" location
            self.set_session(session)
        else:
            # User is holding control, rerun the action
            self.run_action(action, session=session)

    def run_action(self, action, session=None):
        if session is None:
            session = copy.deepcopy(self.dbcon.Session)

        filtered_session = {
            key: value
            for key, value in session.items()
            if value
        }
        # Add to history
        self.action_history.add_action(action, filtered_session)

        # Process the Action
        try:
            action().process(filtered_session)
        except Exception as exc:
            self.log.warning("Action launch failed.", exc_info=True)
            self.echo("Failed: {}".format(str(exc)))

    def set_session(self, session):
        project_name = session.get("AVALON_PROJECT")
        asset_name = session.get("AVALON_ASSET")
        task_name = session.get("AVALON_TASK")

        if project_name:
            # Force the "in project" view.
            self.page_slider.slide_view(1, direction="right")
            index = self.asset_panel.project_bar.project_combobox.findText(
                project_name
            )
            if index >= 0:
                self.asset_panel.project_bar.project_combobox.setCurrentIndex(
                    index
                )

        if asset_name:
            self.asset_panel.select_asset(asset_name)

        if task_name:
            # requires a forced refresh first
            self.asset_panel.select_task_name(task_name)
