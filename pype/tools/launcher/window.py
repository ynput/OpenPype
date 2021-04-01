import copy
import logging

from Qt import QtWidgets, QtCore, QtGui
from avalon import style

from avalon.api import AvalonMongoDB
from openpype.api import resources

from avalon.tools import lib as tools_lib
from avalon.tools.widgets import AssetWidget
from avalon.vendor import qtawesome
from .models import ProjectModel
from .widgets import (
    ProjectBar,
    ActionBar,
    TasksWidget,
    ActionHistory,
    SlidePageWidget
)

from .flickcharm import FlickCharm


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
        return super(IconListView, self).mousePressEvent(event)


class ProjectsPanel(QtWidgets.QWidget):
    """Projects Page"""

    project_clicked = QtCore.Signal(str)

    def __init__(self, dbcon, parent=None):
        super(ProjectsPanel, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)

        self.dbcon = dbcon
        self.dbcon.install()

        view = IconListView(parent=self)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        flick = FlickCharm(parent=self)
        flick.activateOn(view)
        model = ProjectModel(self.dbcon)
        model.hide_invisible = True
        model.refresh()
        view.setModel(model)

        layout.addWidget(view)

        view.clicked.connect(self.on_clicked)

        self.model = model
        self.view = view

    def on_clicked(self, index):
        if index.isValid():
            project_name = index.data(QtCore.Qt.DisplayRole)
            self.project_clicked.emit(project_name)


