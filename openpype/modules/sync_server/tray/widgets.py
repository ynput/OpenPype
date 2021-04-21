import os
import subprocess
import sys
from functools import partial

from Qt import QtWidgets, QtCore, QtGui
from Qt.QtCore import Qt

from openpype.tools.settings import (
    ProjectListWidget,
    style
)

from openpype.api import get_local_site_id
from openpype.lib import PypeLogger

from avalon.tools.delegates import pretty_timestamp
from avalon.vendor import qtawesome

from openpype.modules.sync_server.tray.models import (
    SyncRepresentationSummaryModel,
    SyncRepresentationDetailModel
)

from openpype.modules.sync_server.tray import lib

log = PypeLogger().get_logger("SyncServer")


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

        self.layout().setContentsMargins(0, 0, 0, 0)

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
            model.appendRow(QtGui.QStandardItem(lib.DUMMY_PROJECT))

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
        #menu.setStyleSheet(style.load_stylesheet())
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


class SyncRepresentationWidget(QtWidgets.QWidget):
    """
        Summary dialog with list of representations that matches current
        settings 'local_site' and 'remote_site'.
    """
    active_changed = QtCore.Signal()  # active index changed
    message_generated = QtCore.Signal(str)

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

        model = SyncRepresentationSummaryModel(sync_server, headers, project)
        self.table_view.setModel(model)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.horizontalHeader().setSortIndicator(
            -1, Qt.AscendingOrder)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().hide()

        column = self.table_view.model().get_header_index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("remote_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(self.table_view)

        self.table_view.doubleClicked.connect(self._double_clicked)
        self.filter.textChanged.connect(lambda: model.set_word_filter(
            self.filter.text()))
        self.table_view.customContextMenuRequested.connect(
            self._on_context_menu)

        model.refresh_started.connect(self._save_scrollbar)
        model.refresh_finished.connect(self._set_scrollbar)
        model.modelReset.connect(self._set_selection)

        self.model = model

        self.selection_model = self.table_view.selectionModel()
        self.selection_model.selectionChanged.connect(self._selection_changed)

        horizontal_header = HorizontalHeader(self)

        self.table_view.setHorizontalHeader(horizontal_header)
        self.table_view.setSortingEnabled(True)

        for column_name, width in self.default_widths:
            idx = model.get_header_index(column_name)
            self.table_view.setColumnWidth(idx, width)

    def _selection_changed(self, _new_selection):
        index = self.selection_model.currentIndex()
        self._selected_id = \
            self.model.data(index, Qt.UserRole)

    def _set_selection(self):
        """
            Sets selection to 'self._selected_id' if exists.

            Keep selection during model refresh.
        """
        if self._selected_id:
            index = self.model.get_index(self._selected_id)
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
        _id = self.model.data(index, Qt.UserRole)
        detail_window = SyncServerDetailWindow(
            self.sync_server, _id, self.model.project)
        detail_window.exec()

    def _on_context_menu(self, point):
        """
            Shows menu with loader actions on Right-click.
        """
        point_index = self.table_view.indexAt(point)
        if not point_index.isValid():
            return

        self.item = self.model._data[point_index.row()]
        self.representation_id = self.item._id
        log.debug("menu representation _id:: {}".
                  format(self.representation_id))

        menu = QtWidgets.QMenu()
        menu.setStyleSheet(style.load_stylesheet())
        actions_mapping = {}
        actions_kwargs_mapping = {}

        local_site = self.item.local_site
        local_progress = self.item.local_progress
        remote_site = self.item.remote_site
        remote_progress = self.item.remote_progress

        for site, progress in {local_site: local_progress,
                               remote_site: remote_progress}.items():
            project = self.model.project
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

        if self.item.status in [lib.STATUS[0], lib.STATUS[1]]:
            action = QtWidgets.QAction("Pause")
            actions_mapping[action] = self._pause
            menu.addAction(action)

        if self.item.status == lib.STATUS[3]:
            action = QtWidgets.QAction("Unpause")
            actions_mapping[action] = self._unpause
            menu.addAction(action)

        # if self.item.status == lib.STATUS[1]:
        #     action = QtWidgets.QAction("Open error detail")
        #     actions_mapping[action] = self._show_detail
        #     menu.addAction(action)

        if remote_progress == 1.0:
            action = QtWidgets.QAction("Re-sync Active site")
            actions_mapping[action] = self._reset_local_site
            menu.addAction(action)

        if local_progress == 1.0:
            action = QtWidgets.QAction("Re-sync Remote site")
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

        self.model.refresh()

    def _pause(self):
        self.sync_server.pause_representation(self.model.project,
                                              self.representation_id,
                                              self.site_name)
        self.site_name = None
        self.message_generated.emit("Paused {}".format(self.representation_id))

    def _unpause(self):
        self.sync_server.unpause_representation(
            self.model.project,
            self.representation_id,
            self.site_name)
        self.site_name = None
        self.message_generated.emit("Unpaused {}".format(
            self.representation_id))

    # temporary here for testing, will be removed TODO
    def _add_site(self):
        log.info(self.representation_id)
        project_name = self.model.project
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
                self.model.project,
                self.representation_id,
                local_site,
                True)
            self.message_generated.emit("Site {} removed".format(local_site))
        except ValueError as exp:
            self.message_generated.emit("Error {}".format(str(exp)))
        self.model.refresh(
            load_records=self.model._rec_loaded)

    def _reset_local_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.model.project,
            self.representation_id,
            'local')
        self.model.refresh(
            load_records=self.model._rec_loaded)

    def _reset_remote_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.model.project,
            self.representation_id,
            'remote')
        self.model.refresh(
            load_records=self.model._rec_loaded)

    def _open_in_explorer(self, site):
        if not self.item:
            return

        fpath = self.item.path
        project = self.model.project
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
        ("local_site", 185),
        ("remote_site", 185),
        ("size", 60),
        ("priority", 60),
        ("status", 110)
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

        table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]

        model = SyncRepresentationDetailModel(sync_server, headers, _id,
                                              project)
        table_view.setModel(model)
        table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        table_view.setSelectionBehavior(
            QtWidgets.QTableView.SelectRows)
        table_view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        table_view.horizontalHeader().setSortIndicatorShown(True)
        table_view.setAlternatingRowColors(True)
        table_view.verticalHeader().hide()

        column = model.get_header_index("local_site")
        delegate = ImageDelegate(self)
        table_view.setItemDelegateForColumn(column, delegate)

        column = model.get_header_index("remote_site")
        delegate = ImageDelegate(self)
        table_view.setItemDelegateForColumn(column, delegate)

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

        self.filter.textChanged.connect(lambda: model.set_word_filter(
            self.filter.text()))
        table_view.customContextMenuRequested.connect(self._on_context_menu)

        model.refresh_started.connect(self._save_scrollbar)
        model.refresh_finished.connect(self._set_scrollbar)
        model.modelReset.connect(self._set_selection)

    def _selection_changed(self):
        index = self.selection_model.currentIndex()
        self._selected_id = self.model.data(index, Qt.UserRole)

    def _set_selection(self):
        """
            Sets selection to 'self._selected_id' if exists.

            Keep selection during model refresh.
        """
        if self._selected_id:
            index = self.model.get_index(self._selected_id)
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

        self.item = self.model._data[point_index.row()]

        menu = QtWidgets.QMenu()
        #menu.setStyleSheet(style.load_stylesheet())
        actions_mapping = {}
        actions_kwargs_mapping = {}

        local_site = self.item.local_site
        local_progress = self.item.local_progress
        remote_site = self.item.remote_site
        remote_progress = self.item.remote_progress

        for site, progress in {local_site: local_progress,
                               remote_site: remote_progress}.items():
            project = self.model.project
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

        if self.item.status == lib.STATUS[2]:
            action = QtWidgets.QAction("Open error detail")
            actions_mapping[action] = self._show_detail
            menu.addAction(action)

        if float(remote_progress) == 1.0:
            action = QtWidgets.QAction("Re-sync active site")
            actions_mapping[action] = self._reset_local_site
            menu.addAction(action)

        if float(local_progress) == 1.0:
            action = QtWidgets.QAction("Re-sync remote site")
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
            self.model.project,
            self.representation_id,
            'local',
            self.item._id)
        self.model.refresh(
            load_records=self.model._rec_loaded)

    def _reset_remote_site(self):
        """
            Removes errors or success metadata for particular file >> forces
            redo of upload/download
        """
        self.sync_server.reset_provider_for_file(
            self.model.project,
            self.representation_id,
            'remote',
            self.item._id)
        self.model.refresh(
            load_records=self.model._rec_loaded)

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


