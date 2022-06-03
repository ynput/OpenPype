import os
import subprocess
import sys
from functools import partial

from Qt import QtWidgets, QtCore, QtGui
from Qt.QtCore import Qt
import qtawesome

from openpype.tools.settings import style

from openpype.api import get_local_site_id
from openpype.lib import PypeLogger

from openpype.tools.utils.delegates import pretty_timestamp

from .models import (
    SyncRepresentationSummaryModel,
    SyncRepresentationDetailModel
)

from . import lib
from . import delegates

from openpype.tools.utils.constants import (
    LOCAL_PROGRESS_ROLE,
    REMOTE_PROGRESS_ROLE,
    HEADER_NAME_ROLE,
    STATUS_ROLE,
    PATH_ROLE,
    LOCAL_SITE_NAME_ROLE,
    REMOTE_SITE_NAME_ROLE,
    LOCAL_DATE_ROLE,
    REMOTE_DATE_ROLE,
    ERROR_ROLE,
    TRIES_ROLE
)

log = PypeLogger().get_logger("SyncServer")


class SyncProjectListWidget(QtWidgets.QWidget):
    """
        Lists all projects that are synchronized to choose from
    """
    project_changed = QtCore.Signal()
    message_generated = QtCore.Signal(str)

    refresh_msec = 10000

    def __init__(self, sync_server, parent):
        super(SyncProjectListWidget, self).__init__(parent)
        self.setObjectName("ProjectListWidget")

        self._parent = parent

        label_widget = QtWidgets.QLabel("Projects", self)
        project_list = QtWidgets.QListView(self)
        project_model = QtGui.QStandardItemModel()
        project_list.setModel(project_model)
        project_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # Do not allow editing
        project_list.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(label_widget, 0)
        layout.addWidget(project_list, 1)

        project_list.customContextMenuRequested.connect(self._on_context_menu)
        project_list.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        self.project_model = project_model
        self.project_list = project_list
        self.sync_server = sync_server
        self.current_project = None
        self.project_name = None
        self.local_site = None
        self.remote_site = None
        self.icons = {}

        self._selection_changed = False
        self._model_reset = False

        timer = QtCore.QTimer()
        timer.setInterval(self.refresh_msec)
        timer.timeout.connect(self.refresh)
        timer.start()

        self.timer = timer

    def _on_selection_changed(self, new_selection, _old_selection):
        # block involuntary selection changes
        if self._selection_changed or self._model_reset:
            return

        indexes = new_selection.indexes()
        if not indexes:
            return

        project_name = indexes[0].data(QtCore.Qt.DisplayRole)

        if self.current_project == project_name:
            return
        self._selection_changed = True
        self.current_project = project_name
        self.project_changed.emit()
        self.refresh()
        self._selection_changed = False

    def refresh(self):
        selected_index = None
        model = self.project_model
        self._model_reset = True
        model.clear()
        self._model_reset = False

        selected_item = None
        sync_settings = self.sync_server.sync_project_settings
        for project_name in sync_settings.keys():
            if self.sync_server.is_paused() or \
               self.sync_server.is_project_paused(project_name):
                icon = self._get_icon("paused")
            elif not sync_settings["enabled"]:
                icon = self._get_icon("disabled")
            else:
                icon = self._get_icon("synced")

            if project_name in self.sync_server.projects_processed:
                icon = self._get_icon("refresh")

            item = QtGui.QStandardItem(icon, project_name)
            model.appendRow(item)

            if self.current_project == project_name:
                selected_item = item

        if selected_item:
            selected_index = model.indexFromItem(selected_item)

        if len(self.sync_server.sync_project_settings.keys()) == 0:
            model.appendRow(QtGui.QStandardItem(lib.DUMMY_PROJECT))

        if not self.current_project:
            self.current_project = model.item(0).data(QtCore.Qt.DisplayRole)

        self.project_model = model

        if selected_index and \
           selected_index.isValid() and \
           not self._selection_changed:
            mode = QtCore.QItemSelectionModel.Select | \
                QtCore.QItemSelectionModel.Rows
            self.project_list.selectionModel().select(selected_index, mode)

        if self.current_project:
            self.local_site = self.sync_server.get_active_site(
                self.current_project)
            self.remote_site = self.sync_server.get_remote_site(
                self.current_project)

    def _can_edit(self):
        """Returns true if some site is user local site, eg. could edit"""
        return get_local_site_id() in (self.local_site, self.remote_site)

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

        menu = QtWidgets.QMenu(self)
        actions_mapping = {}

        if self._can_edit():
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

        if self.project_name not in self.sync_server.projects_processed:
            action = QtWidgets.QAction("Validate files on active site")
            actions_mapping[action] = self._validate_site
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

    def _validate_site(self):
        if self.project_name:
            self.sync_server.create_validate_project_task(self.project_name,
                                                          self.local_site)
            self.project_name = None
        self.refresh()


