from Qt import QtWidgets, QtCore, QtGui
from Qt.QtCore import Qt
import attr
import os

import sys
import subprocess

from openpype.tools.settings import (
    ProjectListWidget,
    style
)

from avalon.tools.delegates import PrettyTimeDelegate, pretty_timestamp
from bson.objectid import ObjectId

from openpype.lib import PypeLogger
from openpype.api import get_local_site_id
from openpype import resources

log = PypeLogger().get_logger("SyncServer")

STATUS = {
    0: 'In Progress',
    1: 'Queued',
    2: 'Failed',
    3: 'Paused',
    4: 'Synced OK',
    -1: 'Not available'
}

DUMMY_PROJECT = "No project configured"


class SyncServerWindow(QtWidgets.QDialog):
    """
        Main window that contains list of synchronizable projects and summary
        view with all synchronizable representations for first project
    """

    def __init__(self, sync_server, parent=None):
        super(SyncServerWindow, self).__init__(parent)
        self.sync_server = sync_server
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(resources.pype_icon_filepath()))
        self.resize(1400, 800)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._hide_message)

        body = QtWidgets.QWidget(self)
        footer = QtWidgets.QWidget(self)
        footer.setFixedHeight(20)

        left_column = QtWidgets.QWidget(body)
        left_column_layout = QtWidgets.QVBoxLayout(left_column)

        self.projects = SyncProjectListWidget(sync_server, self)
        self.projects.refresh()  # force selection of default
        left_column_layout.addWidget(self.projects)
        self.pause_btn = QtWidgets.QPushButton("Pause server")

        left_column_layout.addWidget(self.pause_btn)
        left_column.setLayout(left_column_layout)

        repres = SyncRepresentationWidget(
            sync_server,
            project=self.projects.current_project,
            parent=self)
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        split = QtWidgets.QSplitter()
        split.addWidget(left_column)
        split.addWidget(repres)
        split.setSizes([180, 950, 200])
        container_layout.addWidget(split)

        container.setLayout(container_layout)

        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.addWidget(container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self.message = QtWidgets.QLabel(footer)
        self.message.hide()

        footer_layout = QtWidgets.QVBoxLayout(footer)
        footer_layout.addWidget(self.message)
        footer_layout.setContentsMargins(20, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(footer)

        self.setLayout(body_layout)
        self.setWindowTitle("Sync Server")

        self.projects.project_changed.connect(
            lambda: repres.table_view.model().set_project(
                self.projects.current_project))

        self.pause_btn.clicked.connect(self._pause)
        repres.message_generated.connect(self._update_message)

    def _pause(self):
        if self.sync_server.is_paused():
            self.sync_server.unpause_server()
            self.pause_btn.setText("Pause server")
        else:
            self.sync_server.pause_server()
            self.pause_btn.setText("Unpause server")
        self.projects.refresh()

    def _update_message(self, value):
        """
            Update and show message in the footer
        """
        self.message.setText(value)
        if self.message.isVisible():
            self.message.repaint()
        else:
            self.message.show()
        msec_delay = 3000
        self.timer.start(msec_delay)

    def _hide_message(self):
        """
            Hide message in footer

            Called automatically by self.timer after a while
        """
        self.message.setText("")
        self.message.hide()


class SyncProjectListWidget(ProjectListWidget):
    """
        Lists all projects that are synchronized to choose from
    """

    def __init__(self, sync_server, parent):
        super(SyncProjectListWidget, self).__init__(parent)
        self.sync_server = sync_server
        self.project_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(
            self._on_context_menu)
        self.project_name = None
        self.local_site = None
        self.icons = {}

    def validate_context_change(self):
        return True

    def refresh(self):
        model = self.project_list.model()
        model.clear()

        project_name = None
        for project_name in self.sync_server.sync_project_settings.\
                keys():
            if self.sync_server.is_paused() or \
               self.sync_server.is_project_paused(project_name):
                icon = self._get_icon("paused")
            else:
                icon = self._get_icon("synced")

            model.appendRow(QtGui.QStandardItem(icon, project_name))

        if len(self.sync_server.sync_project_settings.keys()) == 0:
            model.appendRow(QtGui.QStandardItem(DUMMY_PROJECT))

        self.current_project = self.project_list.currentIndex().data(
            QtCore.Qt.DisplayRole
        )
        if not self.current_project:
            self.current_project = self.project_list.model().item(0). \
                data(QtCore.Qt.DisplayRole)

        if project_name:
            self.local_site = self.sync_server.get_active_site(project_name)

    def _get_icon(self, status):
        if not self.icons.get(status):
            resource_path = os.path.dirname(__file__)
            resource_path = os.path.join(resource_path, "..",
                                         "resources")
            pix_url = "{}/{}.png".format(resource_path, status)
            icon = QtGui.QIcon(pix_url)
            self.icons[status] = icon
        else:
            icon = self.icons[status]
        return icon

    def _on_context_menu(self, point):
        point_index = self.project_list.indexAt(point)
        if not point_index.isValid():
            return

        self.project_name = point_index.data(QtCore.Qt.DisplayRole)

        menu = QtWidgets.QMenu()
        actions_mapping = {}

        if self.sync_server.is_project_paused(self.project_name):
            action = QtWidgets.QAction("Unpause")
            actions_mapping[action] = self._unpause
        else:
            action = QtWidgets.QAction("Pause")
            actions_mapping[action] = self._pause
        menu.addAction(action)

        if self.local_site == get_local_site_id():
            action = QtWidgets.QAction("Clear local project")
            actions_mapping[action] = self._clear_project
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def _pause(self):
        if self.project_name:
            self.sync_server.pause_project(self.project_name)
            self.project_name = None
        self.refresh()

    def _unpause(self):
        if self.project_name:
            self.sync_server.unpause_project(self.project_name)
            self.project_name = None
        self.refresh()

    def _clear_project(self):
        if self.project_name:
            self.sync_server.clear_project(self.project_name, self.local_site)
            self.project_name = None
        self.refresh()


class ProjectModel(QtCore.QAbstractListModel):
    def __init__(self, *args, projects=None, **kwargs):
        super(ProjectModel, self).__init__(*args, **kwargs)
        self.projects = projects or []

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the data structure.
            status, text = self.projects[index.row()]
            # Return the todo text only.
            return text

    def rowCount(self, index):
        return len(self.todos)


class SyncRepresentationWidget(QtWidgets.QWidget):
    """
        Summary dialog with list of representations that matches current
        settings 'local_site' and 'remote_site'.
    """
    active_changed = QtCore.Signal()  # active index changed
    message_generated = QtCore.Signal(str)

    default_widths = (
        ("asset", 210),
        ("subset", 190),
        ("version", 10),
        ("representation", 90),
        ("created_dt", 105),
        ("sync_dt", 105),
        ("local_site", 80),
        ("remote_site", 80),
        ("files_count", 50),
        ("files_size", 60),
        ("priority", 20),
        ("state", 50)
    )
    column_labels = (
        ("asset", "Asset"),
        ("subset", "Subset"),
        ("version", "Version"),
        ("representation", "Representation"),
        ("created_dt", "Created"),
        ("sync_dt", "Synced"),
        ("local_site", "Active site"),
        ("remote_site", "Remote site"),
        ("files_count", "Files"),
        ("files_size", "Size"),
        ("priority", "Priority"),
        ("state", "Status")
    )

    def __init__(self, sync_server, project=None, parent=None):
        super(SyncRepresentationWidget, self).__init__(parent)

        self.sync_server = sync_server

        self._selected_id = None  # keep last selected _id
        self.representation_id = None
        self.site_name = None  # to pause/unpause representation

        self.filter = QtWidgets.QLineEdit()
        self.filter.setPlaceholderText("Filter representations..")

        self._scrollbar_pos = None

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(self.filter)

        self.table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]
        header_labels = [item[1] for item in self.column_labels]

        model = SyncRepresentationModel(sync_server, headers,
                                        project, header_labels)
        self.table_view.setModel(model)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.horizontalHeader().setSortIndicator(
            -1, Qt.AscendingOrder)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSortIndicatorShown(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().hide()

        time_delegate = PrettyTimeDelegate(self)
        column = self.table_view.model().get_header_index("created_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)
        column = self.table_view.model().get_header_index("sync_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)

        column = self.table_view.model().get_header_index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("remote_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("files_size")
        delegate = SizeDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        for column_name, width in self.default_widths:
            idx = model.get_header_index(column_name)
            self.table_view.setColumnWidth(idx, width)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(self.table_view)

        self.table_view.doubleClicked.connect(self._double_clicked)
        self.filter.textChanged.connect(lambda: model.set_filter(
            self.filter.text()))
        self.table_view.customContextMenuRequested.connect(
            self._on_context_menu)

        model.refresh_started.connect(self._save_scrollbar)
        model.refresh_finished.connect(self._set_scrollbar)
        self.table_view.model().modelReset.connect(self._set_selection)

        self.selection_model = self.table_view.selectionModel()
        self.selection_model.selectionChanged.connect(self._selection_changed)

    def _selection_changed(self, new_selection):
        index = self.selection_model.currentIndex()
        self._selected_id = \
            self.table_view.model().data(index, Qt.UserRole)

    def _set_selection(self):
        """
            Sets selection to 'self._selected_id' if exists.

            Keep selection during model refresh.
        """
        if self._selected_id:
            index = self.table_view.model().get_index(self._selected_id)
            if index and index.isValid():
                mode = QtCore.QItemSelectionModel.Select | \
                    QtCore.QItemSelectionModel.Rows
                self.selection_model.setCurrentIndex(index, mode)
            else:
                self._selected_id = None

    def _double_clicked(self, index):
        """
            Opens representation dialog with all files after doubleclick
        """
        _id = self.table_view.model().data(index, Qt.UserRole)
        detail_window = SyncServerDetailWindow(
            self.sync_server, _id, self.table_view.model().project)
        detail_window.exec()

    def _on_context_menu(self, point):
        """
            Shows menu with loader actions on Right-click.
        """
        point_index = self.table_view.indexAt(point)
        if not point_index.isValid():
            return

        self.item = self.table_view.model()._data[point_index.row()]
        self.representation_id = self.item._id
        log.debug("menu representation _id:: {}".
                  format(self.representation_id))

        menu = QtWidgets.QMenu()
        actions_mapping = {}
        actions_kwargs_mapping = {}

        local_site = self.item.local_site
        local_progress = self.item.local_progress
        remote_site = self.item.remote_site
        remote_progress = self.item.remote_progress

        for site, progress in {local_site: local_progress,
                               remote_site: remote_progress}.items():
            project = self.table_view.model().project
            provider = self.sync_server.get_provider_for_site(project,
                                                              site)
            if provider == 'local_drive':
                if 'studio' in site:
                    txt = " studio version"
                else:
                    txt = " local version"
                action = QtWidgets.QAction("Open in explorer" + txt)
                if progress == 1.0:
                    actions_mapping[action] = self._open_in_explorer
                    actions_kwargs_mapping[action] = {'site': site}
                    menu.addAction(action)

        # progress smaller then 1.0 --> in progress or queued
        if local_progress < 1.0:
            self.site_name = local_site
        else:
            self.site_name = remote_site

        if self.item.state in [STATUS[0], STATUS[1]]:
            action = QtWidgets.QAction("Pause")
            actions_mapping[action] = self._pause
            menu.addAction(action)

        if self.item.state == STATUS[3]:
            action = QtWidgets.QAction("Unpause")
            actions_mapping[action] = self._unpause
            menu.addAction(action)

        # if self.item.state == STATUS[1]:
        #     action = QtWidgets.QAction("Open error detail")
        #     actions_mapping[action] = self._show_detail
        #     menu.addAction(action)

        if remote_progress == 1.0:
            action = QtWidgets.QAction("Reset local site")
            actions_mapping[action] = self._reset_local_site
            menu.addAction(action)

        if local_progress == 1.0:
            action = QtWidgets.QAction("Reset remote site")
            actions_mapping[action] = self._reset_remote_site
            menu.addAction(action)

        if local_site != self.sync_server.DEFAULT_SITE:
            action = QtWidgets.QAction("Completely remove from local")
            actions_mapping[action] = self._remove_site
            menu.addAction(action)
        else:
            action = QtWidgets.QAction("Mark for sync to local")
            actions_mapping[action] = self._add_site
            menu.addAction(action)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            to_run_kwargs = actions_kwargs_mapping.get(result, {})
            if to_run:
                to_run(**to_run_kwargs)

        self.table_view.model().refresh()

    def _pause(self):
        self.sync_server.pause_representation(self.table_view.model().project,
                                              self.representation_id,
                                              self.site_name)
        self.site_name = None
        self.message_generated.emit("Paused {}".format(self.representation_id))

    def _unpause(self):
        self.sync_server.unpause_representation(
            self.table_view.model().project,
            self.representation_id,
            self.site_name)
        self.site_name = None
        self.message_generated.emit("Unpaused {}".format(
            self.representation_id))

    # temporary here for testing, will be removed TODO
    def _add_site(self):
        log.info(self.representation_id)
        project_name = self.table_view.model().project
        local_site_name = get_local_site_id()
        try:
            self.sync_server.add_site(
                project_name,
                self.representation_id,
                local_site_name
                )
            self.message_generated.emit(
                "Site {} added for {}".format(local_site_name,
                                              self.representation_id))
        except ValueError as exp:
            self.message_generated.emit("Error {}".format(str(exp)))

    def _remove_site(self):
        """
            Removes site record AND files.

            This is ONLY for representations stored on local site, which
            cannot be same as SyncServer.DEFAULT_SITE.

            This could only happen when artist work on local machine, not
            connected to studio mounted drives.
        """
        log.info("Removing {}".format(self.representation_id))
        try:
            local_site = get_local_site_id()
            self.sync_server.remove_site(
                self.table_view.model().project,
                self.representation_id,
                local_site,
                True
                )
            self.message_generated.emit("Site {} removed".format(local_site))
        except ValueError as exp:
            self.message_generated.emit("Error {}".format(str(exp)))
        self.table_view.model().refresh(
            load_records=self.table_view.model()._rec_loaded)

    def _reset_local_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.table_view.model().project,
            self.representation_id,
            'local'
            )
        self.table_view.model().refresh(
            load_records=self.table_view.model()._rec_loaded)

    def _reset_remote_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.table_view.model().project,
            self.representation_id,
            'remote'
            )
        self.table_view.model().refresh(
            load_records=self.table_view.model()._rec_loaded)

    def _open_in_explorer(self, site):
        if not self.item:
            return

        fpath = self.item.path
        project = self.table_view.model().project
        fpath = self.sync_server.get_local_file_path(project,
                                                     site,
                                                     fpath)

        fpath = os.path.normpath(os.path.dirname(fpath))
        if os.path.isdir(fpath):
            if 'win' in sys.platform:  # windows
                subprocess.Popen('explorer "%s"' % fpath)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', fpath])
            else:  # linux
                try:
                    subprocess.Popen(['xdg-open', fpath])
                except OSError:
                    raise OSError('unsupported xdg-open call??')

    def _save_scrollbar(self):
        self._scrollbar_pos = self.table_view.verticalScrollBar().value()

    def _set_scrollbar(self):
        if self._scrollbar_pos:
            self.table_view.verticalScrollBar().setValue(self._scrollbar_pos)


ProviderRole = QtCore.Qt.UserRole + 2
ProgressRole = QtCore.Qt.UserRole + 4


class SyncRepresentationModel(QtCore.QAbstractTableModel):
    """
        Model for summary of representations.

        Groups files information per representation. Allows sorting and
        full text filtering.

        Allows pagination, most of heavy lifting is being done on DB side.
        Single model matches to single collection. When project is changed,
        model is reset and refreshed.

        Args:
            sync_server (SyncServer) - object to call server operations (update
                db status, set site status...)
            header (list) - names of visible columns
            project (string) - collection name, all queries must be called on
                a specific collection

    """
    PAGE_SIZE = 20  # default page size to query for
    REFRESH_SEC = 5000  # in seconds, requery DB for new status
    DEFAULT_SORT = {
        "updated_dt_remote": -1,
        "_id": 1
    }
    SORT_BY_COLUMN = [
        "context.asset",  # asset
        "context.subset",  # subset
        "context.version",  # version
        "context.representation",  # representation
        "updated_dt_local",  # local created_dt
        "updated_dt_remote",  # remote created_dt
        "avg_progress_local",  # local progress
        "avg_progress_remote",  # remote progress
        "files_count",  # count of files
        "files_size",  # file size of all files
        "context.asset",  # priority TODO
        "status"  # state
    ]

    refresh_started = QtCore.Signal()
    refresh_finished = QtCore.Signal()

    @attr.s
    class SyncRepresentation:
        """
            Auxiliary object for easier handling.

            Fields must contain all header values (+ any arbitrary values).
        """
        _id = attr.ib()
        asset = attr.ib()
        subset = attr.ib()
        version = attr.ib()
        representation = attr.ib()
        created_dt = attr.ib(default=None)
        sync_dt = attr.ib(default=None)
        local_site = attr.ib(default=None)
        remote_site = attr.ib(default=None)
        local_provider = attr.ib(default=None)
        remote_provider = attr.ib(default=None)
        local_progress = attr.ib(default=None)
        remote_progress = attr.ib(default=None)
        files_count = attr.ib(default=None)
        files_size = attr.ib(default=None)
        priority = attr.ib(default=None)
        state = attr.ib(default=None)
        path = attr.ib(default=None)

    def __init__(self, sync_server, header, project=None, header_labels=None):
        super(SyncRepresentationModel, self).__init__()
        self._header = header
        self._header_labels = header_labels
        self._data = []
        self._project = project
        self._rec_loaded = 0
        self._total_records = 0  # how many documents query actually found
        self.filter = None

        self._initialized = False
        if not self._project or self._project == DUMMY_PROJECT:
            return

        self.sync_server = sync_server
        # TODO think about admin mode
        # this is for regular user, always only single local and single remote
        self.local_site = self.sync_server.get_active_site(self.project)
        self.remote_site = self.sync_server.get_remote_site(self.project)

        self.projection = self.get_default_projection()

        self.sort = self.DEFAULT_SORT

        self.query = self.get_default_query()
        self.default_query = list(self.get_default_query())

        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.REFRESH_SEC)

    @property
    def dbcon(self):
        """
            Database object with preselected project (collection) to run DB
            operations (find, aggregate).

            All queries should go through this (because of collection).
        """
        return self.sync_server.connection.database[self.project]

    @property
    def project(self):
        """Returns project"""
        return self._project

    def data(self, index, role):
        item = self._data[index.row()]

        if role == ProviderRole:
            if self._header[index.column()] == 'local_site':
                return item.local_provider
            if self._header[index.column()] == 'remote_site':
                return item.remote_provider

        if role == ProgressRole:
            if self._header[index.column()] == 'local_site':
                return item.local_progress
            if self._header[index.column()] == 'remote_site':
                return item.remote_progress

        if role == Qt.DisplayRole:
            return attr.asdict(item)[self._header[index.column()]]
        if role == Qt.UserRole:
            return item._id

    def rowCount(self, _index):
        return len(self._data)

    def columnCount(self, _index):
        return len(self._header)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if self._header_labels:
                    return str(self._header_labels[section])
                else:
                    return str(self._header[section])

    def tick(self):
        """
            Triggers refresh of model.

            Because of pagination, prepared (sorting, filtering) query needs
            to be run on DB every X seconds.
        """
        self.refresh(representations=None, load_records=self._rec_loaded)
        self.timer.start(self.REFRESH_SEC)

    def get_header_index(self, value):
        """
            Returns index of 'value' in headers

            Args:
                value (str): header name value
            Returns:
                (int)
        """
        return self._header.index(value)

    def refresh(self, representations=None, load_records=0):
        """
            Reloads representations from DB if necessary, adds them to model.

            Runs periodically (every X seconds) or by demand (change of
            sorting, filtering etc.)

            Emits 'modelReset' signal.

            Args:
                representations (PaginationResult object): pass result of
                    aggregate query from outside - mostly for testing only
                load_records (int) - enforces how many records should be
                    actually queried (scrolled a couple of times to list more
                    than single page of records)
        """
        if self.sync_server.is_paused() or \
                self.sync_server.is_project_paused(self.project):
            return
        self.refresh_started.emit()
        self.beginResetModel()
        self._data = []
        self._rec_loaded = 0

        if not representations:
            self.query = self.get_default_query(load_records)
            representations = self.dbcon.aggregate(self.query)

        self._add_page_records(self.local_site, self.remote_site,
                               representations)
        self.endResetModel()
        self.refresh_finished.emit()

    def _add_page_records(self, local_site, remote_site, representations):
        """
            Process all records from 'representation' and add them to storage.

            Args:
                local_site (str): name of local site (mine)
                remote_site (str): name of cloud provider (theirs)
                representations (Mongo Cursor) - mimics result set, 1 object
                    with paginatedResults array and totalCount array
        """
        result = representations.next()
        count = 0
        total_count = result.get("totalCount")
        if total_count:
            count = total_count.pop().get('count')
        self._total_records = count

        local_provider = _translate_provider_for_icon(self.sync_server,
                                                      self.project,
                                                      local_site)
        remote_provider = _translate_provider_for_icon(self.sync_server,
                                                       self.project,
                                                       remote_site)

        for repre in result.get("paginatedResults"):
            context = repre.get("context").pop()
            files = repre.get("files", [])
            if isinstance(files, dict):  # aggregate returns dictionary
                files = [files]

            # representation without files doesnt concern us
            if not files:
                continue

            local_updated = remote_updated = None
            if repre.get('updated_dt_local'):
                local_updated = \
                    repre.get('updated_dt_local').strftime("%Y%m%dT%H%M%SZ")

            if repre.get('updated_dt_remote'):
                remote_updated = \
                    repre.get('updated_dt_remote').strftime("%Y%m%dT%H%M%SZ")

            avg_progress_remote = _convert_progress(
                repre.get('avg_progress_remote', '0'))
            avg_progress_local = _convert_progress(
                repre.get('avg_progress_local', '0'))

            if context.get("version"):
                version = "v{:0>3d}".format(context.get("version"))
            else:
                version = "master"

            item = self.SyncRepresentation(
                repre.get("_id"),
                context.get("asset"),
                context.get("subset"),
                version,
                context.get("representation"),
                local_updated,
                remote_updated,
                local_site,
                remote_site,
                local_provider,
                remote_provider,
                avg_progress_local,
                avg_progress_remote,
                repre.get("files_count", 1),
                repre.get("files_size", 0),
                1,
                STATUS[repre.get("status", -1)],
                files[0].get('path')
            )

            self._data.append(item)
            self._rec_loaded += 1

    def canFetchMore(self, _index):
        """
            Check if there are more records than currently loaded
        """
        # 'skip' might be suboptimal when representation hits 500k+
        return self._total_records > self._rec_loaded

    def fetchMore(self, index):
        """
            Add more record to model.

            Called when 'canFetchMore' returns true, which means there are
            more records in DB than loaded.
        """
        log.debug("fetchMore")
        items_to_fetch = min(self._total_records - self._rec_loaded,
                             self.PAGE_SIZE)
        self.query = self.get_default_query(self._rec_loaded)
        representations = self.dbcon.aggregate(self.query)
        self.beginInsertRows(index,
                             self._rec_loaded,
                             self._rec_loaded + items_to_fetch - 1)

        self._add_page_records(self.local_site, self.remote_site,
                               representations)

        self.endInsertRows()

    def sort(self, index, order):
        """
            Summary sort per representation.

            Sort is happening on a DB side, model is reset, db queried
            again.

            Args:
                index (int): column index
                order (int): 0|
        """
        # limit unwanted first re-sorting by view
        if index < 0:
            return

        self._rec_loaded = 0
        if order == 0:
            order = 1
        else:
            order = -1

        self.sort = {self.SORT_BY_COLUMN[index]: order, '_id': 1}
        self.query = self.get_default_query()
        # import json
        # log.debug(json.dumps(self.query, indent=4).\
        #           replace('False', 'false').\
        #           replace('True', 'true').replace('None', 'null'))

        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

    def set_filter(self, filter):
        """
            Adds text value filtering

            Args:
                filter (str): string inputted by user
        """
        self.filter = filter
        self.refresh()

    def set_project(self, project):
        """
            Changes project, called after project selection is changed

            Args:
                project (str): name of project
        """
        self._project = project
        self.sync_server.set_sync_project_settings()
        self.local_site = self.sync_server.get_active_site(self.project)
        self.remote_site = self.sync_server.get_remote_site(self.project)
        self.refresh()

    def get_index(self, id):
        """
            Get index of 'id' value.

            Used for keeping selection after refresh.

            Args:
                id (str): MongoDB _id
            Returns:
                (QModelIndex)
        """
        for i in range(self.rowCount(None)):
            index = self.index(i, 0)
            value = self.data(index, Qt.UserRole)
            if value == id:
                return index
        return None

    def get_default_query(self, limit=0):
        """
            Returns basic aggregate query for main table.

            Main table provides summary information about representation,
            which could have multiple files. Details are accessible after
            double click on representation row.
            Columns:
                'created_dt' - max of created or updated (when failed) per repr
                'sync_dt' - same for remote side
                'local_site' - progress of repr on local side, 1 = finished
                'remote_site' - progress on remote side, calculates from files
                'state' -
                    0 - in progress
                    1 - failed
                    2 - queued
                    3 - paused
                    4 - finished on both sides

                are calculated and must be calculated in DB because of
                pagination

            Args:
                limit (int): how many records should be returned, by default
                    it 'PAGE_SIZE' for performance.
                    Should be overridden by value of loaded records for refresh
                    functionality (got more records by scrolling, refresh
                    shouldn't reset that)
        """
        if limit == 0:
            limit = SyncRepresentationModel.PAGE_SIZE

        return [
            {"$match": self._get_match_part()},
            {'$unwind': '$files'},
            # merge potentially unwinded records back to single per repre
            {'$addFields': {
                'order_remote': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.remote_site]}
                                }},
                'order_local': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.local_site]}
                                }}
            }},
            {'$addFields': {
                # prepare progress per file, presence of 'created_dt' denotes
                # successfully finished load/download
                'progress_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.progress"},
                              "$order_remote.progress",
                              {'$cond': [
                                  {'$size': "$order_remote.created_dt"},
                                  [1],
                                  [0]
                              ]}
                              ]}},
                'progress_local': {'$first': {
                    '$cond': [{'$size': "$order_local.progress"},
                              "$order_local.progress",
                              {'$cond': [
                                  {'$size': "$order_local.created_dt"},
                                  [1],
                                  [0]
                              ]}
                              ]}},
                # file might be successfully created or failed, not both
                'updated_dt_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.created_dt"},
                              "$order_remote.created_dt",
                              {'$cond': [
                                  {'$size': "$order_remote.last_failed_dt"},
                                  "$order_remote.last_failed_dt",
                                  []
                              ]}
                              ]}},
                'updated_dt_local': {'$first': {
                    '$cond': [{'$size': "$order_local.created_dt"},
                              "$order_local.created_dt",
                              {'$cond': [
                                  {'$size': "$order_local.last_failed_dt"},
                                  "$order_local.last_failed_dt",
                                  []
                              ]}
                              ]}},
                'files_size': {'$ifNull': ["$files.size", 0]},
                'failed_remote': {
                    '$cond': [{'$size': "$order_remote.last_failed_dt"},
                              1,
                              0]},
                'failed_local': {
                    '$cond': [{'$size': "$order_local.last_failed_dt"},
                              1,
                              0]},
                'failed_local_tries': {
                    '$cond': [{'$size': '$order_local.tries'},
                              {'$first': '$order_local.tries'},
                              0]},
                'failed_remote_tries': {
                    '$cond': [{'$size': '$order_remote.tries'},
                              {'$first': '$order_remote.tries'},
                              0]},
                'paused_remote': {
                    '$cond': [{'$size': "$order_remote.paused"},
                              1,
                              0]},
                'paused_local': {
                    '$cond': [{'$size': "$order_local.paused"},
                              1,
                              0]},
            }},
            {'$group': {
                '_id': '$_id',
                # pass through context - same for representation
                'context': {'$addToSet': '$context'},
                'data': {'$addToSet': '$data'},
                # pass through files as a list
                'files': {'$addToSet': '$files'},
                # count how many files
                'files_count': {'$sum': 1},
                'files_size': {'$sum': '$files_size'},
                # sum avg progress, finished = 1
                'avg_progress_remote': {'$avg': "$progress_remote"},
                'avg_progress_local': {'$avg': "$progress_local"},
                # select last touch of file
                'updated_dt_remote': {'$max': "$updated_dt_remote"},
                'failed_remote': {'$sum': '$failed_remote'},
                'failed_local': {'$sum': '$failed_local'},
                'failed_remote_tries': {'$sum': '$failed_remote_tries'},
                'failed_local_tries': {'$sum': '$failed_local_tries'},
                'paused_remote': {'$sum': '$paused_remote'},
                'paused_local': {'$sum': '$paused_local'},
                'updated_dt_local': {'$max': "$updated_dt_local"}
            }},
            {"$project": self.projection},
            {"$sort": self.sort},
            {
                '$facet': {
                    'paginatedResults': [{'$skip': self._rec_loaded},
                                         {'$limit': limit}],
                    'totalCount': [{'$count': 'count'}]
                }
            }
        ]

    def _get_match_part(self):
        """
            Extend match part with filter if present.

            Filter is set by user input. Each model has different fields to be
            checked.
            If performance issues are found, '$text' and text indexes should
            be investigated.

            Fulltext searches in:
                context.subset
                context.asset
                context.representation  names AND _id (ObjectId)
        """
        base_match = {
                "type": "representation",
                'files.sites.name': {'$all': [self.local_site,
                                              self.remote_site]}
        }
        if not self.filter:
            return base_match
        else:
            regex_str = '.*{}.*'.format(self.filter)
            base_match['$or'] = [
                    {'context.subset': {'$regex': regex_str, '$options': 'i'}},
                    {'context.asset': {'$regex': regex_str, '$options': 'i'}},
                    {'context.representation': {'$regex': regex_str,
                                                '$options': 'i'}}]

            if ObjectId.is_valid(self.filter):
                base_match['$or'] = [{'_id': ObjectId(self.filter)}]

            return base_match

    def get_default_projection(self):
        """
            Projection part for aggregate query.

            All fields with '1' will be returned, no others.

            Returns:
                (dict)
        """
        return {
            "context.subset": 1,
            "context.asset": 1,
            "context.version": 1,
            "context.representation": 1,
            "data.path": 1,
            "files": 1,
            'files_count': 1,
            "files_size": 1,
            'avg_progress_remote': 1,
            'avg_progress_local': 1,
            'updated_dt_remote': 1,
            'updated_dt_local': 1,
            'paused_remote': 1,
            'paused_local': 1,
            'status': {
                '$switch': {
                    'branches': [
                        {
                            'case': {
                                '$or': ['$paused_remote', '$paused_local']},
                            'then': 3  # Paused
                        },
                        {
                            'case': {
                                '$or': [
                                    {'$gte': ['$failed_local_tries', 3]},
                                    {'$gte': ['$failed_remote_tries', 3]}
                                ]},
                            'then': 2},  # Failed
                        {
                            'case': {
                                '$or': [{'$eq': ['$avg_progress_remote', 0]},
                                        {'$eq': ['$avg_progress_local', 0]}]},
                            'then': 1  # Queued
                        },
                        {
                            'case': {'$or': [{'$and': [
                                {'$gt': ['$avg_progress_remote', 0]},
                                {'$lt': ['$avg_progress_remote', 1]}
                            ]},
                                {'$and': [
                                    {'$gt': ['$avg_progress_local', 0]},
                                    {'$lt': ['$avg_progress_local', 1]}
                                ]}
                            ]},
                            'then': 0  # In progress
                        },
                        {
                            'case': {'$and': [
                                {'$eq': ['$avg_progress_remote', 1]},
                                {'$eq': ['$avg_progress_local', 1]}
                            ]},
                            'then': 4  # Synced OK
                        },
                    ],
                    'default': -1
                }
            }
        }