class SyncRepresentationErrorWidget(QtWidgets.QWidget):
    """
        Dialog to show when sync error happened, prints error message
    """

    def __init__(self, _id, dt, tries, msg, parent=None):
        super(SyncRepresentationErrorWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)

        txts = []
        txts.append("{}: {}".format("Last update date", pretty_timestamp(dt)))
        txts.append("{}: {}".format("Retries", str(tries)))
        txts.append("{}: {}".format("Error message", msg))

        text_area = QtWidgets.QPlainTextEdit("\n\n".join(txts))
        text_area.setReadOnly(True)
        layout.addWidget(text_area)


class ImageDelegate(QtWidgets.QStyledItemDelegate):
    """
        Prints icon of site and progress of synchronization
    """

    def __init__(self, parent=None):
        super(ImageDelegate, self).__init__(parent)
        self.icons = {}

    def paint(self, painter, option, index):
        super(ImageDelegate, self).paint(painter, option, index)
        option = QtWidgets.QStyleOptionViewItem(option)
        option.showDecorationSelected = True

        provider = index.data(lib.ProviderRole)
        value = index.data(lib.ProgressRole)
        date_value = index.data(lib.DateRole)
        is_failed = index.data(lib.FailedRole)

        if not self.icons.get(provider):
            resource_path = os.path.dirname(__file__)
            resource_path = os.path.join(resource_path, "..",
                                         "providers", "resources")
            pix_url = "{}/{}.png".format(resource_path, provider)
            pixmap = QtGui.QPixmap(pix_url)
            self.icons[provider] = pixmap
        else:
            pixmap = self.icons[provider]

        padding = 10
        point = QtCore.QPoint(option.rect.x() + padding,
                              option.rect.y() +
                              (option.rect.height() - pixmap.height()) / 2)
        painter.drawPixmap(point, pixmap)

        overlay_rect = option.rect.translated(0, 0)
        overlay_rect.setHeight(overlay_rect.height() * (1.0 - float(value)))
        painter.fillRect(overlay_rect,
                         QtGui.QBrush(QtGui.QColor(0, 0, 0, 100)))
        text_rect = option.rect.translated(10, 0)
        painter.drawText(text_rect,
                         QtCore.Qt.AlignCenter,
                         date_value)

        if is_failed:
            overlay_rect = option.rect.translated(0, 0)
            painter.fillRect(overlay_rect,
                             QtGui.QBrush(QtGui.QColor(255, 0, 0, 35)))


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


