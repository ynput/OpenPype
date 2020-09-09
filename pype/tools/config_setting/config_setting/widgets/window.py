from Qt import QtWidgets
from .base import SystemWidget, ProjectWidget


class MainWidget(QtWidgets.QWidget):
    widget_width = 1000
    widget_height = 600

    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent)

        self.resize(self.widget_width, self.widget_height)

        header_tab_widget = QtWidgets.QTabWidget(parent=self)

        studio_widget = SystemWidget()
        project_widget = ProjectWidget()
        header_tab_widget.addTab(studio_widget, "System")
        header_tab_widget.addTab(project_widget, "Project")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header_tab_widget)

        self.setLayout(layout)
