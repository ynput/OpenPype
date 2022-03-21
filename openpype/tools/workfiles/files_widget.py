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
    workfile_created = QtCore.Signal(str)
    file_opened = QtCore.Signal()

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(parent=parent)

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

        files_view = FilesView(self)

        # Create the Files model
        extensions = set(self.host.file_extensions())
        files_model = WorkAreaFilesModel(extensions)

        # Create proxy model for files to be able sort and filter
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(files_model)
        proxy_model.setDynamicSortFilter(True)
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        # Set up the file list tree view
        files_view.setModel(proxy_model)
        files_view.setSortingEnabled(True)
        files_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # Date modified delegate
        time_delegate = PrettyTimeDelegate()
        files_view.setItemDelegateForColumn(1, time_delegate)
        files_view.setIndentation(3)   # smaller indentation

        # Default to a wider first filename column it is what we mostly care
        # about and the date modified is relatively small anyway.
        files_view.setColumnWidth(0, 330)

        # Filtering input
        filter_input = PlaceholderLineEdit(self)
        filter_input.setPlaceholderText("Filter files..")
        filter_input.textChanged.connect(proxy_model.setFilterFixedString)

        # Home Page
        # Build buttons widget for files widget
        btns_widget = QtWidgets.QWidget(self)
        btn_save = QtWidgets.QPushButton("Save As", btns_widget)
        btn_browse = QtWidgets.QPushButton("Browse", btns_widget)
        btn_open = QtWidgets.QPushButton("Open", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addWidget(btn_open)
        btns_layout.addWidget(btn_browse)
        btns_layout.addWidget(btn_save)

        # Build files widgets for home page
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(filter_input)
        main_layout.addWidget(files_view)
        main_layout.addWidget(btns_widget)

        # Register signal callbacks
        files_view.doubleClickedLeft.connect(self.on_open_pressed)
        files_view.customContextMenuRequested.connect(self.on_context_menu)
        files_view.selectionModel().selectionChanged.connect(
            self.on_file_select
        )

        btn_open.pressed.connect(self.on_open_pressed)
        btn_browse.pressed.connect(self.on_browse_pressed)
        btn_save.pressed.connect(self.on_save_as_pressed)

        # Store attributes
        self.time_delegate = time_delegate

        self.filter_input = filter_input

        self.files_view = files_view
        self.files_model = files_model

        self.btns_widget = btns_widget
        self.btn_open = btn_open
        self.btn_browse = btn_browse
        self.btn_save = btn_save

    def set_asset_task(self, asset_id, task_name, task_type):
        if asset_id != self._asset_id:
            self._asset_doc = None
        self._asset_id = asset_id
        self._task_name = task_name
        self._task_type = task_type

        # Define a custom session so we can query the work root
        # for a "Work area" that is not our current Session.
        # This way we can browse it even before we enter it.
        if self._asset_id and self._task_name and self._task_type:
            session = self._get_session()
            self._workdir_path = session["AVALON_WORKDIR"]
            self._workfiles_root = self.host.work_root(session)
            self.files_model.set_root(self._workfiles_root)

        else:
            self.files_model.set_root(None)

        # Disable/Enable buttons based on available files in model
        has_valid_items = self.files_model.has_valid_items()
        self.btn_browse.setEnabled(has_valid_items)
        self.btn_open.setEnabled(has_valid_items)
        if not has_valid_items:
            # Manually trigger file selection
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
        selection = self.files_view.selectionModel()
        index = selection.currentIndex()
        if not index.isValid():
            return

        return index.data(FILEPATH_ROLE)

    def on_open_pressed(self):
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

    def on_file_select(self):
        self.file_selected.emit(self._get_selected_filepath())

    def refresh(self):
        """Refresh listed files for current selection in the interface"""
        self.files_model.refresh()

        if self.auto_select_latest_modified:
            self._select_last_modified_file()

    def on_context_menu(self, point):
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
        global_point = self.files_view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action:
            return

    def _select_last_modified_file(self):
        """Utility function to select the file with latest date modified"""
        model = self.files_view.model()

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
            self.files_view.setCurrentIndex(highest_index)
