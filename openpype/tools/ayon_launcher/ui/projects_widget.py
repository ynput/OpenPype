from qtpy import QtWidgets, QtCore

from openpype.tools.flickcharm import FlickCharm
from openpype.tools.utils import PlaceholderLineEdit, RefreshButton
from openpype.tools.ayon_utils.widgets import (
    ProjectsQtModel,
    ProjectSortFilterProxy,
)
from openpype.tools.ayon_utils.models import PROJECTS_MODEL_SENDER


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
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
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

            self.verticalScrollBar().setSingleStep(34)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.set_mode(int(not self._mode))
        return super(ProjectIconView, self).mousePressEvent(event)


class ProjectsWidget(QtWidgets.QWidget):
    """Projects Page"""

    refreshed = QtCore.Signal()

    def __init__(self, controller, parent=None):
        super(ProjectsWidget, self).__init__(parent=parent)

        header_widget = QtWidgets.QWidget(self)

        projects_filter_text = PlaceholderLineEdit(header_widget)
        projects_filter_text.setPlaceholderText("Filter projects...")

        refresh_btn = RefreshButton(header_widget)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(projects_filter_text, 1)
        header_layout.addWidget(refresh_btn, 0)

        projects_view = ProjectIconView(parent=self)
        projects_view.setSelectionMode(QtWidgets.QListView.NoSelection)
        flick = FlickCharm(parent=self)
        flick.activateOn(projects_view)
        projects_model = ProjectsQtModel(controller)
        projects_proxy_model = ProjectSortFilterProxy()
        projects_proxy_model.setSourceModel(projects_model)

        projects_view.setModel(projects_proxy_model)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(header_widget, 0)
        main_layout.addWidget(projects_view, 1)

        projects_view.clicked.connect(self._on_view_clicked)
        projects_model.refreshed.connect(self.refreshed)
        projects_filter_text.textChanged.connect(
            self._on_project_filter_change)
        refresh_btn.clicked.connect(self._on_refresh_clicked)

        controller.register_event_callback(
            "projects.refresh.finished",
            self._on_projects_refresh_finished
        )

        self._controller = controller

        self._projects_view = projects_view
        self._projects_model = projects_model
        self._projects_proxy_model = projects_proxy_model

    def has_content(self):
        """Model has at least one project.

        Returns:
             bool: True if there is any content in the model.
        """

        return self._projects_model.has_content()

    def _on_view_clicked(self, index):
        if not index.isValid():
            return
        model = index.model()
        flags = model.flags(index)
        if not flags & QtCore.Qt.ItemIsEnabled:
            return
        project_name = index.data(QtCore.Qt.DisplayRole)
        self._controller.set_selected_project(project_name)

    def _on_project_filter_change(self, text):
        self._projects_proxy_model.setFilterFixedString(text)

    def _on_refresh_clicked(self):
        self._controller.refresh()

    def _on_projects_refresh_finished(self, event):
        if event["sender"] != PROJECTS_MODEL_SENDER:
            self._projects_model.refresh()