class _SyncRepresentationWidget(QtWidgets.QWidget):
    """
        Summary dialog with list of representations that matches current
        settings 'local_site' and 'remote_site'.
    """
    active_changed = QtCore.Signal()  # active index changed
    message_generated = QtCore.Signal(str)

    def _selection_changed(self, _new_selected, _all_selected):
        idxs = self.selection_model.selectedRows()
        self._selected_ids = set()

        for index in idxs:
            self._selected_ids.add(self.model.data(index, Qt.UserRole))

    def _set_selection(self):
        """
            Sets selection to 'self._selected_id' if exists.

            Keep selection during model refresh.
        """
        existing_ids = set()
        for selected_id in self._selected_ids:
            index = self.model.get_index(selected_id)
            if index and index.isValid():
                mode = QtCore.QItemSelectionModel.Select | \
                    QtCore.QItemSelectionModel.Rows
                self.selection_model.select(index, mode)
                existing_ids.add(selected_id)

        self._selected_ids = existing_ids

    def _double_clicked(self, index):
        """
            Opens representation dialog with all files after doubleclick
        """
        # priority editing
        if self.model.can_edit:
            column_name = self.model.get_column(index.column())
            if column_name[0] in self.model.EDITABLE_COLUMNS:
                self.model.is_editing = True
                self.table_view.openPersistentEditor(index)
                return

        _id = self.model.data(index, Qt.UserRole)
        detail_window = SyncServerDetailWindow(
            self.sync_server, _id, self.model.project, parent=self)
        detail_window.exec()

    def _on_context_menu(self, point):
        """
            Shows menu with loader actions on Right-click.

            Supports multiple selects - adds all available actions, each
            action handles if it appropriate for item itself, if not it skips.
        """
        is_multi = len(self._selected_ids) > 1
        point_index = self.table_view.indexAt(point)
        if not point_index.isValid() and not is_multi:
            return

        if is_multi:
            index = self.model.get_index(list(self._selected_ids)[0])
            local_progress = self.model.data(index, LOCAL_PROGRESS_ROLE)
            remote_progress = self.model.data(index, REMOTE_PROGRESS_ROLE)
            status = self.model.data(index, STATUS_ROLE)
        else:
            local_progress = self.model.data(point_index, LOCAL_PROGRESS_ROLE)
            remote_progress = self.model.data(point_index,
                                              REMOTE_PROGRESS_ROLE)
            status = self.model.data(point_index, STATUS_ROLE)


        can_edit = self.model.can_edit
        action_kwarg_map, actions_mapping, menu = self._prepare_menu(
            local_progress, remote_progress, is_multi, can_edit, status)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            to_run_kwargs = action_kwarg_map.get(result, {})
            if to_run:
                to_run(**to_run_kwargs)

        self.model.refresh()

    def _prepare_menu(self, local_progress, remote_progress,
                      is_multi, can_edit, status=None):
        menu = QtWidgets.QMenu(self)

        actions_mapping = {}
        action_kwarg_map = {}

        active_site = self.model.active_site
        remote_site = self.model.remote_site

        for site, progress in {active_site: local_progress,
                               remote_site: remote_progress}.items():
            provider = self.sync_server.get_provider_for_site(site=site)
            if provider == 'local_drive':
                if 'studio' in site:
                    txt = " studio version"
                else:
                    txt = " local version"
                action = QtWidgets.QAction("Open in explorer" + txt)
                if progress == 1.0 or is_multi:
                    actions_mapping[action] = self._open_in_explorer
                    action_kwarg_map[action] = \
                        self._get_action_kwargs(site)
                    menu.addAction(action)

        if can_edit and (remote_progress == 1.0 or is_multi):
            action = QtWidgets.QAction("Re-sync Active site")
            action_kwarg_map[action] = self._get_action_kwargs(active_site)
            actions_mapping[action] = self._reset_site
            menu.addAction(action)

        if can_edit and (local_progress == 1.0 or is_multi):
            action = QtWidgets.QAction("Re-sync Remote site")
            action_kwarg_map[action] = self._get_action_kwargs(remote_site)
            actions_mapping[action] = self._reset_site
            menu.addAction(action)

        if can_edit and active_site == get_local_site_id():
            action = QtWidgets.QAction("Completely remove from local")
            action_kwarg_map[action] = self._get_action_kwargs(active_site)
            actions_mapping[action] = self._remove_site
            menu.addAction(action)

        if can_edit:
            action = QtWidgets.QAction("Change priority")
            action_kwarg_map[action] = self._get_action_kwargs(active_site)
            actions_mapping[action] = self._change_priority
            menu.addAction(action)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        return action_kwarg_map, actions_mapping, menu

    def _pause(self, selected_ids=None):
        log.debug("Pause {}".format(selected_ids))
        for representation_id in selected_ids:
            status = lib.get_value_from_id_by_role(self.model,
                                                   representation_id,
                                                   STATUS_ROLE)
            if status not in [lib.STATUS[0], lib.STATUS[1]]:
                continue
            for site_name in [self.model.active_site, self.model.remote_site]:
                check_progress = self._get_progress(self.model,
                                                    representation_id,
                                                    site_name)
                if check_progress < 1:
                    self.sync_server.pause_representation(self.model.project,
                                                          representation_id,
                                                          site_name)

            self.message_generated.emit("Paused {}".format(representation_id))

    def _unpause(self, selected_ids=None):
        log.debug("UnPause {}".format(selected_ids))
        for representation_id in selected_ids:
            status = lib.get_value_from_id_by_role(self.model,
                                                   representation_id,
                                                   STATUS_ROLE)
            if status not in lib.STATUS[3]:
                continue
            for site_name in [self.model.active_site, self.model.remote_site]:
                check_progress = self._get_progress(self.model,
                                                    representation_id,
                                                    site_name)
                if check_progress < 1:
                    self.sync_server.unpause_representation(
                        self.model.project,
                        representation_id,
                        site_name)

            self.message_generated.emit("Unpause {}".format(representation_id))

    # temporary here for testing, will be removed TODO
    def _add_site(self, selected_ids=None, site_name=None):
        log.debug("Add site {}:{}".format(selected_ids, site_name))
        for representation_id in selected_ids:
            item_local_site = lib.get_value_from_id_by_role(
                self.model, representation_id, LOCAL_SITE_NAME_ROLE)
            item_remote_site = lib.get_value_from_id_by_role(
                self.model, representation_id, REMOTE_SITE_NAME_ROLE)
            if site_name in [item_local_site, item_remote_site]:
                # site already exists skip
                continue

            try:
                self.sync_server.add_site(
                    self.model.project,
                    representation_id,
                    site_name)
                self.message_generated.emit(
                    "Site {} added for {}".format(site_name,
                                                  representation_id))
            except ValueError as exp:
                self.message_generated.emit("Error {}".format(str(exp)))
        self.sync_server.reset_timer()

    def _remove_site(self, selected_ids=None, site_name=None):
        """
            Removes site record AND files.

            This is ONLY for representations stored on local site, which
            cannot be same as SyncServer.DEFAULT_SITE.

            This could only happen when artist work on local machine, not
            connected to studio mounted drives.
        """
        log.debug("Remove site {}:{}".format(selected_ids, site_name))
        for representation_id in selected_ids:
            log.info("Removing {}".format(representation_id))
            try:
                self.sync_server.remove_site(
                    self.model.project,
                    representation_id,
                    site_name,
                    True)
                self.message_generated.emit(
                    "Site {} removed".format(site_name))
            except ValueError as exp:
                self.message_generated.emit("Error {}".format(str(exp)))

        self.model.refresh(
            load_records=self.model._rec_loaded)
        self.sync_server.reset_timer()

    def _reset_site(self, selected_ids=None, site_name=None):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        log.debug("Reset site {}:{}".format(selected_ids, site_name))
        for representation_id in selected_ids:
            check_progress = self._get_progress(self.model, representation_id,
                                                site_name, True)

            # do not reset if opposite side is not fully there
            if check_progress != 1:
                log.debug("Not fully available {} on other side, skipping".
                          format(check_progress))
                continue

            self.sync_server.reset_site_on_representation(
                self.model.project,
                representation_id,
                site_name=site_name,
                force=True)

        self.model.refresh(
            load_records=self.model._rec_loaded)
        self.sync_server.reset_timer()

    def _open_in_explorer(self, selected_ids=None, site_name=None):
        log.debug("Open in Explorer {}:{}".format(selected_ids, site_name))
        for selected_id in selected_ids:
            fpath = lib.get_value_from_id_by_role(self.model, selected_id,
                                                  PATH_ROLE)
            project = self.model.project
            fpath = self.sync_server.get_local_file_path(project,
                                                         site_name,
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

    def _change_priority(self, **kwargs):
        """Open editor to change priority on first selected row"""
        if self._selected_ids:
            # get_index returns dummy index with column equals to 0
            index = self.model.get_index(list(self._selected_ids)[0])
            column_no = self.model.get_header_index("priority")  # real column
            real_index = self.model.index(index.row(), column_no)
            self.model.is_editing = True
            self.table_view.openPersistentEditor(real_index)

    def _get_progress(self, model, representation_id,
                      site_name, opposite=False):
        """Returns progress value according to site (side)"""
        local_progress = lib.get_value_from_id_by_role(model,
                                                       representation_id,
                                                       LOCAL_PROGRESS_ROLE)
        remote_progress = lib.get_value_from_id_by_role(model,
                                                        representation_id,
                                                        REMOTE_PROGRESS_ROLE)
        progress = {'local': local_progress,
                    'remote': remote_progress}
        side = 'remote'
        if site_name == self.model.active_site:
            side = 'local'
        if opposite:
            side = 'remote' if side == 'local' else 'local'

        return progress[side]

    def _get_action_kwargs(self, site_name):
        """Default format of kwargs for action"""
        return {"selected_ids": self._selected_ids, "site_name": site_name}

    def _save_scrollbar(self):
        self._scrollbar_pos = self.table_view.verticalScrollBar().value()

    def _set_scrollbar(self):
        if self._scrollbar_pos:
            self.table_view.verticalScrollBar().setValue(self._scrollbar_pos)


class SyncRepresentationSummaryWidget(_SyncRepresentationWidget):

    default_widths = (
        ("asset", 190),
        ("subset", 170),
        ("version", 60),
        ("representation", 145),
        ("local_site", 160),
        ("remote_site", 160),
        ("files_count", 50),
        ("files_size", 60),
        ("priority", 70),
        ("status", 110)
    )

    def __init__(self, sync_server, project=None, parent=None):
        import time
        log.info("SyncRepresentationSummaryWidget start")
        super(SyncRepresentationSummaryWidget, self).__init__(parent)

        self.sync_server = sync_server
        self._selected_ids = set()  # keep last selected _id

        txt_filter = QtWidgets.QLineEdit()
        txt_filter.setPlaceholderText("Quick filter representations..")
        txt_filter.setClearButtonEnabled(True)
        txt_filter.addAction(
            qtawesome.icon("fa.filter", color="gray"),
            QtWidgets.QLineEdit.LeadingPosition)
        self.txt_filter = txt_filter

        self._scrollbar_pos = None

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(self.txt_filter)

        table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]

        start_time = time.time()
        model = SyncRepresentationSummaryModel(sync_server, headers, project,
                                               parent=self)
        log.info("SyncRepresentationSummaryModel:: {}".format(time.time() - start_time))
        start_time = time.time()
        table_view.setModel(model)
        table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        table_view.horizontalHeader().setSortIndicator(
            -1, Qt.AscendingOrder)
        table_view.setAlternatingRowColors(True)
        table_view.verticalHeader().hide()
        table_view.viewport().setAttribute(QtCore.Qt.WA_Hover, True)

        column = table_view.model().get_header_index("local_site")
        delegate = delegates.ImageDelegate(self, side="local")
        table_view.setItemDelegateForColumn(column, delegate)

        column = table_view.model().get_header_index("remote_site")
        delegate = delegates.ImageDelegate(self, side="remote")
        table_view.setItemDelegateForColumn(column, delegate)

        column = table_view.model().get_header_index("priority")
        priority_delegate = delegates.PriorityDelegate(self)
        table_view.setItemDelegateForColumn(column, priority_delegate)
        log.info("SyncRepresentationSummaryWidget.2:: {}".format(time.time() - start_time))
        start_time = time.time()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(table_view)

        self.table_view = table_view
        self.model = model
        log.info("SyncRepresentationSummaryWidget.3:: {}".format(time.time() - start_time))
        start_time = time.time()
        horizontal_header = HorizontalHeader(self)
        log.info("SyncRepresentationSummaryWidget.4:: {}".format(time.time() - start_time))
        start_time = time.time()
        table_view.setHorizontalHeader(horizontal_header)
        log.info("SyncRepresentationSummaryWidget.4.1:: {}".format(time.time() - start_time))
        start_time = time.time()
        table_view.setSortingEnabled(True)
        log.info("SyncRepresentationSummaryWidget.5:: {}".format(time.time() - start_time))
        start_time = time.time()
        for column_name, width in self.default_widths:
            idx = model.get_header_index(column_name)
            table_view.setColumnWidth(idx, width)
        log.info("SyncRepresentationSummaryWidget.6:: {}".format(time.time() - start_time))
        start_time = time.time()
        table_view.doubleClicked.connect(self._double_clicked)
        self.txt_filter.textChanged.connect(lambda: model.set_word_filter(
            self.txt_filter.text()))
        table_view.customContextMenuRequested.connect(self._on_context_menu)
        log.info("SyncRepresentationSummaryWidget.7:: {}".format(time.time() - start_time))
        start_time = time.time()
        model.refresh_started.connect(self._save_scrollbar)
        model.refresh_finished.connect(self._set_scrollbar)
        model.modelReset.connect(self._set_selection)

        self.selection_model = self.table_view.selectionModel()
        self.selection_model.selectionChanged.connect(self._selection_changed)
        log.info("SyncRepresentationSummaryWidget.end:: {}".format(time.time() - start_time))

    def _prepare_menu(self, local_progress, remote_progress,
                      is_multi, can_edit, status=None):
        action_kwarg_map, actions_mapping, menu = \
            super()._prepare_menu(local_progress, remote_progress,
                                  is_multi, can_edit)

        if can_edit and (
                status in [lib.STATUS[0], lib.STATUS[1]] or is_multi):
            action = QtWidgets.QAction("Pause in queue")
            actions_mapping[action] = self._pause
            # pause handles which site_name it will pause itself
            action_kwarg_map[action] = {"selected_ids": self._selected_ids}
            menu.addAction(action)

        if can_edit and (status == lib.STATUS[3] or is_multi):
            action = QtWidgets.QAction("Unpause  in queue")
            actions_mapping[action] = self._unpause
            action_kwarg_map[action] = {"selected_ids": self._selected_ids}
            menu.addAction(action)

        return action_kwarg_map, actions_mapping, menu


