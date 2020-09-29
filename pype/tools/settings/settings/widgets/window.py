from Qt import QtWidgets
from .base import SystemWidget, ProjectWidget


class MainWidget(QtWidgets.QWidget):
    widget_width = 1000
    widget_height = 600

    def __init__(self, develop, parent=None):
        super(MainWidget, self).__init__(parent)
        self.setObjectName("MainWidget")
        self.setWindowTitle("Pype Settings")

        self.resize(self.widget_width, self.widget_height)

        header_tab_widget = QtWidgets.QTabWidget(parent=self)

        studio_widget = SystemWidget(develop, header_tab_widget)
        project_widget = ProjectWidget(develop, header_tab_widget)
        header_tab_widget.addTab(studio_widget, "System")
        header_tab_widget.addTab(project_widget, "Project")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        layout.addWidget(header_tab_widget)

        self.setLayout(layout)
