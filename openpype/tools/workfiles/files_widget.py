import os
import logging
import shutil

import Qt
from Qt import QtWidgets, QtCore
from avalon import io, api

from openpype.tools.utils import PlaceholderLineEdit
from openpype.tools.utils.delegates import PrettyTimeDelegate
from openpype.lib import (
    emit_event,
    Anatomy,
    get_workfile_template_key,
    create_workdir_extra_folders,
)
from openpype.lib.avalon_context import (
    update_current_task,
    compute_session_changes
)
from .model import (
    WorkAreaFilesModel,
    PublishFilesModel,

    FILEPATH_ROLE,
    DATE_MODIFIED_ROLE,
)
from .save_as_dialog import SaveAsDialog

log = logging.getLogger(__name__)


class FilesView(QtWidgets.QTreeView):
    doubleClickedLeft = QtCore.Signal()
    doubleClickedRight = QtCore.Signal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.doubleClickedLeft.emit()

        elif event.button() == QtCore.Qt.RightButton:
            self.doubleClickedRight.emit()

        return super(FilesView, self).mouseDoubleClickEvent(event)


class FilesWidget(QtWidgets.QWidget):
    """A widget displaying files that allows to save and open files."""
    file_selected = QtCore.Signal(str)
    file_opened = QtCore.Signal()
    workfile_created = QtCore.Signal(str)
    published_visible_changed = QtCore.Signal(bool)

    def __init__(self, parent):
        super(FilesWidget, self).__init__(parent)

        # Setup
        self._asset_id = None
        self._asset_doc = None
        self._task_name = None
        self._task_type = None

        # Pype's anatomy object for current project
        self.anatomy = Anatomy(io.Session["AVALON_PROJECT"])
        # Template key used to get work template from anatomy templates
        self.template_key = "work"

        # This is not root but workfile directory
        self._workfiles_root = None
        self._workdir_path = None
        self.host = api.registered_host()

        # Whether to automatically select the latest modified
        # file on a refresh of the files model.
        self.auto_select_latest_modified = True

        # Avoid crash in Blender and store the message box
        # (setting parent doesn't work as it hides the message box)
        self._messagebox = None

        # Filtering input
        filter_widget = QtWidgets.QWidget(self)

        published_checkbox = QtWidgets.QCheckBox("Published", filter_widget)

        filter_input = PlaceholderLineEdit(filter_widget)
        filter_input.setPlaceholderText("Filter files..")

        filter_layout = QtWidgets.QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(published_checkbox, 0)
        filter_layout.addWidget(filter_input, 1)

        # Create the Files models
        extensions = set(self.host.file_extensions())

        views_widget = QtWidgets.QWidget(self)
        # Workarea view
        workarea_files_model = WorkAreaFilesModel(extensions)

        # Create proxy model for files to be able sort and filter
        workarea_proxy_model = QtCore.QSortFilterProxyModel()
        workarea_proxy_model.setSourceModel(workarea_files_model)
        workarea_proxy_model.setDynamicSortFilter(True)
        workarea_proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        # Set up the file list tree view
        workarea_files_view = FilesView(views_widget)
        workarea_files_view.setModel(workarea_proxy_model)
        workarea_files_view.setSortingEnabled(True)
        workarea_files_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # Date modified delegate
        workarea_time_delegate = PrettyTimeDelegate()
        workarea_files_view.setItemDelegateForColumn(1, workarea_time_delegate)
        workarea_files_view.setIndentation(3)   # smaller indentation

        # Default to a wider first filename column it is what we mostly care
        # about and the date modified is relatively small anyway.
        workarea_files_view.setColumnWidth(0, 330)

        # Publish files view
        publish_files_model = PublishFilesModel(extensions, io, self.anatomy)

        publish_proxy_model = QtCore.QSortFilterProxyModel()
        publish_proxy_model.setSourceModel(publish_files_model)
        publish_proxy_model.setDynamicSortFilter(True)
        publish_proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        publish_files_view = FilesView(views_widget)
        publish_files_view.setModel(publish_proxy_model)

        publish_files_view.setSortingEnabled(True)
        publish_files_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # Date modified delegate
        publish_time_delegate = PrettyTimeDelegate()
        publish_files_view.setItemDelegateForColumn(1, publish_time_delegate)
        publish_files_view.setIndentation(3)   # smaller indentation

        # Default to a wider first filename column it is what we mostly care
        # about and the date modified is relatively small anyway.
        publish_files_view.setColumnWidth(0, 330)

        views_layout = QtWidgets.QHBoxLayout(views_widget)
        views_layout.setContentsMargins(0, 0, 0, 0)
        views_layout.addWidget(workarea_files_view, 1)
        views_layout.addWidget(publish_files_view, 1)

        # Home Page
        # Build buttons widget for files widget
        btns_widget = QtWidgets.QWidget(self)
        btn_save = QtWidgets.QPushButton("Save As", btns_widget)
        btn_browse = QtWidgets.QPushButton("Browse", btns_widget)
        btn_open = QtWidgets.QPushButton("Open", btns_widget)

        btn_view_published = QtWidgets.QPushButton("View", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addWidget(btn_open, 1)
        btns_layout.addWidget(btn_browse, 1)
        btns_layout.addWidget(btn_save, 1)
        btns_layout.addWidget(btn_view_published, 1)

        # Build files widgets for home page
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(filter_widget, 0)
        main_layout.addWidget(views_widget, 1)
        main_layout.addWidget(btns_widget, 0)

        # Register signal callbacks
        published_checkbox.stateChanged.connect(self._on_published_change)
        filter_input.textChanged.connect(self._on_filter_text_change)

        workarea_files_view.doubleClickedLeft.connect(
            self._on_workarea_open_pressed
        )
        workarea_files_view.customContextMenuRequested.connect(
            self._on_workarea_context_menu
        )
        workarea_files_view.selectionModel().selectionChanged.connect(
            self.on_file_select
        )

        btn_open.pressed.connect(self._on_workarea_open_pressed)
        btn_browse.pressed.connect(self.on_browse_pressed)
        btn_save.pressed.connect(self.on_save_as_pressed)
        btn_view_published.pressed.connect(self._on_view_published_pressed)

        # Store attributes
        self._published_checkbox = published_checkbox
        self._filter_input = filter_input

        self._workarea_time_delegate = workarea_time_delegate
        self._workarea_files_view = workarea_files_view
        self._workarea_files_model = workarea_files_model
        self._workarea_proxy_model = workarea_proxy_model

        self._publish_time_delegate = publish_time_delegate
        self._publish_files_view = publish_files_view
        self._publish_files_model = publish_files_model
        self._publish_proxy_model = publish_proxy_model

        self._btns_widget = btns_widget
        self._btn_open = btn_open
        self._btn_browse = btn_browse
        self._btn_save = btn_save
        self._btn_view_published = btn_view_published

        # Create a proxy widget for files widget
        self.setFocusProxy(btn_open)

        # Hide publish files widgets
        publish_files_view.setVisible(False)
        btn_view_published.setVisible(False)

    @property
    def published_enabled(self):
        return self._published_checkbox.isChecked()

    def _on_published_change(self):
        published_enabled = self.published_enabled

        self._workarea_files_view.setVisible(not published_enabled)
        self._btn_open.setVisible(not published_enabled)
        self._btn_browse.setVisible(not published_enabled)
        self._btn_save.setVisible(not published_enabled)

        self._publish_files_view.setVisible(published_enabled)
        self._btn_view_published.setVisible(published_enabled)

        self._update_filtering()
        self._update_asset_task()

        self.published_visible_changed.emit(published_enabled)

    def _on_filter_text_change(self):
        self._update_filtering()

    def _update_filtering(self):
        text = self._filter_input.text()
        if self.published_enabled:
            self._publish_proxy_model.setFilterFixedString(text)
        else:
            self._workarea_proxy_model.setFilterFixedString(text)

    def set_save_enabled(self, enabled):
        self._btn_save.setEnabled(enabled)

    def set_asset_task(self, asset_id, task_name, task_type):
        if asset_id != self._asset_id:
            self._asset_doc = None
        self._asset_id = asset_id
        self._task_name = task_name
        self._task_type = task_type
        self._update_asset_task()

    def _update_asset_task(self):
        if self.published_enabled:
            self._publish_files_model.set_context(
                self._asset_id, self._task_name
            )
            has_valid_items = self._publish_files_model.has_valid_items()
            self._btn_view_published.setEnabled(has_valid_items)
        else:
            # Define a custom session so we can query the work root
            # for a "Work area" that is not our current Session.
            # This way we can browse it even before we enter it.
            if self._asset_id and self._task_name and self._task_type:
                session = self._get_session()
                self._workdir_path = session["AVALON_WORKDIR"]
                self._workfiles_root = self.host.work_root(session)
                self._workarea_files_model.set_root(self._workfiles_root)

            else:
                self._workarea_files_model.set_root(None)

            # Disable/Enable buttons based on available files in model
            has_valid_items = self._workarea_files_model.has_valid_items()
            self._btn_browse.setEnabled(has_valid_items)
            self._btn_open.setEnabled(has_valid_items)
        # Manually trigger file selection
        if not has_valid_items:
            self.on_file_select()

    def _get_asset_doc(self):
        if self._asset_id is None:
            return None

        if self._asset_doc is None:
            self._asset_doc = io.find_one({"_id": self._asset_id})
        return self._asset_doc

    def _get_session(self):
        """Return a modified session for the current asset and task"""

        session = api.Session.copy()
        self.template_key = get_workfile_template_key(
            self._task_type,
            session["AVALON_APP"],
            project_name=session["AVALON_PROJECT"]
        )
        changes = compute_session_changes(
            session,
            asset=self._get_asset_doc(),
            task=self._task_name,
            template_key=self.template_key
        )
        session.update(changes)

        return session

    def _enter_session(self):
        """Enter the asset and task session currently selected"""

        session = api.Session.copy()
        changes = compute_session_changes(
            session,
            asset=self._get_asset_doc(),
            task=self._task_name,
            template_key=self.template_key
        )
        if not changes:
            # Return early if we're already in the right Session context
            # to avoid any unwanted Task Changed callbacks to be triggered.
            return

        update_current_task(
            asset=self._get_asset_doc(),
            task=self._task_name,
            template_key=self.template_key
        )

    def open_file(self, filepath):
        host = self.host
        if host.has_unsaved_changes():
            result = self.save_changes_prompt()
            if result is None:
                # Cancel operation
                return False

            # Save first if has changes
            if result:
                current_file = host.current_file()
                if not current_file:
                    # If the user requested to save the current scene
                    # we can't actually automatically do so if the current
                    # file has not been saved with a name yet. So we'll have
                    # to opt out.
                    log.error("Can't save scene with no filename. Please "
                              "first save your work file using 'Save As'.")
                    return

                # Save current scene, continue to open file
                host.save_file(current_file)

        self._enter_session()
        host.open_file(filepath)
        self.file_opened.emit()

    def save_changes_prompt(self):
        self._messagebox = messagebox = QtWidgets.QMessageBox(parent=self)
        messagebox.setWindowFlags(messagebox.windowFlags() |
                                  QtCore.Qt.FramelessWindowHint)
        messagebox.setIcon(messagebox.Warning)
        messagebox.setWindowTitle("Unsaved Changes!")
        messagebox.setText(
            "There are unsaved changes to the current file."
            "\nDo you want to save the changes?"
        )
        messagebox.setStandardButtons(
            messagebox.Yes | messagebox.No | messagebox.Cancel
        )

        result = messagebox.exec_()
        if result == messagebox.Yes:
            return True
        if result == messagebox.No:
            return False
        return None

    def get_filename(self):
        """Show save dialog to define filename for save or duplicate

        Returns:
            str: The filename to create.

        """
        session = self._get_session()

        window = SaveAsDialog(
            parent=self,
            root=self._workfiles_root,
            anatomy=self.anatomy,
            template_key=self.template_key,
            session=session
        )
        window.exec_()

        return window.get_result()

    def on_duplicate_pressed(self):
        work_file = self.get_filename()
        if not work_file:
            return

        src = self._get_selected_filepath()
        dst = os.path.join(self._workfiles_root, work_file)
        shutil.copy(src, dst)

        self.workfile_created.emit(dst)

        self.refresh()

    def _get_selected_filepath(self):
        """Return current filepath selected in view"""
        if self.published_enabled:
            source_view = self._publish_files_view
        else:
            source_view = self._workarea_files_view
        selection = source_view.selectionModel()
        index = selection.currentIndex()
        if not index.isValid():
            return

        return index.data(FILEPATH_ROLE)

    def _on_workarea_open_pressed(self):
        path = self._get_selected_filepath()
        if not path:
            print("No file selected to open..")
            return

        self.open_file(path)

    def on_browse_pressed(self):
        ext_filter = "Work File (*{0})".format(
            " *".join(self.host.file_extensions())
        )
        kwargs = {
            "caption": "Work Files",
            "filter": ext_filter
        }
        if Qt.__binding__ in ("PySide", "PySide2"):
            kwargs["dir"] = self._workfiles_root
        else:
            kwargs["directory"] = self._workfiles_root

        work_file = QtWidgets.QFileDialog.getOpenFileName(**kwargs)[0]
        if work_file:
            self.open_file(work_file)

    def on_save_as_pressed(self):
        work_filename = self.get_filename()
        if not work_filename:
            return

        # Trigger before save event
        emit_event(
            "workfile.save.before",
            {"filename": work_filename, "workdir_path": self._workdir_path},
            source="workfiles.tool"
        )

        # Make sure workfiles root is updated
        # - this triggers 'workio.work_root(...)' which may change value of
        #   '_workfiles_root'
        self.set_asset_task(
            self._asset_id, self._task_name, self._task_type
        )

        # Create workfiles root folder
        if not os.path.exists(self._workfiles_root):
            log.debug("Initializing Work Directory: %s", self._workfiles_root)
            os.makedirs(self._workfiles_root)

        # Update session if context has changed
        self._enter_session()
        # Prepare full path to workfile and save it
        filepath = os.path.join(
            os.path.normpath(self._workfiles_root), work_filename
        )
        self.host.save_file(filepath)
        # Create extra folders
        create_workdir_extra_folders(
            self._workdir_path,
            api.Session["AVALON_APP"],
            self._task_type,
            self._task_name,
            api.Session["AVALON_PROJECT"]
        )
        # Trigger after save events
        emit_event(
            "workfile.save.after",
            {"filename": work_filename, "workdir_path": self._workdir_path},
            source="workfiles.tool"
        )

        self.workfile_created.emit(filepath)
        # Refresh files model
        self.refresh()

    def _on_view_published_pressed(self):
        print("View of published workfile triggered")

    def on_file_select(self):
        self.file_selected.emit(self._get_selected_filepath())

    def refresh(self):
        """Refresh listed files for current selection in the interface"""
        if self.published_enabled:
            self._publish_files_model.refresh()
        else:
            self._workarea_files_model.refresh()


        if self.auto_select_latest_modified:
            self._select_last_modified_file()

    def _on_workarea_context_menu(self, point):
        index = self._workarea_files_view.indexAt(point)
        if not index.isValid():
            return

        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return

        menu = QtWidgets.QMenu(self)

        # Duplicate
        action = QtWidgets.QAction("Duplicate", menu)
        tip = "Duplicate selected file."
        action.setToolTip(tip)
        action.setStatusTip(tip)
        action.triggered.connect(self.on_duplicate_pressed)
        menu.addAction(action)

        # Show the context action menu
        global_point = self._workarea_files_view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action:
            return

    def _select_last_modified_file(self):
        """Utility function to select the file with latest date modified"""
        if self.published_enabled:
            source_view = self._publish_files_view
        else:
            source_view = self._workarea_files_view
        model = source_view.model()

        highest_index = None
        highest = 0
        for row in range(model.rowCount()):
            index = model.index(row, 0, parent=QtCore.QModelIndex())
            if not index.isValid():
                continue

            modified = index.data(DATE_MODIFIED_ROLE)
            if modified is not None and modified > highest:
                highest_index = index
                highest = modified

        if highest_index:
            source_view.setCurrentIndex(highest_index)
