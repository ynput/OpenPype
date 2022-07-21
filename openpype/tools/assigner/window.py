from Qt import QtWidgets

from openpype import style
from openpype.tools.utils import PlaceholderLineEdit

from .controller import AssignerController
from .widgets import (
    ContainersWidget,
    FamiliesWidget,
    VersionsWidget,
    ThumbnailsWidget,
    VersionsInformationWidget,
)


class ConnectionWindow(QtWidgets.QWidget):
    def __init__(self, host, parent=None):
        super(ConnectionWindow, self).__init__(parent)

        controller = AssignerController(host)

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

        # Conteiners widget
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
        #   - contains thumbnails and informations about selected version
        right_side_widget = QtWidgets.QWidget(main_splitter)
        thumbnails_widget = ThumbnailsWidget(right_side_widget)
        version_info_widget = VersionsInformationWidget(right_side_widget)

        right_side_layout = QtWidgets.QVBoxLayout(right_side_widget)
        right_side_layout.setContentsMargins(0, 0, 0, 0)
        right_side_layout.addWidget(thumbnails_widget, 0)
        right_side_layout.addWidget(version_info_widget, 0)

        # Add widgets to splitter
        main_splitter.addWidget(left_side_widget)
        main_splitter.addWidget(versions_widget)
        main_splitter.addWidget(right_side_widget)

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