class SyncServerDetailWindow(QtWidgets.QDialog):
    def __init__(self, sync_server, _id, project, parent=None):
        log.debug(
            "!!! SyncServerDetailWindow _id:: {}".format(_id))
        super(SyncServerDetailWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
        self.resize(1000, 400)

        body = QtWidgets.QWidget()
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(20)

        container = SyncRepresentationDetailWidget(sync_server, _id, project,
                                                   parent=self)
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.addWidget(container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self.message = QtWidgets.QLabel()
        self.message.hide()

        footer_layout = QtWidgets.QVBoxLayout(footer)
        footer_layout.addWidget(self.message)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(footer)

        self.setLayout(body_layout)
        self.setWindowTitle("Sync Representation Detail")


class SyncRepresentationDetailWidget(QtWidgets.QWidget):
    """
        Widget to display list of synchronizable files for single repre.

        Args:
            _id (str): representation _id
            project (str): name of project with repre
            parent (QDialog): SyncServerDetailWindow
    """
    active_changed = QtCore.Signal()  # active index changed

    default_widths = (
        ("file", 290),
        ("created_dt", 105),
        ("sync_dt", 105),
        ("local_site", 80),
        ("remote_site", 80),
        ("size", 60),
        ("priority", 20),
        ("state", 90)
    )

    column_labels = (
        ("file", "File name"),
        ("created_dt", "Created"),
        ("sync_dt", "Synced"),
        ("local_site", "Active site"),
        ("remote_site", "Remote site"),
        ("files_size", "Size"),
        ("priority", "Priority"),
        ("state", "Status")
    )

    def __init__(self, sync_server, _id=None, project=None, parent=None):
        super(SyncRepresentationDetailWidget, self).__init__(parent)

        log.debug("Representation_id:{}".format(_id))
        self.representation_id = _id
        self.item = None  # set to item that mouse was clicked over
        self.project = project

        self.sync_server = sync_server

        self._selected_id = None

        self.filter = QtWidgets.QLineEdit()
        self.filter.setPlaceholderText("Filter representation..")

        self._scrollbar_pos = None

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(self.filter)

        self.table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]
        header_labels = [item[1] for item in self.column_labels]

        model = SyncRepresentationDetailModel(sync_server, headers, _id,
                                              project, header_labels)
        self.table_view.setModel(model)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(
            QtWidgets.QTableView.SelectRows)
        self.table_view.horizontalHeader().setSortIndicator(-1,
                                                            Qt.AscendingOrder)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSortIndicatorShown(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().hide()

        time_delegate = PrettyTimeDelegate(self)
        column = self.table_view.model().get_header_index("created_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)
        column = self.table_view.model().get_header_index("sync_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)

        column = self.table_view.model().get_header_index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("remote_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("size")
        delegate = SizeDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        for column_name, width in self.default_widths:
            idx = model.get_header_index(column_name)
            self.table_view.setColumnWidth(idx, width)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(self.table_view)

        self.filter.textChanged.connect(lambda: model.set_filter(
            self.filter.text()))
        self.table_view.customContextMenuRequested.connect(
            self._on_context_menu)

        model.refresh_started.connect(self._save_scrollbar)
        model.refresh_finished.connect(self._set_scrollbar)
        self.table_view.model().modelReset.connect(self._set_selection)

        self.selection_model = self.table_view.selectionModel()
        self.selection_model.selectionChanged.connect(self._selection_changed)

    def _selection_changed(self):
        index = self.selection_model.currentIndex()
        self._selected_id = self.table_view.model().data(index, Qt.UserRole)

    def _set_selection(self):
        """
            Sets selection to 'self._selected_id' if exists.

            Keep selection during model refresh.
        """
        if self._selected_id:
            index = self.table_view.model().get_index(self._selected_id)
            if index and index.isValid():
                mode = QtCore.QItemSelectionModel.Select | \
                    QtCore.QItemSelectionModel.Rows
                self.selection_model.setCurrentIndex(index, mode)
            else:
                self._selected_id = None

    def _show_detail(self):
        """
            Shows windows with error message for failed sync of a file.
        """
        dt = max(self.item.created_dt, self.item.sync_dt)
        detail_window = SyncRepresentationErrorWindow(self.item._id,
                                                      self.project,
                                                      dt,
                                                      self.item.tries,
                                                      self.item.error)
        detail_window.exec()

    def _on_context_menu(self, point):
        """
            Shows menu with loader actions on Right-click.
        """
        point_index = self.table_view.indexAt(point)
        if not point_index.isValid():
            return

        self.item = self.table_view.model()._data[point_index.row()]

        menu = QtWidgets.QMenu()
        actions_mapping = {}
        actions_kwargs_mapping = {}

        local_site = self.item.local_site
        local_progress = self.item.local_progress
        remote_site = self.item.remote_site
        remote_progress = self.item.remote_progress

        for site, progress in {local_site: local_progress,
                               remote_site: remote_progress}.items():
            project = self.table_view.model().project
            provider = self.sync_server.get_provider_for_site(project,
                                                              site)
            if provider == 'local_drive':
                if 'studio' in site:
                    txt = " studio version"
                else:
                    txt = " local version"
                action = QtWidgets.QAction("Open in explorer" + txt)
                if progress == 1:
                    actions_mapping[action] = self._open_in_explorer
                    actions_kwargs_mapping[action] = {'site': site}
                    menu.addAction(action)

        if self.item.state == STATUS[2]:
            action = QtWidgets.QAction("Open error detail")
            actions_mapping[action] = self._show_detail
            menu.addAction(action)

        if float(remote_progress) == 1.0:
            action = QtWidgets.QAction("Reset active site")
            actions_mapping[action] = self._reset_local_site
            menu.addAction(action)

        if float(local_progress) == 1.0:
            action = QtWidgets.QAction("Reset remote site")
            actions_mapping[action] = self._reset_remote_site
            menu.addAction(action)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            to_run_kwargs = actions_kwargs_mapping.get(result, {})
            if to_run:
                to_run(**to_run_kwargs)

    def _reset_local_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.table_view.model().project,
            self.representation_id,
            'local',
            self.item._id)
        self.table_view.model().refresh(
            load_records=self.table_view.model()._rec_loaded)

    def _reset_remote_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.table_view.model().project,
            self.representation_id,
            'remote',
            self.item._id)
        self.table_view.model().refresh(
            load_records=self.table_view.model()._rec_loaded)

    def _open_in_explorer(self, site):
        if not self.item:
            return

        fpath = self.item.path
        project = self.project
        fpath = self.sync_server.get_local_file_path(project, site, fpath)

        fpath = os.path.normpath(os.path.dirname(fpath))
        if os.path.isdir(fpath):
            if 'win' in sys.platform:  # windows
                subprocess.Popen('explorer "%s"' % fpath)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', fpath])
            else:  # linux
                try:
                    subprocess.Popen(['xdg-open', fpath])
                except OSError:
                    raise OSError('unsupported xdg-open call??')

    def _save_scrollbar(self):
        self._scrollbar_pos = self.table_view.verticalScrollBar().value()

    def _set_scrollbar(self):
        if self._scrollbar_pos:
            self.table_view.verticalScrollBar().setValue(self._scrollbar_pos)


class SyncRepresentationDetailModel(QtCore.QAbstractTableModel):
    """
        List of all syncronizable files per single representation.

        Used in detail window accessible after clicking on single repre in the
        summary.

        TODO refactor - merge with SyncRepresentationModel if possible

        Args:
            sync_server (SyncServer) - object to call server operations (update
                db status, set site status...)
            header (list) - names of visible columns
            _id (string) - MongoDB _id of representation
            project (string) - collection name, all queries must be called on
                a specific collection
    """
    PAGE_SIZE = 30
    DEFAULT_SORT = {
        "files.path": 1
    }
    SORT_BY_COLUMN = [
        "files.path",
        "updated_dt_local",  # local created_dt
        "updated_dt_remote",  # remote created_dt
        "progress_local",  # local progress
        "progress_remote",  # remote progress
        "size",  # remote progress
        "context.asset",  # priority TODO
        "status"  # state
    ]

    refresh_started = QtCore.Signal()
    refresh_finished = QtCore.Signal()

    @attr.s
    class SyncRepresentationDetail:
        """
            Auxiliary object for easier handling.

            Fields must contain all header values (+ any arbitrary values).
        """
        _id = attr.ib()
        file = attr.ib()
        created_dt = attr.ib(default=None)
        sync_dt = attr.ib(default=None)
        local_site = attr.ib(default=None)
        remote_site = attr.ib(default=None)
        local_provider = attr.ib(default=None)
        remote_provider = attr.ib(default=None)
        local_progress = attr.ib(default=None)
        remote_progress = attr.ib(default=None)
        size = attr.ib(default=None)
        priority = attr.ib(default=None)
        state = attr.ib(default=None)
        tries = attr.ib(default=None)
        error = attr.ib(default=None)
        path = attr.ib(default=None)

    def __init__(self, sync_server, header, _id,
                 project=None, header_labels=None):
        super(SyncRepresentationDetailModel, self).__init__()
        self._header = header
        self._header_labels = header_labels
        self._data = []
        self._project = project
        self._rec_loaded = 0
        self._total_records = 0  # how many documents query actually found
        self.filter = None
        self._id = _id
        self._initialized = False

        self.sync_server = sync_server
        # TODO think about admin mode
        # this is for regular user, always only single local and single remote
        self.local_site = self.sync_server.get_active_site(self.project)
        self.remote_site = self.sync_server.get_remote_site(self.project)

        self.sort = self.DEFAULT_SORT

        # in case we would like to hide/show some columns
        self.projection = self.get_default_projection()

        self.query = self.get_default_query()
        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(SyncRepresentationModel.REFRESH_SEC)

    @property
    def dbcon(self):
        """
            Database object with preselected project (collection) to run DB
            operations (find, aggregate).

            All queries should go through this (because of collection).
        """
        return self.sync_server.connection.database[self.project]

    @property
    def project(self):
        """Returns project"""
        return self._project

    def tick(self):
        """
            Triggers refresh of model.

            Because of pagination, prepared (sorting, filtering) query needs
            to be run on DB every X seconds.
        """
        self.refresh(representations=None, load_records=self._rec_loaded)
        self.timer.start(SyncRepresentationModel.REFRESH_SEC)

    def get_header_index(self, value):
        """
            Returns index of 'value' in headers

            Args:
                value (str): header name value
            Returns:
                (int)
        """
        return self._header.index(value)

    def data(self, index, role):
        item = self._data[index.row()]

        if role == ProviderRole:
            if self._header[index.column()] == 'local_site':
                return item.local_provider
            if self._header[index.column()] == 'remote_site':
                return item.remote_provider

        if role == ProgressRole:
            if self._header[index.column()] == 'local_site':
                return item.local_progress
            if self._header[index.column()] == 'remote_site':
                return item.remote_progress

        if role == Qt.DisplayRole:
            return attr.asdict(item)[self._header[index.column()]]
        if role == Qt.UserRole:
            return item._id

    def rowCount(self, _index):
        return len(self._data)

    def columnCount(self, _index):
        return len(self._header)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if self._header_labels:
                    return str(self._header_labels[section])
                else:
                    return str(self._header[section])

    def refresh(self, representations=None, load_records=0):
        if self.sync_server.is_paused():
            return

        self.refresh_started.emit()
        self.beginResetModel()
        self._data = []
        self._rec_loaded = 0

        if not representations:
            self.query = self.get_default_query(load_records)
            representations = self.dbcon.aggregate(self.query)

        self._add_page_records(self.local_site, self.remote_site,
                               representations)
        self.endResetModel()
        self.refresh_finished.emit()

    def _add_page_records(self, local_site, remote_site, representations):
        """
            Process all records from 'representation' and add them to storage.

            Args:
                local_site (str): name of local site (mine)
                remote_site (str): name of cloud provider (theirs)
                representations (Mongo Cursor) - mimics result set, 1 object
                    with paginatedResults array and totalCount array
        """
        # representations is a Cursor, get first
        result = representations.next()
        count = 0
        total_count = result.get("totalCount")
        if total_count:
            count = total_count.pop().get('count')
        self._total_records = count

        local_provider = _translate_provider_for_icon(self.sync_server,
                                                      self.project,
                                                      local_site)
        remote_provider = _translate_provider_for_icon(self.sync_server,
                                                       self.project,
                                                       remote_site)

        for repre in result.get("paginatedResults"):
            # log.info("!!! repre:: {}".format(repre))
            files = repre.get("files", [])
            if isinstance(files, dict):  # aggregate returns dictionary
                files = [files]

            for file in files:
                local_updated = remote_updated = None
                if repre.get('updated_dt_local'):
                    local_updated = \
                        repre.get('updated_dt_local').strftime(
                            "%Y%m%dT%H%M%SZ")

                if repre.get('updated_dt_remote'):
                    remote_updated = \
                        repre.get('updated_dt_remote').strftime(
                            "%Y%m%dT%H%M%SZ")

                remote_progress = _convert_progress(
                    repre.get('progress_remote', '0'))
                local_progress = _convert_progress(
                    repre.get('progress_local', '0'))

                errors = []
                if repre.get('failed_remote_error'):
                    errors.append(repre.get('failed_remote_error'))
                if repre.get('failed_local_error'):
                    errors.append(repre.get('failed_local_error'))

                item = self.SyncRepresentationDetail(
                    file.get("_id"),
                    os.path.basename(file["path"]),
                    local_updated,
                    remote_updated,
                    local_site,
                    remote_site,
                    local_provider,
                    remote_provider,
                    local_progress,
                    remote_progress,
                    file.get('size', 0),
                    1,
                    STATUS[repre.get("status", -1)],
                    repre.get("tries"),
                    '\n'.join(errors),
                    file.get('path')

                )
                self._data.append(item)
                self._rec_loaded += 1

    def canFetchMore(self, _index):
        """
            Check if there are more records than currently loaded
        """
        # 'skip' might be suboptimal when representation hits 500k+
        return self._total_records > self._rec_loaded

    def fetchMore(self, index):
        """
            Add more record to model.

            Called when 'canFetchMore' returns true, which means there are
            more records in DB than loaded.
            'self._buffer' is used to stash cursor to limit requery
        """
        log.debug("fetchMore")
        items_to_fetch = min(self._total_records - self._rec_loaded,
                             self.PAGE_SIZE)
        self.query = self.get_default_query(self._rec_loaded)
        representations = self.dbcon.aggregate(self.query)
        self.beginInsertRows(index,
                             self._rec_loaded,
                             self._rec_loaded + items_to_fetch - 1)

        self._add_page_records(self.local_site, self.remote_site,
                               representations)

        self.endInsertRows()

    def sort(self, index, order):
        # limit unwanted first re-sorting by view
        if index < 0:
            return

        self._rec_loaded = 0  # change sort - reset from start

        if order == 0:
            order = 1
        else:
            order = -1

        self.sort = {self.SORT_BY_COLUMN[index]: order}
        self.query = self.get_default_query()

        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

    def set_filter(self, filter):
        self.filter = filter
        self.refresh()

    def get_index(self, id):
        """
            Get index of 'id' value.

            Used for keeping selection after refresh.

            Args:
                id (str): MongoDB _id
            Returns:
                (QModelIndex)
        """
        for i in range(self.rowCount(None)):
            index = self.index(i, 0)
            value = self.data(index, Qt.UserRole)
            if value == id:
                return index
        return None

    def get_default_query(self, limit=0):
        """
            Gets query that gets used when no extra sorting, filtering or
            projecting is needed.

            Called for basic table view.

            Returns:
                [(dict)] - list with single dict - appropriate for aggregate
                    function for MongoDB
        """
        if limit == 0:
            limit = SyncRepresentationModel.PAGE_SIZE

        return [
            {"$match": self._get_match_part()},
            {"$unwind": "$files"},
            {'$addFields': {
                'order_remote': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.remote_site]}
                                }},
                'order_local': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.local_site]}
                                }}
            }},
            {'$addFields': {
                # prepare progress per file, presence of 'created_dt' denotes
                # successfully finished load/download
                'progress_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.progress"},
                              "$order_remote.progress",
                              {'$cond': [
                                  {'$size': "$order_remote.created_dt"},
                                  [1],
                                  [0]
                              ]}
                              ]}},
                'progress_local': {'$first': {
                    '$cond': [{'$size': "$order_local.progress"},
                              "$order_local.progress",
                              {'$cond': [
                                  {'$size': "$order_local.created_dt"},
                                  [1],
                                  [0]
                              ]}
                              ]}},
                # file might be successfully created or failed, not both
                'updated_dt_remote': {'$first': {
                    '$cond': [
                        {'$size': "$order_remote.created_dt"},
                        "$order_remote.created_dt",
                        {
                            '$cond': [
                                {'$size': "$order_remote.last_failed_dt"},
                                "$order_remote.last_failed_dt",
                                []
                            ]
                        }
                    ]
                }},
                'updated_dt_local': {'$first': {
                    '$cond': [
                        {'$size': "$order_local.created_dt"},
                        "$order_local.created_dt",
                        {
                            '$cond': [
                                {'$size': "$order_local.last_failed_dt"},
                                "$order_local.last_failed_dt",
                                []
                            ]
                        }
                    ]
                }},
                'paused_remote': {
                    '$cond': [{'$size': "$order_remote.paused"},
                              1,
                              0]},
                'paused_local': {
                    '$cond': [{'$size': "$order_local.paused"},
                              1,
                              0]},
                'failed_remote': {
                    '$cond': [{'$size': "$order_remote.last_failed_dt"},
                              1,
                              0]},
                'failed_local': {
                    '$cond': [{'$size': "$order_local.last_failed_dt"},
                              1,
                              0]},
                'failed_remote_error': {'$first': {
                    '$cond': [{'$size': "$order_remote.error"},
                              "$order_remote.error",
                              [""]]}},
                'failed_local_error': {'$first': {
                    '$cond': [{'$size': "$order_local.error"},
                              "$order_local.error",
                              [""]]}},
                'tries': {'$first': {
                    '$cond': [
                        {'$size': "$order_local.tries"},
                        "$order_local.tries",
                        {'$cond': [
                            {'$size': "$order_remote.tries"},
                            "$order_remote.tries",
                            []
                        ]}
                    ]}}
            }},
            {"$project": self.projection},
            {"$sort": self.sort},
            {
                '$facet': {
                    'paginatedResults': [{'$skip': self._rec_loaded},
                                         {'$limit': limit}],
                    'totalCount': [{'$count': 'count'}]
                }
            }
        ]

    def _get_match_part(self):
        """
            Returns different content for 'match' portion if filtering by
            name is present

            Returns:
                (dict)
        """
        if not self.filter:
            return {
                "type": "representation",
                "_id": self._id
            }
        else:
            regex_str = '.*{}.*'.format(self.filter)
            return {
                "type": "representation",
                "_id": self._id,
                '$or': [{'files.path': {'$regex': regex_str, '$options': 'i'}}]
            }

    def get_default_projection(self):
        """
            Projection part for aggregate query.

            All fields with '1' will be returned, no others.

            Returns:
                (dict)
        """
        return {
            "files": 1,
            'progress_remote': 1,
            'progress_local': 1,
            'updated_dt_remote': 1,
            'updated_dt_local': 1,
            'paused_remote': 1,
            'paused_local': 1,
            'failed_remote_error': 1,
            'failed_local_error': 1,
            'tries': 1,
            'status': {
                '$switch': {
                    'branches': [
                        {
                            'case': {
                                '$or': ['$paused_remote', '$paused_local']},
                            'then': 3  # Paused
                        },
                        {
                            'case': {
                                '$and': [{'$or': ['$failed_remote',
                                                  '$failed_local']},
                                         {'$eq': ['$tries', 3]}]},
                            'then': 1  # Failed (3 tries)
                        },
                        {
                            'case': {
                                '$or': [{'$eq': ['$progress_remote', 0]},
                                        {'$eq': ['$progress_local', 0]}]},
                            'then': 2  # Queued
                        },
                        {
                            'case': {
                                '$or': ['$failed_remote', '$failed_local']},
                            'then': 1  # Failed
                        },
                        {
                            'case': {'$or': [{'$and': [
                                {'$gt': ['$progress_remote', 0]},
                                {'$lt': ['$progress_remote', 1]}
                            ]},
                                {'$and': [
                                    {'$gt': ['$progress_local', 0]},
                                    {'$lt': ['$progress_local', 1]}
                                ]}
                            ]},
                            'then': 0  # In Progress
                        },
                        {
                            'case': {'$and': [
                                {'$eq': ['$progress_remote', 1]},
                                {'$eq': ['$progress_local', 1]}
                            ]},
                            'then': 4  # Synced OK
                        },
                    ],
                    'default': -1
                }
            },
            'data.path': 1
        }


