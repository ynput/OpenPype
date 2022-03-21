import sys
import os
import shutil
import logging
import datetime

import Qt
from Qt import QtWidgets, QtCore
from avalon import io, api

from openpype import style
from openpype.tools.utils.lib import (
    qt_app_context
)
from openpype.tools.utils import PlaceholderLineEdit
from openpype.tools.utils.assets_widget import SingleSelectAssetsWidget
from openpype.tools.utils.tasks_widget import TasksWidget
from openpype.tools.utils.delegates import PrettyTimeDelegate
from openpype.lib import (
    emit_event,
    Anatomy,
    get_workfile_doc,
    create_workfile_doc,
    save_workfile_data_to_doc,
    get_workfile_template_key,
    create_workdir_extra_folders,
)
from openpype.lib.avalon_context import (
    update_current_task,
    compute_session_changes
)
from .model import FilesModel
from .save_as_dialog import SaveAsDialog
from .view import FilesView

log = logging.getLogger(__name__)

module = sys.modules[__name__]
module.window = None


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
        files_model = FilesModel(file_extensions=extensions)

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
        has_filenames = self.files_model.has_filenames()
        self.btn_browse.setEnabled(has_filenames)
        self.btn_open.setEnabled(has_filenames)
        if not has_filenames:
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

        return index.data(self.files_model.FilePathRole)

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
        index = self.files_view.indexAt(point)
        if not index.isValid():
            return

        is_enabled = index.data(FilesModel.IsEnabled)
        if not is_enabled:
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
        role = self.files_model.DateModifiedRole
        model = self.files_view.model()

        highest_index = None
        highest = 0
        for row in range(model.rowCount()):
            index = model.index(row, 0, parent=QtCore.QModelIndex())
            if not index.isValid():
                continue

            modified = index.data(role)
            if modified is not None and modified > highest:
                highest_index = index
                highest = modified

        if highest_index:
            self.files_view.setCurrentIndex(highest_index)


