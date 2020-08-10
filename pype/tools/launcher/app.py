import sys
import copy

from avalon.vendor.Qt import QtWidgets, QtCore, QtGui
from avalon import io, api, style

from avalon.tools import lib as tools_lib
from avalon.tools.widgets import AssetWidget
from avalon.vendor import qtawesome
from .models import ProjectModel
from .widgets import (
    ProjectBar, ActionBar, TasksWidget, ActionHistory, SlidePageWidget
)

from .flickcharm import FlickCharm

module = sys.modules[__name__]
module.window = None


class IconListView(QtWidgets.QListView):
    """Styled ListView that allows to toggle between icon and list mode.

    Toggling between the two modes is done by Right Mouse Click.

    """

    IconMode = 0
    ListMode = 1

    def __init__(self, parent=None, mode=ListMode):
        super(IconListView, self).__init__(parent=parent)

        # Workaround for scrolling being super slow or fast when
        # toggling between the two visual modes
        self.setVerticalScrollMode(self.ScrollPerPixel)

        self._mode = 0
        self.set_mode(mode)

    def set_mode(self, mode):
        if mode == self.IconMode:
            self.setViewMode(QtWidgets.QListView.IconMode)
            self.setResizeMode(QtWidgets.QListView.Adjust)
            self.setWrapping(True)
            self.setWordWrap(True)
            self.setGridSize(QtCore.QSize(151, 90))
            self.setIconSize(QtCore.QSize(50, 50))
            self.setSpacing(0)
            self.setAlternatingRowColors(False)

            self.setStyleSheet("""
            QListView {
                font-size: 11px;
                border: 0px;
                padding: 0px;
                margin: 0px;

            }

            QListView::item  {
                margin-top: 6px;
                /* Won't work without borders set */
                border: 0px;
            }

            /* For icon only */
            QListView::icon {
                top: 3px;
            }
            """)

            self.verticalScrollBar().setSingleStep(30)

        elif self.ListMode:
            self.setStyleSheet("")   # clear stylesheet
            self.setViewMode(QtWidgets.QListView.ListMode)
            self.setResizeMode(QtWidgets.QListView.Adjust)
            self.setWrapping(False)
            self.setWordWrap(False)
            self.setIconSize(QtCore.QSize(20, 20))
            self.setGridSize(QtCore.QSize(100, 25))
            self.setSpacing(0)
            self.setAlternatingRowColors(False)

            self.verticalScrollBar().setSingleStep(33.33)

        self._mode = mode

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.set_mode(int(not self._mode))
        return super(IconListView, self).mousePressEvent(event)


class ProjectsPanel(QtWidgets.QWidget):
    """Projects Page"""

    project_clicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(ProjectsPanel, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)

        io.install()
        view = IconListView(parent=self)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        flick = FlickCharm(parent=self)
        flick.activateOn(view)
        model = ProjectModel()
        model.hide_invisible = True
        model.refresh()
        view.setModel(model)

        layout.addWidget(view)

        view.clicked.connect(self.on_clicked)

        self.model = model
        self.view = view

    def on_clicked(self, index):
        if index.isValid():
            project = index.data(QtCore.Qt.DisplayRole)
            self.project_clicked.emit(project)