class ImageDelegate(QtWidgets.QStyledItemDelegate):
    """
        Prints icon of site and progress of synchronization
    """

    def __init__(self, parent=None):
        super(ImageDelegate, self).__init__(parent)
        self.icons = {}

    def paint(self, painter, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        option.showDecorationSelected = True

        if (option.showDecorationSelected and
                (option.state & QtWidgets.QStyle.State_Selected)):
            painter.setOpacity(0.20)  # highlight color is a bit off
            painter.fillRect(option.rect,
                             option.palette.highlight())
            painter.setOpacity(1)

        provider = index.data(ProviderRole)
        value = index.data(ProgressRole)

        if not self.icons.get(provider):
            resource_path = os.path.dirname(__file__)
            resource_path = os.path.join(resource_path, "..",
                                         "providers", "resources")
            pix_url = "{}/{}.png".format(resource_path, provider)
            pixmap = QtGui.QPixmap(pix_url)
            self.icons[provider] = pixmap
        else:
            pixmap = self.icons[provider]

        point = QtCore.QPoint(option.rect.x() +
                              (option.rect.width() - pixmap.width()) / 2,
                              option.rect.y() +
                              (option.rect.height() - pixmap.height()) / 2)
        painter.drawPixmap(point, pixmap)

        painter.setOpacity(0.5)
        overlay_rect = option.rect
        overlay_rect.setHeight(overlay_rect.height() * (1.0 - float(value)))
        painter.fillRect(overlay_rect,
                         QtGui.QBrush(QtGui.QColor(0, 0, 0, 200)))
        painter.setOpacity(1)


class SyncRepresentationErrorWindow(QtWidgets.QDialog):
    def __init__(self, _id, project, dt, tries, msg, parent=None):
        super(SyncRepresentationErrorWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
        self.resize(250, 200)

        body = QtWidgets.QWidget()
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(20)

        container = SyncRepresentationErrorWidget(_id, project, dt, tries, msg,
                                                  parent=self)
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.addWidget(container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        message = QtWidgets.QLabel()
        message.hide()

        footer_layout = QtWidgets.QVBoxLayout(footer)
        footer_layout.addWidget(message)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(footer)

        self.setLayout(body_layout)
        self.setWindowTitle("Sync Representation Error Detail")


class SyncRepresentationErrorWidget(QtWidgets.QWidget):
    """
        Dialog to show when sync error happened, prints error message
    """

    def __init__(self, _id, project, dt, tries, msg, parent=None):
        super(SyncRepresentationErrorWidget, self).__init__(parent)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow(QtWidgets.QLabel("Last update date"),
                      QtWidgets.QLabel(pretty_timestamp(dt)))
        layout.addRow(QtWidgets.QLabel("Retries"),
                      QtWidgets.QLabel(str(tries)))
        layout.addRow(QtWidgets.QLabel("Error message"),
                      QtWidgets.QLabel(msg))


class SizeDelegate(QtWidgets.QStyledItemDelegate):
    """
        Pretty print for file size
    """

    def __init__(self, parent=None):
        super(SizeDelegate, self).__init__(parent)

    def displayText(self, value, _locale):
        if value is None:
            # Ignore None value
            return

        return self._pretty_size(value)

    def _pretty_size(self, value, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(value) < 1024.0:
                return "%3.1f%s%s" % (value, unit, suffix)
            value /= 1024.0
        return "%.1f%s%s" % (value, 'Yi', suffix)


def _convert_progress(value):
    try:
        progress = float(value)
    except (ValueError, TypeError):
        progress = 0.0

    return progress


def _translate_provider_for_icon(sync_server, project, site):
    """
        Get provider for 'site'

        This is used for getting icon, 'studio' should have different icon
        then local sites, even the provider 'local_drive' is same

    """
    if site == sync_server.DEFAULT_SITE:
        return sync_server.DEFAULT_SITE
    return sync_server.get_provider_for_site(project, site)