class SidePanelWidget(QtWidgets.QWidget):
    save_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(SidePanelWidget, self).__init__(parent)

        details_label = QtWidgets.QLabel("Details", self)
        details_input = QtWidgets.QPlainTextEdit(self)
        details_input.setReadOnly(True)

        note_label = QtWidgets.QLabel("Artist note", self)
        note_input = QtWidgets.QPlainTextEdit(self)
        btn_note_save = QtWidgets.QPushButton("Save note", self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(details_label, 0)
        main_layout.addWidget(details_input, 0)
        main_layout.addWidget(note_label, 0)
        main_layout.addWidget(note_input, 1)
        main_layout.addWidget(btn_note_save, alignment=QtCore.Qt.AlignRight)

        note_input.textChanged.connect(self.on_note_change)
        btn_note_save.clicked.connect(self.on_save_click)

        self.details_input = details_input
        self.note_input = note_input
        self.btn_note_save = btn_note_save

        self._orig_note = ""
        self._workfile_doc = None

    def on_note_change(self):
        text = self.note_input.toPlainText()
        self.btn_note_save.setEnabled(self._orig_note != text)

    def on_save_click(self):
        self._orig_note = self.note_input.toPlainText()
        self.on_note_change()
        self.save_clicked.emit()

    def set_context(self, asset_id, task_name, filepath, workfile_doc):
        # Check if asset, task and file are selected
        # NOTE workfile document is not requirement
        enabled = bool(asset_id) and bool(task_name) and bool(filepath)

        self.details_input.setEnabled(enabled)
        self.note_input.setEnabled(enabled)
        self.btn_note_save.setEnabled(enabled)

        # Make sure workfile doc is overridden
        self._workfile_doc = workfile_doc
        # Disable inputs and remove texts if any required arguments are missing
        if not enabled:
            self._orig_note = ""
            self.details_input.setPlainText("")
            self.note_input.setPlainText("")
            return

        orig_note = ""
        if workfile_doc:
            orig_note = workfile_doc["data"].get("note") or orig_note

        self._orig_note = orig_note
        self.note_input.setPlainText(orig_note)
        # Set as empty string
        self.details_input.setPlainText("")

        filestat = os.stat(filepath)
        size_ending_mapping = {
            "KB": 1024 ** 1,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3
        }
        size = filestat.st_size
        ending = "B"
        for _ending, _size in size_ending_mapping.items():
            if filestat.st_size < _size:
                break
            size = filestat.st_size / _size
            ending = _ending

        # Append html string
        datetime_format = "%b %d %Y %H:%M:%S"
        creation_time = datetime.datetime.fromtimestamp(filestat.st_ctime)
        modification_time = datetime.datetime.fromtimestamp(filestat.st_mtime)
        lines = (
            "<b>Size:</b>",
            "{:.2f} {}".format(size, ending),
            "<b>Created:</b>",
            creation_time.strftime(datetime_format),
            "<b>Modified:</b>",
            modification_time.strftime(datetime_format)
        )
        self.details_input.appendHtml("<br>".join(lines))

    def get_workfile_data(self):
        data = {
            "note": self.note_input.toPlainText()
        }
        return self._workfile_doc, data


class Window(QtWidgets.QMainWindow):
    """Work Files Window"""
    title = "Work Files"

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)
        self.setWindowTitle(self.title)
        window_flags = QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint
        if not parent:
            window_flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)

        # Create pages widget and set it as central widget
        pages_widget = QtWidgets.QStackedWidget(self)
        self.setCentralWidget(pages_widget)

        home_page_widget = QtWidgets.QWidget(pages_widget)
        home_body_widget = QtWidgets.QWidget(home_page_widget)

        assets_widget = SingleSelectAssetsWidget(io, parent=home_body_widget)
        assets_widget.set_current_asset_btn_visibility(True)

        tasks_widget = TasksWidget(io, home_body_widget)
        files_widget = FilesWidget(home_body_widget)
        side_panel = SidePanelWidget(home_body_widget)

        pages_widget.addWidget(home_page_widget)

        # Build home
        home_page_layout = QtWidgets.QVBoxLayout(home_page_widget)
        home_page_layout.addWidget(home_body_widget)

        # Build home - body
        body_layout = QtWidgets.QVBoxLayout(home_body_widget)
        split_widget = QtWidgets.QSplitter(home_body_widget)
        split_widget.addWidget(assets_widget)
        split_widget.addWidget(tasks_widget)
        split_widget.addWidget(files_widget)
        split_widget.addWidget(side_panel)
        split_widget.setSizes([255, 160, 455, 175])

        body_layout.addWidget(split_widget)

        # Add top margin for tasks to align it visually with files as
        # the files widget has a filter field which tasks does not.
        tasks_widget.setContentsMargins(0, 32, 0, 0)

        # Set context after asset widget is refreshed
        # - to do so it is necessary to wait until refresh is done
        set_context_timer = QtCore.QTimer()
        set_context_timer.setInterval(100)

        # Connect signals
        set_context_timer.timeout.connect(self._on_context_set_timeout)
        assets_widget.selection_changed.connect(self._on_asset_changed)
        tasks_widget.task_changed.connect(self._on_task_changed)
        files_widget.file_selected.connect(self.on_file_select)
        files_widget.workfile_created.connect(self.on_workfile_create)
        files_widget.file_opened.connect(self._on_file_opened)
        side_panel.save_clicked.connect(self.on_side_panel_save)

        self._set_context_timer = set_context_timer
        self.home_page_widget = home_page_widget
        self.pages_widget = pages_widget
        self.home_body_widget = home_body_widget
        self.split_widget = split_widget

        self.assets_widget = assets_widget
        self.tasks_widget = tasks_widget
        self.files_widget = files_widget
        self.side_panel = side_panel

        # Force focus on the open button by default, required for Houdini.
        files_widget.btn_open.setFocus()

        self.resize(1200, 600)

        self._first_show = True
        self._context_to_set = None

    def showEvent(self, event):
        super(Window, self).showEvent(event)
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

    def set_save_enabled(self, enabled):
        self.files_widget.btn_save.setEnabled(enabled)

    def on_file_select(self, filepath):
        asset_id = self.assets_widget.get_selected_asset_id()
        task_name = self.tasks_widget.get_selected_task_name()

        workfile_doc = None
        if asset_id and task_name and filepath:
            filename = os.path.split(filepath)[1]
            workfile_doc = get_workfile_doc(
                asset_id, task_name, filename, io
            )
        self.side_panel.set_context(
            asset_id, task_name, filepath, workfile_doc
        )

    def on_workfile_create(self, filepath):
        self._create_workfile_doc(filepath)

    def _on_file_opened(self):
        self.close()

    def on_side_panel_save(self):
        workfile_doc, data = self.side_panel.get_workfile_data()
        if not workfile_doc:
            filepath = self.files_widget._get_selected_filepath()
            self._create_workfile_doc(filepath, force=True)
            workfile_doc = self._get_current_workfile_doc()

        save_workfile_data_to_doc(workfile_doc, data, io)

    def _get_current_workfile_doc(self, filepath=None):
        if filepath is None:
            filepath = self.files_widget._get_selected_filepath()
        task_name = self.tasks_widget.get_selected_task_name()
        asset_id = self.assets_widget.get_selected_asset_id()
        if not task_name or not asset_id or not filepath:
            return

        filename = os.path.split(filepath)[1]
        return get_workfile_doc(
            asset_id, task_name, filename, io
        )

    def _create_workfile_doc(self, filepath, force=False):
        workfile_doc = None
        if not force:
            workfile_doc = self._get_current_workfile_doc(filepath)

        if not workfile_doc:
            workdir, filename = os.path.split(filepath)
            asset_id = self.assets_widget.get_selected_asset_id()
            asset_doc = io.find_one({"_id": asset_id})
            task_name = self.tasks_widget.get_selected_task_name()
            create_workfile_doc(asset_doc, task_name, filename, workdir, io)

    def refresh(self):
        # Refresh asset widget
        self.assets_widget.refresh()

        self._on_task_changed()

    def set_context(self, context):
        self._context_to_set = context
        self._set_context_timer.start()

    def _on_context_set_timeout(self):
        if self._context_to_set is None:
            self._set_context_timer.stop()
            return

        if self.assets_widget.refreshing:
            return

        self._context_to_set, context = None, self._context_to_set
        if "asset" in context:
            asset_doc = io.find_one(
                {
                    "name": context["asset"],
                    "type": "asset"
                },
                {"_id": 1}
            ) or {}
            asset_id = asset_doc.get("_id")
            # Select the asset
            self.assets_widget.select_asset(asset_id)
            self.tasks_widget.set_asset_id(asset_id)

        if "task" in context:
            self.tasks_widget.select_task_name(context["task"])
        self._on_task_changed()

    def _on_asset_changed(self):
        asset_id = self.assets_widget.get_selected_asset_id()
        if asset_id:
            self.tasks_widget.setEnabled(True)
        else:
            # Force disable the other widgets if no
            # active selection
            self.tasks_widget.setEnabled(False)
            self.files_widget.setEnabled(False)

        self.tasks_widget.set_asset_id(asset_id)

    def _on_task_changed(self):
        asset_id = self.assets_widget.get_selected_asset_id()
        task_name = self.tasks_widget.get_selected_task_name()
        task_type = self.tasks_widget.get_selected_task_type()

        asset_is_valid = asset_id is not None
        self.tasks_widget.setEnabled(asset_is_valid)

        self.files_widget.setEnabled(bool(task_name) and asset_is_valid)
        self.files_widget.set_asset_task(asset_id, task_name, task_type)
        self.files_widget.refresh()


