import os
import subprocess
import sys

from Qt import QtWidgets, QtCore, QtGui
from Qt.QtCore import Qt

from openpype.tools.settings import (
    ProjectListWidget,
    style
)

from openpype.api import get_local_site_id
from openpype.lib import PypeLogger

from avalon.tools.delegates import pretty_timestamp

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
        menu.setStyleSheet(style.load_stylesheet())
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
        ("asset", 220),
        ("subset", 190),
        ("version", 55),
        ("representation", 95),
        ("local_site", 170),
        ("remote_site", 170),
        ("files_count", 50),
        ("files_size", 60),
        ("priority", 50),
        ("state", 110)
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
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSortIndicatorShown(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().hide()

        column = self.table_view.model().get_header_index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("remote_site")
        delegate = ImageDelegate(self)
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

    def _selection_changed(self, _new_selection):
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
        menu.setStyleSheet(style.load_stylesheet())
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

        if self.item.state in [lib.STATUS[0], lib.STATUS[1]]:
            action = QtWidgets.QAction("Pause")
            actions_mapping[action] = self._pause
            menu.addAction(action)

        if self.item.state == lib.STATUS[3]:
            action = QtWidgets.QAction("Unpause")
            actions_mapping[action] = self._unpause
            menu.addAction(action)

        # if self.item.state == lib.STATUS[1]:
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
                True)
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
            'local')
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
            'remote')
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
        ("priority", 25),
        ("state", 110)
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

        model = SyncRepresentationDetailModel(sync_server, headers, _id,
                                              project)
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

        column = self.table_view.model().get_header_index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model().get_header_index("remote_site")
        delegate = ImageDelegate(self)
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
        menu.setStyleSheet(style.load_stylesheet())
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

        if self.item.state == lib.STATUS[2]:
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


class SyncRepresentationErrorWidget(QtWidgets.QWidget):
    """
        Dialog to show when sync error happened, prints error message
    """

    def __init__(self, _id, dt, tries, msg, parent=None):
        super(SyncRepresentationErrorWidget, self).__init__(parent)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow(QtWidgets.QLabel("Last update date"),
                      QtWidgets.QLabel(pretty_timestamp(dt)))
        layout.addRow(QtWidgets.QLabel("Retries"),
                      QtWidgets.QLabel(str(tries)))
        layout.addRow(QtWidgets.QLabel("Error message"),
                      QtWidgets.QLabel(msg))


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
        self.resize(250, 200)

        body = QtWidgets.QWidget()
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(20)

        container = SyncRepresentationErrorWidget(_id, dt, tries, msg,
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