class AssetsPanel(QtWidgets.QWidget):
    """Assets page"""
    back_clicked = QtCore.Signal()
    session_changed = QtCore.Signal()

    def __init__(self, dbcon, parent=None):
        super(AssetsPanel, self).__init__(parent=parent)

        self.dbcon = dbcon

        # project bar
        project_bar_widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QHBoxLayout(project_bar_widget)
        layout.setSpacing(4)

        btn_back_icon = qtawesome.icon("fa.angle-left", color="white")
        btn_back = QtWidgets.QPushButton(project_bar_widget)
        btn_back.setIcon(btn_back_icon)
        btn_back.setFixedWidth(23)
        btn_back.setFixedHeight(23)

        project_bar = ProjectBar(self.dbcon, project_bar_widget)

        layout.addWidget(btn_back)
        layout.addWidget(project_bar)

        # assets
        assets_proxy_widgets = QtWidgets.QWidget(self)
        assets_proxy_widgets.setContentsMargins(0, 0, 0, 0)
        assets_layout = QtWidgets.QVBoxLayout(assets_proxy_widgets)
        assets_widget = AssetWidget(
            dbcon=self.dbcon, parent=assets_proxy_widgets
        )

        # Make assets view flickable
        flick = FlickCharm(parent=self)
        flick.activateOn(assets_widget.view)
        assets_widget.view.setVerticalScrollMode(
            assets_widget.view.ScrollPerPixel
        )
        assets_layout.addWidget(assets_widget)

        # tasks
        tasks_widget = TasksWidget(self.dbcon, self)
        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_proxy_widgets)
        body.addWidget(tasks_widget)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 65)

        # main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(project_bar_widget)
        layout.addWidget(body)

        self.project_bar = project_bar
        self.assets_widget = assets_widget
        self.tasks_widget = tasks_widget

        # signals
        project_bar.project_changed.connect(self.on_project_changed)
        assets_widget.selection_changed.connect(self.on_asset_changed)
        assets_widget.refreshed.connect(self.on_asset_changed)
        tasks_widget.task_changed.connect(self.on_task_change)

        btn_back.clicked.connect(self.back_clicked)

        # Force initial refresh for the assets since we might not be
        # trigging a Project switch if we click the project that was set
        # prior to launching the Launcher
        # todo: remove this behavior when AVALON_PROJECT is not required
        assets_widget.refresh()

    def set_project(self, project):
        before = self.project_bar.get_current_project()
        if before == project:
            self.assets_widget.refresh()
            return

        self.project_bar.set_project(project)
        self.on_project_changed()

    def on_project_changed(self):
        project_name = self.project_bar.get_current_project()
        self.dbcon.Session["AVALON_PROJECT"] = project_name

        self.session_changed.emit()

        self.assets_widget.refresh()

    def on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.

        """

        print("Asset changed..")

        asset_name = None
        asset_silo = None

        # Check asset on current index and selected assets
        asset_doc = self.assets_widget.get_active_asset_document()
        selected_asset_docs = self.assets_widget.get_selected_assets()
        # If there are not asset selected docs then active asset is not
        # selected
        if not selected_asset_docs:
            asset_doc = None
        elif asset_doc:
            # If selected asset doc and current asset are not same than
            # something bad happened
            if selected_asset_docs[0]["_id"] != asset_doc["_id"]:
                asset_doc = None

        if asset_doc:
            asset_name = asset_doc["name"]
            asset_silo = asset_doc.get("silo")

        self.dbcon.Session["AVALON_TASK"] = None
        self.dbcon.Session["AVALON_ASSET"] = asset_name
        self.dbcon.Session["AVALON_SILO"] = asset_silo

        self.session_changed.emit()

        asset_id = None
        if asset_doc:
            asset_id = asset_doc["_id"]
        self.tasks_widget.set_asset(asset_id)

    def on_task_change(self):
        task_name = self.tasks_widget.get_current_task()
        self.dbcon.Session["AVALON_TASK"] = task_name
        self.session_changed.emit()


class LauncherWindow(QtWidgets.QDialog):
    """Launcher interface"""

    def __init__(self, parent=None):
        super(LauncherWindow, self).__init__(parent)

        self.log = logging.getLogger(
            ".".join([__name__, self.__class__.__name__])
        )
        self.dbcon = AvalonMongoDB()

        self.setWindowTitle("Launcher")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        icon = QtGui.QIcon(resources.pype_icon_filepath())
        self.setWindowIcon(icon)
        self.setStyleSheet(style.load_stylesheet())

        # Allow minimize
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint
        )

        project_panel = ProjectsPanel(self.dbcon)
        asset_panel = AssetsPanel(self.dbcon)

        page_slider = SlidePageWidget()
        page_slider.addWidget(project_panel)
        page_slider.addWidget(asset_panel)

        # actions
        actions_bar = ActionBar(self.dbcon, self)

        # statusbar
        statusbar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(statusbar)

        message_label = QtWidgets.QLabel()
        message_label.setFixedHeight(15)

        action_history = ActionHistory()
        action_history.setStatusTip("Show Action History")

        layout.addWidget(message_label)
        layout.addWidget(action_history)

        # Vertically split Pages and Actions
        body = QtWidgets.QSplitter()
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
        layout.addWidget(statusbar)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.message_label = message_label
        self.project_panel = project_panel
        self.asset_panel = asset_panel
        self.actions_bar = actions_bar
        self.action_history = action_history
        self.page_slider = page_slider
        self._page = 0

        # signals
        actions_bar.action_clicked.connect(self.on_action_clicked)
        action_history.trigger_history.connect(self.on_history_action)
        project_panel.project_clicked.connect(self.on_project_clicked)
        asset_panel.back_clicked.connect(self.on_back_clicked)
        asset_panel.session_changed.connect(self.on_session_changed)

        # todo: Simplify this callback connection
        asset_panel.project_bar.project_changed.connect(
            self.on_project_changed
        )

        self.resize(520, 740)

    def showEvent(self, event):
        super().showEvent(event)
        # TODO implement refresh/reset which will trigger updating
        self.discover_actions()

    def set_page(self, page):
        current = self.page_slider.currentIndex()
        if current == page and self._page == page:
            return

        direction = "right" if page > current else "left"
        self._page = page
        self.page_slider.slide_view(page, direction=direction)

    def echo(self, message):
        self.message_label.setText(str(message))
        QtCore.QTimer.singleShot(5000, lambda: self.message_label.setText(""))
        self.log.debug(message)

    def on_project_changed(self):
        project_name = self.asset_panel.project_bar.get_current_project()
        self.dbcon.Session["AVALON_PROJECT"] = project_name

        # Update the Action plug-ins available for the current project
        self.discover_actions()

    def on_session_changed(self):
        self.filter_actions()

    def discover_actions(self):
        self.actions_bar.discover_actions()
        self.filter_actions()

    def filter_actions(self):
        self.actions_bar.filter_actions()

    def on_project_clicked(self, project_name):
        self.dbcon.Session["AVALON_PROJECT"] = project_name
        # Refresh projects
        self.asset_panel.set_project(project_name)
        self.set_page(1)
        self.discover_actions()

    def on_back_clicked(self):
        self.dbcon.Session["AVALON_PROJECT"] = None
        self.set_page(0)
        self.project_panel.model.refresh()    # Refresh projects
        self.discover_actions()

    def on_action_clicked(self, action):
        self.echo("Running action: {}".format(action.name))
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
        silo = session.get("AVALON_SILO")
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

        if silo:
            self.asset_panel.assets_widget.set_silo(silo)

        if asset_name:
            self.asset_panel.assets_widget.select_assets([asset_name])

        if task_name:
            # requires a forced refresh first
            self.asset_panel.on_asset_changed()
            self.asset_panel.tasks_widget.select_task(task_name)