class SyncRepresentationErrorWindow(QtWidgets.QDialog):
    def __init__(self, _id, project, dt, tries, msg, parent=None):
        super(SyncRepresentationErrorWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
        self.resize(900, 150)

        body = QtWidgets.QWidget()

        container = SyncRepresentationErrorWidget(_id, dt, tries, msg,
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


class TransparentWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal(str)

    def __init__(self, column_name, *args, **kwargs):
        super(TransparentWidget, self).__init__(*args, **kwargs)
        self.column_name = column_name
        # self.setStyleSheet("background: red;")

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.column_name)

        super(TransparentWidget, self).mouseReleaseEvent(event)


class HorizontalHeader(QtWidgets.QHeaderView):

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
        for column_idx in range(self.model.columnCount()):
            column_name, column_label = self.model.get_column(column_idx)
            filter_rec = self.model.get_filters().get(column_name)
            if not filter_rec:
                continue

            icon = self.filter_icon
            button = QtWidgets.QPushButton(icon, "", self)

            button.setFixedSize(24, 24)
            button.setStyleSheet("QPushButton::menu-indicator{width:0px;}"
                "QPushButton{border: none;background: transparent;}")
            button.clicked.connect(partial(self._get_menu,
                                           column_name, column_idx))
            button.setFlat(True)
            self.filter_buttons[column_name] = button

    def showEvent(self, event):
        super(HorizontalHeader, self).showEvent(event)

        for i in range(len(self.header_cells)):
            cell_content = self.header_cells[i]
            cell_content.setGeometry(self.sectionViewportPosition(i), 0,
                                     self.sectionSize(i)-1, self.height())

            cell_content.show()

    def _set_filter_icon(self, column_name):
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
            txt = "Type..."
            if self.checked_values.get(column_name):
                txt = list(self.checked_values.get(column_name).keys())[0]
            line_edit.setPlaceholderText(txt)

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
        checked = self.checked_values.get(column_name,
            dict(self.menu_items_dict[column_name]))
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
                                                lib.HeaderNameRole)
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

