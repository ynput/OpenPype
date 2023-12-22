from qtpy import QtCore, QtWidgets, QtGui

from openpype import style, resources
from openpype.tools.utils import (
    PlaceholderLineEdit,
    MessageOverlayObject,
)

from openpype.tools.ayon_utils.widgets import FoldersWidget, TasksWidget
from openpype.tools.ayon_workfiles.control import BaseWorkfileController
from openpype.tools.utils import GoToCurrentButton, RefreshButton

from .side_panel import SidePanelWidget
from .files_widget import FilesWidget
from .utils import BaseOverlayFrame


class InvalidHostOverlay(BaseOverlayFrame):
    def __init__(self, parent):
        super(InvalidHostOverlay, self).__init__(parent)

        label_widget = QtWidgets.QLabel(
            (
                "Workfiles tool is not supported in this host/DCCs."
                "<br/><br/>This may be caused by a bug."
                " Please contact your TD for more information."
            ),
            self
        )
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setObjectName("OverlayFrameLabel")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch(2)
        layout.addWidget(label_widget, 0, QtCore.Qt.AlignCenter)
        layout.addStretch(3)

        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)


class WorkfilesToolWindow(QtWidgets.QWidget):
    """WorkFiles Window.

    Main windows of workfiles tool.

    Args:
        controller (AbstractWorkfilesFrontend): Frontend controller.
        parent (Optional[QtWidgets.QWidget]): Parent widget.
    """

    title = "Work Files"

    def __init__(self, controller=None, parent=None):
        super(WorkfilesToolWindow, self).__init__(parent=parent)

        if controller is None:
            controller = BaseWorkfileController()

        self.setWindowTitle(self.title)
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        flags = self.windowFlags() | QtCore.Qt.Window
        self.setWindowFlags(flags)

        self._default_window_flags = flags

        self._folders_widget = None
        self._folder_filter_input = None

        self._files_widget = None

        self._first_show = True
        self._controller_refreshed = False
        self._context_to_set = None
        # Host validation should happen only once
        self._host_is_valid = None

        self._controller = controller

        # Create pages widget and set it as central widget
        pages_widget = QtWidgets.QStackedWidget(self)

        home_page_widget = QtWidgets.QWidget(pages_widget)
        home_body_widget = QtWidgets.QWidget(home_page_widget)

        col_1_widget = self._create_col_1_widget(controller, parent)
        tasks_widget = TasksWidget(
            controller, home_body_widget, handle_expected_selection=True
        )
        col_3_widget = self._create_col_3_widget(controller, home_body_widget)
        side_panel = SidePanelWidget(controller, home_body_widget)

        pages_widget.addWidget(home_page_widget)

        # Build home
        home_page_layout = QtWidgets.QVBoxLayout(home_page_widget)
        home_page_layout.addWidget(home_body_widget)

        # Build home - body
        body_layout = QtWidgets.QVBoxLayout(home_body_widget)
        split_widget = QtWidgets.QSplitter(home_body_widget)
        split_widget.addWidget(col_1_widget)
        split_widget.addWidget(tasks_widget)
        split_widget.addWidget(col_3_widget)
        split_widget.addWidget(side_panel)
        split_widget.setSizes([255, 160, 455, 175])

        body_layout.addWidget(split_widget)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(pages_widget, 1)

        overlay_messages_widget = MessageOverlayObject(self)
        overlay_invalid_host = InvalidHostOverlay(self)
        overlay_invalid_host.setVisible(False)

        first_show_timer = QtCore.QTimer()
        first_show_timer.setSingleShot(True)
        first_show_timer.setInterval(50)

        first_show_timer.timeout.connect(self._on_first_show)

        controller.register_event_callback(
            "save_as.finished",
            self._on_save_as_finished,
        )
        controller.register_event_callback(
            "copy_representation.finished",
            self._on_copy_representation_finished,
        )
        controller.register_event_callback(
            "workfile_duplicate.finished",
            self._on_duplicate_finished
        )
        controller.register_event_callback(
            "open_workfile.finished",
            self._on_open_finished
        )
        controller.register_event_callback(
            "controller.reset.started",
            self._on_controller_refresh_started,
        )
        controller.register_event_callback(
            "controller.reset.finished",
            self._on_controller_refresh_finished,
        )

        self._overlay_messages_widget = overlay_messages_widget
        self._overlay_invalid_host = overlay_invalid_host
        self._home_page_widget = home_page_widget
        self._pages_widget = pages_widget
        self._home_body_widget = home_body_widget
        self._split_widget = split_widget

        self._tasks_widget = tasks_widget
        self._side_panel = side_panel

        self._first_show_timer = first_show_timer

        self._post_init()

    def _post_init(self):
        self._on_published_checkbox_changed()

        # Force focus on the open button by default, required for Houdini.
        self._files_widget.setFocus()

        self.resize(1200, 600)

    def _create_col_1_widget(self, controller, parent):
        col_widget = QtWidgets.QWidget(parent)
        header_widget = QtWidgets.QWidget(col_widget)

        folder_filter_input = PlaceholderLineEdit(header_widget)
        folder_filter_input.setPlaceholderText("Filter folders..")

        go_to_current_btn = GoToCurrentButton(header_widget)
        refresh_btn = RefreshButton(header_widget)

        folder_widget = FoldersWidget(
            controller, col_widget, handle_expected_selection=True
        )

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(folder_filter_input, 1)
        header_layout.addWidget(go_to_current_btn, 0)
        header_layout.addWidget(refresh_btn, 0)

        col_layout = QtWidgets.QVBoxLayout(col_widget)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.addWidget(header_widget, 0)
        col_layout.addWidget(folder_widget, 1)

        folder_filter_input.textChanged.connect(self._on_folder_filter_change)
        go_to_current_btn.clicked.connect(self._on_go_to_current_clicked)
        refresh_btn.clicked.connect(self._on_refresh_clicked)

        self._folder_filter_input = folder_filter_input
        self._folders_widget = folder_widget

        return col_widget

    def _create_col_3_widget(self, controller, parent):
        col_widget = QtWidgets.QWidget(parent)

        header_widget = QtWidgets.QWidget(col_widget)

        files_filter_input = PlaceholderLineEdit(header_widget)
        files_filter_input.setPlaceholderText("Filter files..")

        published_checkbox = QtWidgets.QCheckBox("Published", header_widget)
        published_checkbox.setToolTip("Show published workfiles")

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(files_filter_input, 1)
        header_layout.addWidget(published_checkbox, 0)

        files_widget = FilesWidget(controller, col_widget)

        col_layout = QtWidgets.QVBoxLayout(col_widget)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.addWidget(header_widget, 0)
        col_layout.addWidget(files_widget, 1)

        files_filter_input.textChanged.connect(
            self._on_file_text_filter_change)
        published_checkbox.stateChanged.connect(
            self._on_published_checkbox_changed
        )

        self._files_filter_input = files_filter_input
        self._published_checkbox = published_checkbox

        self._files_widget = files_widget

        return col_widget

    def set_window_on_top(self, on_top):
        """Set window on top of other windows.

        Args:
            on_top (bool): Show on top of other windows.
        """

        flags = self._default_window_flags
        if on_top:
            flags |= QtCore.Qt.WindowStaysOnTopHint
        if self.windowFlags() != flags:
            self.setWindowFlags(flags)

    def ensure_visible(self, use_context=True, save=True, on_top=False):
        """Ensure the window is visible.

        This method expects arguments for compatibility with previous variant
            of Workfiles tool.

        Args:
            use_context (Optional[bool]): DEPRECATED: This argument is
                ignored.
            save (Optional[bool]): Allow to save workfiles.
            on_top (Optional[bool]): Show on top of other windows.
        """

        save = True if save is None else save
        on_top = False if on_top is None else on_top

        is_visible = self.isVisible()
        self._controller.set_save_enabled(save)
        self.set_window_on_top(on_top)

        self.show()
        self.raise_()
        self.activateWindow()
        if is_visible:
            self.refresh()

    def refresh(self):
        """Trigger refresh of workfiles tool controller."""

        self._controller.reset()

    def showEvent(self, event):
        super(WorkfilesToolWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._first_show_timer.start()
            self.setStyleSheet(style.load_stylesheet())

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidentally perform Maya commands
        whilst trying to name an instance.
        """

        pass

    def _on_first_show(self):
        if not self._controller_refreshed:
            self.refresh()

    def _on_file_text_filter_change(self, text):
        self._files_widget.set_text_filter(text)

    def _on_published_checkbox_changed(self):
        """Publish mode changed.

        Tell children widgets about it so they can handle the mode.
        """

        published_mode = self._published_checkbox.isChecked()
        self._files_widget.set_published_mode(published_mode)
        self._side_panel.set_published_mode(published_mode)

    def _on_folder_filter_change(self, text):
        self._folders_widget.set_name_filter(text)

    def _on_go_to_current_clicked(self):
        self._controller.go_to_current_context()

    def _on_refresh_clicked(self):
        self.refresh()

    def _on_controller_refresh_started(self):
        self._controller_refreshed = True

    def _on_controller_refresh_finished(self):
        if self._host_is_valid is None:
            self._host_is_valid = self._controller.is_host_valid()
            self._overlay_invalid_host.setVisible(not self._host_is_valid)

        if not self._host_is_valid:
            return

        self._folders_widget.set_project_name(
            self._controller.get_current_project_name()
        )

    def _on_save_as_finished(self, event):
        if event["failed"]:
            self._overlay_messages_widget.add_message(
                "Failed to save workfile",
                "error",
            )
        else:
            self._overlay_messages_widget.add_message(
                "Workfile saved"
            )

    def _on_copy_representation_finished(self, event):
        if event["failed"]:
            self._overlay_messages_widget.add_message(
                "Failed to copy published workfile",
                "error",
            )
        else:
            self._overlay_messages_widget.add_message(
                "Publish workfile saved"
            )

    def _on_duplicate_finished(self, event):
        if event["failed"]:
            self._overlay_messages_widget.add_message(
                "Failed to duplicate workfile",
                "error",
            )
        else:
            self._overlay_messages_widget.add_message(
                "Workfile duplicated"
            )

    def _on_open_finished(self, event):
        if event["failed"]:
            self._overlay_messages_widget.add_message(
                "Failed to open workfile",
                "error",
            )
        else:
            self.close()