class SyncServerDetailWindow(QtWidgets.QDialog):
    """Wrapper window for SyncRepresentationDetailWidget

        Creates standalone window with list of files for selected repre_id.
    """
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

        self.setWindowTitle("Sync Representation Detail")


class SyncRepresentationDetailWidget(_SyncRepresentationWidget):
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
        ("local_site", 185),
        ("remote_site", 185),
        ("size", 60),
        ("priority", 60),
        ("status", 110)
    )

    def __init__(self, sync_server, _id=None, project=None, parent=None):
        super(SyncRepresentationDetailWidget, self).__init__(parent)

        log.debug("Representation_id:{}".format(_id))
        self.project = project

        self.sync_server = sync_server

        self.representation_id = _id
        self._selected_ids = set()

        self.txt_filter = QtWidgets.QLineEdit()
        self.txt_filter.setPlaceholderText("Quick filter representation..")
        self.txt_filter.setClearButtonEnabled(True)
        self.txt_filter.addAction(qtawesome.icon("fa.filter", color="gray"),
                                  QtWidgets.QLineEdit.LeadingPosition)

        self._scrollbar_pos = None

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(self.txt_filter)

        table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]

        model = SyncRepresentationDetailModel(sync_server, headers, _id,
                                              project)
        model.is_running = True

        table_view.setModel(model)
        table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        table_view.setSelectionBehavior(
            QtWidgets.QTableView.SelectRows)
        table_view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        table_view.horizontalHeader().setSortIndicatorShown(True)
        table_view.setAlternatingRowColors(True)
        table_view.verticalHeader().hide()

        column = model.get_header_index("local_site")
        delegate = delegates.ImageDelegate(self, side="local")
        table_view.setItemDelegateForColumn(column, delegate)

        column = model.get_header_index("remote_site")
        delegate = delegates.ImageDelegate(self, side="remote")
        table_view.setItemDelegateForColumn(column, delegate)

        if model.can_edit:
            column = table_view.model().get_header_index("priority")
            priority_delegate = delegates.PriorityDelegate(self)
            table_view.setItemDelegateForColumn(column, priority_delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(table_view)

        self.model = model

        self.selection_model = table_view.selectionModel()
        self.selection_model.selectionChanged.connect(self._selection_changed)

        horizontal_header = HorizontalHeader(self)

        table_view.setHorizontalHeader(horizontal_header)
        table_view.setSortingEnabled(True)

        for column_name, width in self.default_widths:
            idx = model.get_header_index(column_name)
            table_view.setColumnWidth(idx, width)

        self.table_view = table_view

        self.txt_filter.textChanged.connect(lambda: model.set_word_filter(
            self.txt_filter.text()))
        table_view.doubleClicked.connect(self._double_clicked)
        table_view.customContextMenuRequested.connect(self._on_context_menu)

        model.refresh_started.connect(self._save_scrollbar)
        model.refresh_finished.connect(self._set_scrollbar)
        model.modelReset.connect(self._set_selection)

    def _double_clicked(self, index):
        """
            Opens representation dialog with all files after doubleclick
        """
        # priority editing
        if self.model.can_edit:
            column_name = self.model.get_column(index.column())
            if column_name[0] in self.model.EDITABLE_COLUMNS:
                self.model.is_editing = True
                self.table_view.openPersistentEditor(index)
                return

    def _show_detail(self, selected_ids=None):
        """
            Shows windows with error message for failed sync of a file.
        """
        detail_window = SyncRepresentationErrorWindow(self.model, selected_ids)

        detail_window.exec()

    def _prepare_menu(self, local_progress, remote_progress,
                      is_multi, can_edit, status=None):
        """Adds view (and model) dependent actions to default ones"""
        action_kwarg_map, actions_mapping, menu = \
            super()._prepare_menu(local_progress, remote_progress,
                                  is_multi, can_edit, status)

        if status == lib.STATUS[2] or is_multi:
            action = QtWidgets.QAction("Open error detail")
            actions_mapping[action] = self._show_detail
            action_kwarg_map[action] = {"selected_ids": self._selected_ids}

            menu.addAction(action)

        return action_kwarg_map, actions_mapping, menu

    def _reset_site(self, selected_ids=None, site_name=None):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        for file_id in selected_ids:
            check_progress = self._get_progress(self.model, file_id,
                                                site_name, True)

            # do not reset if opposite side is not fully there
            if check_progress != 1:
                log.debug("Not fully available {} on other side, skipping".
                          format(check_progress))
                continue

            self.sync_server.reset_site_on_representation(
                self.model.project,
                self.representation_id,
                site_name=site_name,
                file_id=file_id,
                force=True)
        self.model.refresh(
            load_records=self.model._rec_loaded)


class SyncRepresentationErrorWindow(QtWidgets.QDialog):
    """Wrapper window to show errors during sync on file(s)"""
    def __init__(self, model, selected_ids, parent=None):
        super(SyncRepresentationErrorWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
        self.resize(900, 150)

        body = QtWidgets.QWidget()

        container = SyncRepresentationErrorWidget(model,
                                                  selected_ids,
                                                  parent=self)
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.addWidget(container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        message = QtWidgets.QLabel()
        message.hide()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)

        self.setLayout(body_layout)
        self.setWindowTitle("Sync Representation Error Detail")


class SyncRepresentationErrorWidget(QtWidgets.QWidget):
    """
        Dialog to show when sync error happened, prints formatted error message
    """
    def __init__(self, model, selected_ids, parent=None):
        super(SyncRepresentationErrorWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)

        no_errors = True
        for file_id in selected_ids:
            created_dt = lib.get_value_from_id_by_role(model, file_id,
                                                       LOCAL_DATE_ROLE)
            sync_dt = lib.get_value_from_id_by_role(model, file_id,
                                                    REMOTE_DATE_ROLE)
            errors = lib.get_value_from_id_by_role(model, file_id,
                                                   ERROR_ROLE)
            if not created_dt or not sync_dt or not errors:
                continue

            tries = lib.get_value_from_id_by_role(model, file_id,
                                                  TRIES_ROLE)

            no_errors = False
            dt = max(created_dt, sync_dt)

            txts = []
            txts.append("{}: {}<br>".format("<b>Last update date</b>",
                                            pretty_timestamp(dt)))
            txts.append("{}: {}<br>".format("<b>Retries</b>",
                                            str(tries)))
            txts.append("{}: {}<br>".format("<b>Error message</b>",
                                            errors))

            text_area = QtWidgets.QTextEdit("\n\n".join(txts))
            text_area.setReadOnly(True)
            layout.addWidget(text_area)

        if no_errors:
            text_area = QtWidgets.QTextEdit()
            text_area.setText("<h4>No errors located</h4>")
            text_area.setReadOnly(True)
            layout.addWidget(text_area)


class HorizontalHeader(QtWidgets.QHeaderView):
    """Reiplemented QHeaderView to contain clickable changeable button"""
    def __init__(self, parent=None):
        super(HorizontalHeader, self).__init__(QtCore.Qt.Horizontal, parent)
        self._parent = parent
        self.checked_values = {}
        self.setModel(self._parent.model)

        self.setSectionsClickable(True)

        self.menu_items_dict = {}
        self.menu = None
        self.header_cells = []
        self.filter_buttons = {}

        self.filter_icon = qtawesome.icon("fa.filter", color="gray")
        self.filter_set_icon = qtawesome.icon("fa.filter", color="white")

        self.init_layout()

        self._resetting = False

    @property
    def model(self):
        """Keep model synchronized with parent widget"""
        return self._parent.model

    def init_layout(self):
        """Initial preparation of header's content"""
        for column_idx in range(self.model.columnCount()):
            column_name, column_label = self.model.get_column(column_idx)
            filter_rec = self.model.get_filters().get(column_name)
            if not filter_rec:
                continue

            icon = self.filter_icon
            button = QtWidgets.QPushButton(icon, "", self)

            button.setFixedSize(24, 24)
            button.setStyleSheet(
                "QPushButton::menu-indicator{width:0px;}"
                "QPushButton{border: none;background: transparent;}")
            button.clicked.connect(partial(self._get_menu,
                                           column_name, column_idx))
            button.setFlat(True)
            self.filter_buttons[column_name] = button

    def showEvent(self, event):
        """Paint header"""
        super(HorizontalHeader, self).showEvent(event)

        for i in range(len(self.header_cells)):
            cell_content = self.header_cells[i]
            cell_content.setGeometry(self.sectionViewportPosition(i), 0,
                                     self.sectionSize(i) - 1, self.height())

            cell_content.show()

    def _set_filter_icon(self, column_name):
        """Set different states of button depending on its engagement"""
        button = self.filter_buttons.get(column_name)
        if button:
            if self.checked_values.get(column_name):
                button.setIcon(self.filter_set_icon)
            else:
                button.setIcon(self.filter_icon)

    def _reset_filter(self, column_name):
        """
            Remove whole column from filter >> not in $match at all (faster)
        """
        self._resetting = True  # mark changes to consume them
        if self.checked_values.get(column_name) is not None:
            self.checked_values.pop(column_name)
            self._set_filter_icon(column_name)
        self._filter_and_refresh_model_and_menu(column_name, True, True)
        self._resetting = False

    def _apply_filter(self, column_name, values, state):
        """
            Sets 'values' to specific 'state' (checked/unchecked),
            sends to model.
        """
        if self._resetting:  # event triggered by _resetting, skip it
            return

        self._update_checked_values(column_name, values, state)
        self._set_filter_icon(column_name)
        self._filter_and_refresh_model_and_menu(column_name, True, False)

    def _apply_text_filter(self, column_name, items, line_edit):
        """
            Resets all checkboxes, prefers inserted text.
        """
        le_text = line_edit.text()
        self._update_checked_values(column_name, items, 0)  # reset other
        if self.checked_values.get(column_name) is not None or \
                le_text == '':
            self.checked_values.pop(column_name)  # reset during typing

        if le_text:
            self._update_checked_values(column_name, {le_text: le_text}, 2)
        self._set_filter_icon(column_name)
        self._filter_and_refresh_model_and_menu(column_name, True, True)

    def _filter_and_refresh_model_and_menu(self, column_name,
                                           model=True, menu=True):
        """
            Refresh model and its content and possibly menu for big changes.
        """
        if model:
            self.model.set_column_filtering(self.checked_values)
            self.model.refresh()
        if menu:
            self._menu_refresh(column_name)

    def _get_menu(self, column_name, index):
        """Prepares content of menu for 'column_name'"""
        menu = QtWidgets.QMenu(self)
        filter_rec = self.model.get_filters()[column_name]
        self.menu_items_dict[column_name] = filter_rec.values()

        # text filtering only if labels same as values, not if codes are used
        if 'text' in filter_rec.search_variants():
            line_edit = QtWidgets.QLineEdit(menu)
            line_edit.setClearButtonEnabled(True)
            line_edit.addAction(self.filter_icon,
                                QtWidgets.QLineEdit.LeadingPosition)

            line_edit.setFixedHeight(line_edit.height())
            txt = ""
            if self.checked_values.get(column_name):
                txt = list(self.checked_values.get(column_name).keys())[0]
            line_edit.setText(txt)

            action_le = QtWidgets.QWidgetAction(menu)
            action_le.setDefaultWidget(line_edit)
            line_edit.textChanged.connect(
                partial(self._apply_text_filter, column_name,
                        filter_rec.values(), line_edit))
            menu.addAction(action_le)
            menu.addSeparator()

        if 'checkbox' in filter_rec.search_variants():
            action_all = QtWidgets.QAction("All", self)
            action_all.triggered.connect(partial(self._reset_filter,
                                                 column_name))
            menu.addAction(action_all)

            action_none = QtWidgets.QAction("Unselect all", self)
            state_unchecked = 0
            action_none.triggered.connect(partial(self._apply_filter,
                                                  column_name,
                                                  filter_rec.values(),
                                                  state_unchecked))
            menu.addAction(action_none)
            menu.addSeparator()

        # nothing explicitly >> ALL implicitly >> first time
        if self.checked_values.get(column_name) is None:
            checked_keys = self.menu_items_dict[column_name].keys()
        else:
            checked_keys = self.checked_values[column_name]

        for value, label in self.menu_items_dict[column_name].items():
            checkbox = QtWidgets.QCheckBox(str(label), menu)

            # temp
            checkbox.setStyleSheet("QCheckBox{spacing: 5px;"
                                   "padding:5px 5px 5px 5px;}")
            if value in checked_keys:
                checkbox.setChecked(True)

            action = QtWidgets.QWidgetAction(menu)
            action.setDefaultWidget(checkbox)

            checkbox.stateChanged.connect(partial(self._apply_filter,
                                                  column_name, {value: label}))
            menu.addAction(action)

        self.menu = menu

        self._show_menu(index, menu)

    def _show_menu(self, index, menu):
        """Shows 'menu' under header column of 'index'"""
        global_pos_point = self.mapToGlobal(
            QtCore.QPoint(self.sectionViewportPosition(index), 0))
        menu.setMinimumWidth(self.sectionSize(index))
        menu.setMinimumHeight(self.height())
        menu.exec_(QtCore.QPoint(global_pos_point.x(),
                                 global_pos_point.y() + self.height()))

    def _menu_refresh(self, column_name):
        """
            Reset boxes after big change - word filtering or reset
        """
        for action in self.menu.actions():
            if not isinstance(action, QtWidgets.QWidgetAction):
                continue

            widget = action.defaultWidget()
            if not isinstance(widget, QtWidgets.QCheckBox):
                continue

            if not self.checked_values.get(column_name) or \
                    widget.text() in self.checked_values[column_name].values():
                widget.setChecked(True)
            else:
                widget.setChecked(False)

    def _update_checked_values(self, column_name, values, state):
        """
            Modify dictionary of set values in columns for filtering.

            Modifies 'self.checked_values'
        """
        copy_menu_items = dict(self.menu_items_dict[column_name])
        checked = self.checked_values.get(column_name, copy_menu_items)
        set_items = dict(values.items())  # prevent dict change during loop
        for value, label in set_items.items():
            if state == 2 and label:  # checked
                checked[value] = label
            elif state == 0 and checked.get(value):
                checked.pop(value)

        self.checked_values[column_name] = checked

    def paintEvent(self, event):
        self._fix_size()
        super(HorizontalHeader, self).paintEvent(event)

    def _fix_size(self):
        for column_idx in range(self.model.columnCount()):
            vis_index = self.visualIndex(column_idx)
            index = self.logicalIndex(vis_index)
            section_width = self.sectionSize(index)

            column_name = self.model.headerData(column_idx,
                                                QtCore.Qt.Horizontal,
                                                HEADER_NAME_ROLE)
            button = self.filter_buttons.get(column_name)
            if not button:
                continue

            pos_x = self.sectionViewportPosition(
                index) + section_width - self.height()

            pos_y = 0
            if button.height() < self.height():
                pos_y = int((self.height() - button.height()) / 2)
            button.setGeometry(
                pos_x,
                pos_y,
                self.height(),
                self.height())