def validate_host_requirements(host):
    if host is None:
        raise RuntimeError("No registered host.")

    # Verify the host has implemented the api for Work Files
    required = [
        "open_file",
        "save_file",
        "current_file",
        "has_unsaved_changes",
        "work_root",
        "file_extensions",
    ]
    missing = []
    for name in required:
        if not hasattr(host, name):
            missing.append(name)
    if missing:
        raise RuntimeError(
            "Host is missing required Work Files interfaces: "
            "%s (host: %s)" % (", ".join(missing), host)
        )
    return True


def show(root=None, debug=False, parent=None, use_context=True, save=True):
    """Show Work Files GUI"""
    # todo: remove `root` argument to show()

    try:
        module.window.close()
        del(module.window)
    except (AttributeError, RuntimeError):
        pass

    host = api.registered_host()
    validate_host_requirements(host)

    if debug:
        api.Session["AVALON_ASSET"] = "Mock"
        api.Session["AVALON_TASK"] = "Testing"

    with qt_app_context():
        window = Window(parent=parent)
        window.refresh()

        if use_context:
            context = {
                "asset": api.Session["AVALON_ASSET"],
                "silo": api.Session["AVALON_SILO"],
                "task": api.Session["AVALON_TASK"]
            }
            window.set_context(context)

        window.set_save_enabled(save)

        window.show()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
