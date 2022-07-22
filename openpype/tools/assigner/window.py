from Qt import QtWidgets, QtCore, QtGui

from openpype import style, resources
from openpype.tools.utils import PlaceholderLineEdit

from .controller import AssignerController
from .widgets import (
    ContainersWidget,
    FamiliesWidget,
    ThumbnailsWidget,
    VersionsInformationWidget,
)
from .versions_widget import VersionsWidget


class ConnectionWindow(QtWidgets.QWidget):
    def __init__(self, host, parent=None):
        super(ConnectionWindow, self).__init__(parent)

        controller = AssignerController(host)

        title = "Assigner"
        project_name = controller.project_name
        if project_name:
            title += " - {}".format(project_name)
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())

        self.setWindowTitle(title)
        self.setWindowIcon(icon)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        main_splitter = QtWidgets.QSplitter(self)

        # Left side widget
        #   - contains containers and families filter
        left_side_widget = QtWidgets.QWidget(main_splitter)

        # Containers filtering
        filtering_widget = QtWidgets.QWidget(left_side_widget)
        subset_name_filter_input = PlaceholderLineEdit(filtering_widget)
        subset_name_filter_input.setPlaceholderText("Filtere subsets...")

        filtering_layout = QtWidgets.QHBoxLayout(filtering_widget)
        filtering_layout.setContentsMargins(0, 0, 0, 0)
        filtering_layout.addWidget(subset_name_filter_input, 1)

        # Containers widget
        containers_widget = ContainersWidget(controller, left_side_widget)
        # Families widget (for filtering of families in versions widget)
        families_widget = FamiliesWidget(left_side_widget)

        left_side_layout = QtWidgets.QVBoxLayout(left_side_widget)
        left_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_layout.addWidget(filtering_widget, 0)
        left_side_layout.addWidget(containers_widget, 2)
        left_side_layout.addWidget(families_widget, 1)

        # Versions widget with subset/version
        versions_widget = VersionsWidget(controller, main_splitter)

        # Right side widget
        #   - contains thumbnails and information about selected version
        right_side_splitter = QtWidgets.QSplitter(main_splitter)
        thumbnails_widget = ThumbnailsWidget(controller, right_side_splitter)
        version_info_widget = VersionsInformationWidget(
            controller, right_side_splitter
        )

        right_side_splitter.setOrientation(QtCore.Qt.Vertical)
        right_side_splitter.addWidget(thumbnails_widget)
        right_side_splitter.addWidget(version_info_widget)

        right_side_splitter.setStretchFactor(0, 30)
        right_side_splitter.setStretchFactor(1, 35)

        # Add widgets to splitter
        main_splitter.addWidget(left_side_widget)
        main_splitter.addWidget(versions_widget)
        main_splitter.addWidget(right_side_splitter)

        # Add splitter to layout of window
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(main_splitter, 1)

        subset_name_filter_input.textChanged.connect(
            self._on_subset_name_filter
        )

        self._controller = controller

        self._containers_widget = containers_widget

        self._first_show = True

    def showEvent(self, event):
        super(ConnectionWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())
            self.resize(1600, 850)
            self.refresh()

    def refresh(self):
        self._containers_widget.refresh_model()

    def _on_subset_name_filter(self, text):
        self._containers_widget.set_subset_name_filter(text)
