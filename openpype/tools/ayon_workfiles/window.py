from qtpy import QtCore, QtWidgets, QtGui

from openpype import style, resources

from .widgets import (
    SidePanelWidget,
    FoldersWidget,
    TasksWidget,
    FilesWidget,
)
from .control import BaseWorkfileController


class WorkfilesToolWindow(QtWidgets.QWidget):
    """WorkFiles Window"""
    title = "Work Files"

    def __init__(self, controller=None, parent=None):
        super(WorkfilesToolWindow, self).__init__(parent=parent)

        if controller is None:
            controller = BaseWorkfileController()

        self.setWindowTitle(self.title)
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)

        # Create pages widget and set it as central widget
        pages_widget = QtWidgets.QStackedWidget(self)

        home_page_widget = QtWidgets.QWidget(pages_widget)
        home_body_widget = QtWidgets.QWidget(home_page_widget)

        folder_widget = FoldersWidget(controller, home_body_widget)
        tasks_widget = TasksWidget(controller, home_body_widget)
        files_widget = FilesWidget(controller, home_body_widget)
        side_panel = SidePanelWidget(controller, home_body_widget)

        pages_widget.addWidget(home_page_widget)

        # Build home
        home_page_layout = QtWidgets.QVBoxLayout(home_page_widget)
        home_page_layout.addWidget(home_body_widget)

        # Build home - body
        body_layout = QtWidgets.QVBoxLayout(home_body_widget)
        split_widget = QtWidgets.QSplitter(home_body_widget)
        split_widget.addWidget(folder_widget)
        split_widget.addWidget(tasks_widget)
        split_widget.addWidget(files_widget)
        split_widget.addWidget(side_panel)
        split_widget.setSizes([255, 160, 455, 175])

        body_layout.addWidget(split_widget)

        # Add top margin for tasks to align it visually with files as
        # the files widget has a filter field which tasks does not.
        tasks_widget.setContentsMargins(0, 32, 0, 0)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(pages_widget, 1)

        files_widget.file_opened.connect(self._on_file_opened)

        self._home_page_widget = home_page_widget
        self._pages_widget = pages_widget
        self._home_body_widget = home_body_widget
        self._split_widget = split_widget

        self._folder_widget = folder_widget
        self._tasks_widget = tasks_widget
        self._files_widget = files_widget
        self._side_panel = side_panel

        # Force focus on the open button by default, required for Houdini.
        files_widget.setFocus()

        self.resize(1200, 600)

        self._controller = controller

        self._first_show = True
        self._context_to_set = None

    def ensure_visible(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        super(WorkfilesToolWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.refresh()
            self.setStyleSheet(style.load_stylesheet())

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidentally perform Maya commands
        whilst trying to name an instance.
        """

        pass

    def _on_file_opened(self):
        self.close()

    def refresh(self):
        self._controller.refresh()

    def _on_folder_changed(self):
        pass

    def _on_task_changed(self):
        pass