class AssetsPanel(QtWidgets.QWidget):
    """Assets page"""

    back_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(AssetsPanel, self).__init__(parent=parent)

        # project bar
        project_bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(project_bar)
        layout.setSpacing(4)

        icon = qtawesome.icon("fa.angle-left", color="white")
        back = QtWidgets.QPushButton()
        back.setIcon(icon)
        back.setFixedWidth(23)
        back.setFixedHeight(23)
        projects = ProjectBar()
        projects.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(back)
        layout.addWidget(projects)

        # assets
        assets_proxy_widgets = QtWidgets.QWidget()
        assets_proxy_widgets.setContentsMargins(0, 0, 0, 0)
        assets_layout = QtWidgets.QVBoxLayout(assets_proxy_widgets)
        assets_widgets = AssetWidget()

        # Make assets view flickable
        flick = FlickCharm(parent=self)
        flick.activateOn(assets_widgets.view)
        assets_widgets.view.setVerticalScrollMode(
            assets_widgets.view.ScrollPerPixel
        )
        assets_layout.addWidget(assets_widgets)

        # tasks
        tasks_widgets = TasksWidget()
        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_proxy_widgets)
        body.addWidget(tasks_widgets)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 65)

        # main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(project_bar)
        layout.addWidget(body)

        self.data = {
            "model": {
                "projects": projects,
                "assets": assets_widgets,
                "tasks": tasks_widgets
            },
        }

        # signals
        projects.project_changed.connect(self.on_project_changed)
        assets_widgets.selection_changed.connect(self.asset_changed)
        back.clicked.connect(self.back_clicked)

        # Force initial refresh for the assets since we might not be
        # trigging a Project switch if we click the project that was set
        # prior to launching the Launcher
        # todo: remove this behavior when AVALON_PROJECT is not required
        assets_widgets.refresh()

    def set_project(self, project):

        projects = self.data["model"]["projects"]

        before = projects.get_current_project()
        projects.set_project(project)
        if project == before:
            # Force a refresh on the assets if the project hasn't changed
            self.data["model"]["assets"].refresh()

    def asset_changed(self):
        tools_lib.schedule(self.on_asset_changed, 0.05,
                           channel="assets")

    def on_project_changed(self):

        project = self.data["model"]["projects"].get_current_project()

        api.Session["AVALON_PROJECT"] = project
        self.data["model"]["assets"].refresh()

        # Force asset change callback to ensure tasks are correctly reset
        self.asset_changed()

    def on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.

        """

        print("Asset changed..")

        tasks = self.data["model"]["tasks"]
        assets = self.data["model"]["assets"]

        asset = assets.get_active_asset_document()
        if asset:
            tasks.set_asset(asset["_id"])
        else:
            tasks.set_asset(None)

    def _get_current_session(self):

        tasks = self.data["model"]["tasks"]
        assets = self.data["model"]["assets"]

        asset = assets.get_active_asset_document()
        session = copy.deepcopy(api.Session)

        # Clear some values that we are about to collect if available
        session.pop("AVALON_SILO", None)
        session.pop("AVALON_ASSET", None)
        session.pop("AVALON_TASK", None)

        if asset:
            session["AVALON_ASSET"] = asset["name"]

            silo = asset.get("silo")
            if silo:
                session["AVALON_SILO"] = silo

            task = tasks.get_current_task()
            if task:
                session["AVALON_TASK"] = task

        return session


class Window(QtWidgets.QDialog):
    """Launcher interface"""

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.setWindowTitle("Launcher")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Allow minimize
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint
        )

        project_panel = ProjectsPanel()
        asset_panel = AssetsPanel()

        pages = SlidePageWidget()
        pages.addWidget(project_panel)
        pages.addWidget(asset_panel)

        # actions
        actions = ActionBar()

        # statusbar
        statusbar = QtWidgets.QWidget()
        message = QtWidgets.QLabel()
        message.setFixedHeight(15)
        action_history = ActionHistory()
        action_history.setStatusTip("Show Action History")
        layout = QtWidgets.QHBoxLayout(statusbar)
        layout.addWidget(message)
        layout.addWidget(action_history)

        # Vertically split Pages and Actions
        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        body.setOrientation(QtCore.Qt.Vertical)
        body.addWidget(pages)
        body.addWidget(actions)

        # Set useful default sizes and set stretch
        # for the pages so that is the only one that
        # stretches on UI resize.
        body.setStretchFactor(0, 10)
        body.setSizes([580, 160])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(statusbar)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.data = {
            "label": {
                "message": message,
            },
            "pages": {
                "project": project_panel,
                "asset": asset_panel
            },
            "model": {
                "actions": actions,
                "action_history": action_history
            },
        }

        self.pages = pages
        self._page = 0

        # signals
        actions.action_clicked.connect(self.on_action_clicked)
        action_history.trigger_history.connect(self.on_history_action)
        project_panel.project_clicked.connect(self.on_project_clicked)
        asset_panel.back_clicked.connect(self.on_back_clicked)

        # Add some signals to propagate from the asset panel
        for signal in [
            asset_panel.data["model"]["projects"].project_changed,
            asset_panel.data["model"]["assets"].selection_changed,
            asset_panel.data["model"]["tasks"].task_changed
        ]:
            signal.connect(self.on_session_changed)

        # todo: Simplify this callback connection
        asset_panel.data["model"]["projects"].project_changed.connect(
            self.on_project_changed
        )

        self.resize(520, 740)

    def set_page(self, page):

        current = self.pages.currentIndex()
        if current == page and self._page == page:
            return

        direction = "right" if page > current else "left"
        self._page = page
        self.pages.slide_view(page, direction=direction)

    def refresh(self):
        asset = self.data["pages"]["asset"]
        asset.data["model"]["assets"].refresh()
        self.refresh_actions()

    def echo(self, message):
        widget = self.data["label"]["message"]
        widget.setText(str(message))

        QtCore.QTimer.singleShot(5000, lambda: widget.setText(""))

        print(message)

    def on_project_changed(self):
        project_name = self.data["pages"]["asset"].data["model"]["projects"].get_current_project()
        io.Session["AVALON_PROJECT"] = project_name

        # Update the Action plug-ins available for the current project
        actions_model = self.data["model"]["actions"].model
        actions_model.discover()

    def on_session_changed(self):
        self.refresh_actions()

    def refresh_actions(self, delay=1):
        tools_lib.schedule(self.on_refresh_actions, delay)

    def on_project_clicked(self, project):
        io.Session["AVALON_PROJECT"] = project
        asset_panel = self.data["pages"]["asset"]
        asset_panel.data["model"]["projects"].refresh()  # Refresh projects
        asset_panel.set_project(project)
        self.set_page(1)
        self.refresh_actions()

    def on_back_clicked(self):

        self.set_page(0)
        self.data["pages"]["project"].model.refresh()    # Refresh projects
        self.refresh_actions()

    def on_refresh_actions(self):
        session = self.get_current_session()

        actions = self.data["model"]["actions"]
        actions.model.set_session(session)
        actions.model.refresh()

    def on_action_clicked(self, action):
        self.echo("Running action: %s" % action.name)
        self.run_action(action)

    def on_history_action(self, history_data):
        action, session = history_data
        app = QtWidgets.QApplication.instance()
        modifiers = app.keyboardModifiers()

        is_control_down = QtCore.Qt.ControlModifier & modifiers
        if is_control_down:
            # User is holding control, rerun the action
            self.run_action(action, session=session)
        else:
            # Revert to that "session" location
            self.set_session(session)

    def get_current_session(self):

        index = self._page
        if index == 1:
            # Assets page
            return self.data["pages"]["asset"]._get_current_session()

        else:
            session = copy.deepcopy(api.Session)

            # Remove some potential invalid session values
            # that we know are not set when not browsing in
            # a project.
            session.pop("AVALON_PROJECT", None)
            session.pop("AVALON_ASSET", None)
            session.pop("AVALON_SILO", None)
            session.pop("AVALON_TASK", None)

            return session

    def run_action(self, action, session=None):

        if session is None:
            session = self.get_current_session()

        # Add to history
        history = self.data["model"]["action_history"]
        history.add_action(action, session)

        # Process the Action
        action().process(session)

    def set_session(self, session):

        panel = self.data["pages"]["asset"]

        project = session.get("AVALON_PROJECT")
        silo = session.get("AVALON_SILO")
        asset = session.get("AVALON_ASSET")
        task = session.get("AVALON_TASK")

        if project:

            # Force the "in project" view.
            self.pages.slide_view(1, direction="right")

            projects = panel.data["model"]["projects"]
            index = projects.view.findText(project)
            if index >= 0:
                projects.view.setCurrentIndex(index)

        if silo:
            panel.data["model"]["assets"].set_silo(silo)

        if asset:
            panel.data["model"]["assets"].select_assets([asset])

        if task:
            panel.on_asset_changed()     # requires a forced refresh first
            panel.data["model"]["tasks"].select_task(task)


class Application(QtWidgets.QApplication):

    def __init__(self, *args):
        super(Application, self).__init__(*args)

        # Set app icon
        icon_path = tools_lib.resource("icons", "png", "avalon-logo-16.png")
        icon = QtGui.QIcon(icon_path)

        self.setWindowIcon(icon)

        # Toggles
        self.toggles = {"autoHide": False}

        # Timers
        keep_visible = QtCore.QTimer(self)
        keep_visible.setInterval(100)
        keep_visible.setSingleShot(True)

        timers = {"keepVisible": keep_visible}

        tray = QtWidgets.QSystemTrayIcon(icon)
        tray.setToolTip("Avalon Launcher")

        # Signals
        tray.activated.connect(self.on_tray_activated)
        self.aboutToQuit.connect(self.on_quit)

        menu = self.build_menu()
        tray.setContextMenu(menu)
        tray.show()

        tray.showMessage("Avalon", "Launcher started.")

        # Don't close the app when we close the log window.
        # self.setQuitOnLastWindowClosed(False)

        self.focusChanged.connect(self.on_focus_changed)

        window = Window()
        window.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.timers = timers
        self._tray = tray
        self._window = window

        # geometry = self.calculate_window_geometry(window)
        # window.setGeometry(geometry)

    def show(self):
        """Show the primary GUI

        This also activates the window and deals with platform-differences.

        """

        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

        self.timers["keepVisible"].start()

    def on_tray_activated(self, reason):
        if self._window.isVisible():
            self._window.hide()

        elif reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.show()

    def on_focus_changed(self, old, new):
        """Respond to window losing focus"""
        window = new
        keep_visible = self.timers["keepVisible"].isActive()
        self._window.hide() if (self.toggles["autoHide"] and
                                not window and
                                not keep_visible) else None

    def on_autohide_changed(self, auto_hide):
        """Respond to changes to auto-hide

        Auto-hide is changed in the UI and determines whether or not
        the UI hides upon losing focus.

        """

        self.toggles["autoHide"] = auto_hide
        self.echo("Hiding when losing focus" if auto_hide else "Stays visible")

    def on_quit(self):
        """Respond to the application quitting"""
        self._tray.hide()

    def build_menu(self):
        """Build the right-mouse context menu for the tray icon"""
        menu = QtWidgets.QMenu()

        icon = qtawesome.icon("fa.eye", color=style.colors.default)
        open = QtWidgets.QAction(icon, "Open", self)
        open.triggered.connect(self.show)

        def toggle():
            self.on_autohide_changed(not self.toggles['autoHide'])

        keep_open = QtWidgets.QAction("Keep open", self)
        keep_open.setCheckable(True)
        keep_open.setChecked(not self.toggles['autoHide'])
        keep_open.triggered.connect(toggle)

        quit = QtWidgets.QAction("Quit", self)
        quit.triggered.connect(self.quit)

        menu.setStyleSheet("""
        QMenu {
            padding: 0px;
            margin: 0px;
        }
        """)

        for action in [open, keep_open, quit]:
            menu.addAction(action)

        return menu

    def calculate_window_geometry(self, window):
        """Respond to status changes

        On creation, align window with where the tray icon is
        located. For example, if the tray icon is in the upper
        right corner of the screen, then this is where the
        window is supposed to appear.

        Arguments:
            status (int): Provided by Qt, the status flag of
                loading the input file.

        """

        tray_x = self._tray.geometry().x()
        tray_y = self._tray.geometry().y()

        width = window.width()
        width = max(width, window.minimumWidth())

        height = window.height()
        height = max(height, window.sizeHint().height())

        desktop_geometry = QtWidgets.QDesktopWidget().availableGeometry()
        screen_geometry = window.geometry()

        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Calculate width and height of system tray
        systray_width = screen_geometry.width() - desktop_geometry.width()
        systray_height = screen_geometry.height() - desktop_geometry.height()

        padding = 10

        x = screen_width - width
        y = screen_height - height

        if tray_x < (screen_width / 2):
            x = 0 + systray_width + padding
        else:
            x -= systray_width + padding

        if tray_y < (screen_height / 2):
            y = 0 + systray_height + padding
        else:
            y -= systray_height + padding

        return QtCore.QRect(x, y, width, height)


def show(root=None, debug=False, parent=None):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): When provided parent the interface
            to this QObject.

    """

    app = Application(sys.argv)
    app.setStyleSheet(style.load_stylesheet())

    # Show the window on launch
    app.show()

    app.exec_()


def cli(args):
    import argparse
    parser = argparse.ArgumentParser()
    #parser.add_argument("project")

    args = parser.parse_args(args)
    #project = args.project

    import launcher.actions as actions
    print("Registering default actions..")
    actions.register_default_actions()
    print("Registering config actions..")
    actions.register_config_actions()
    print("Registering environment actions..")
    actions.register_environment_actions()
    io.install()

    #api.Session["AVALON_PROJECT"] = project

    import traceback
    sys.excepthook = lambda typ, val, tb: traceback.print_last()

    show()
