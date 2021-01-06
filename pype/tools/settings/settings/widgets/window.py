from Qt import QtWidgets, QtGui
from .base import CategoryState, SystemWidget, ProjectWidget
from .widgets import ShadowWidget
from .. import style


class MainWidget(QtWidgets.QWidget):
    widget_width = 1000
    widget_height = 600

    def __init__(self, user_role, parent=None):
        super(MainWidget, self).__init__(parent)
        self.setObjectName("MainWidget")
        self.setWindowTitle("Pype Settings")

        self.resize(self.widget_width, self.widget_height)

        stylesheet = style.load_stylesheet()
        self.setStyleSheet(stylesheet)
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

        header_tab_widget = QtWidgets.QTabWidget(parent=self)

        studio_widget = SystemWidget(user_role, header_tab_widget)
        project_widget = ProjectWidget(user_role, header_tab_widget)

        tab_widgets = [
            studio_widget,
            project_widget
        ]

        header_tab_widget.addTab(studio_widget, "System")
        header_tab_widget.addTab(project_widget, "Project")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        layout.addWidget(header_tab_widget)

        self.setLayout(layout)

        for tab_widget in tab_widgets:
            tab_widget.saved.connect(self._on_tab_save)

        self.tab_widgets = tab_widgets

    def _on_tab_save(self, source_widget):
        for tab_widget in self.tab_widgets:
            tab_widget.on_saved(source_widget)

    def reset(self):
        for tab_widget in self.tab_widgets:
            tab_widget.reset()
