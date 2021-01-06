import sys

sys.path.append(
    'c:\\Users\\petrk\\PycharmProjects\\Pype3.0\\pype\\repos\\pyblish-base')

from Qt import QtWidgets, QtCore, QtGui
from Qt.QtCore import Qt
from avalon import style
from avalon.api import AvalonMongoDB
from pype.tools.settings.settings.widgets.base import ProjectListWidget
from pype.modules import ModulesManager
import attr
import os
from pype.tools.settings.settings import style
from avalon.tools.delegates import PrettyTimeDelegate

from pype.lib import PypeLogger

import json

log = PypeLogger().get_logger("SyncServer")

STATUS = {
    0: 'Queued',
    1: 'Failed',
    2: 'In Progress',
    3: 'Paused',
    4: 'Synced OK',
    -1: 'Not available'
}

class SyncServerWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SyncServerWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
        self.resize(1400, 800)

        body = QtWidgets.QWidget()
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(20)

        container = QtWidgets.QWidget()
        projects = SyncProjectListWidget(parent=self)
        repres = SyncRepresentationWidget(project=projects.current_project,
                                          parent=self)

        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        split = QtWidgets.QSplitter()
        split.addWidget(projects)
        split.addWidget(repres)
        split.setSizes([180, 950, 200])
        container_layout.addWidget(split)

        container.setLayout(container_layout)

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
        self.setWindowTitle("Sync Server")


class SyncProjectListWidget(ProjectListWidget):
    """
        Lists all projects that are syncronized to choose from
    """

    def validate_context_change(self):
        return True

    def refresh(self):
        selected_project = None
        for index in self.project_list.selectedIndexes():
            selected_project = index.data(QtCore.Qt.DisplayRole)
            break

        model = self.project_list.model()
        model.clear()
        items = []
        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]

        for project_name in sync_server.get_synced_presets().keys():
            items.append(project_name)

        sync_server.log.debug("ld !!!! items:: {}".format(items))
        for item in items:
            model.appendRow(QtGui.QStandardItem(item))

        # self.select_project(selected_project)

        self.current_project = self.project_list.currentIndex().data(
            QtCore.Qt.DisplayRole
        )


class SyncRepresentationWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal()    # active index changed

    default_widths = (
        ("asset", 210),
        ("subset", 190),
        ("version", 10),
        ("representation", 90),
        ("created_dt", 100),
        ("sync_dt", 100),
        ("local_site", 60),
        ("remote_site", 70),
        ("files_count", 70),
        ("files_size", 70),
        ("priority", 20),
        ("state", 50)
    )

    def __init__(self, project=None, parent=None):
        super(SyncRepresentationWidget, self).__init__(parent)
        self.project = project

        self.filter = QtWidgets.QLineEdit()
        self.filter.setPlaceholderText("Filter representations..")

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(self.filter)

        # TODO ? TreeViewSpinner

        self.table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]
        log.debug("!!! headers:: {}".format(headers))
        model = SyncRepresentationModel(headers)
        self.table_view.setModel(model)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self.table_view.setSelectionMode(
        #     QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.horizontalHeader().setSortIndicator(
            -1, Qt.AscendingOrder)
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().hide()

        time_delegate = PrettyTimeDelegate(self)
        column = self.table_view.model()._header.index("created_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)
        column = self.table_view.model()._header.index("sync_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)

        column = self.table_view.model()._header.index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)


        column = self.table_view.model()._header.index("remote_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model()._header.index("files_size")
        delegate = SizeDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        for column_name, width in self.default_widths:
            idx = model._header.index(column_name)
            self.table_view.setColumnWidth(idx, width)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(self.table_view)

        self.table_view.doubleClicked.connect(self._doubleClicked)
        self.filter.textChanged.connect(lambda: model.set_filter(
            self.filter.text()))
        self.table_view.customContextMenuRequested.connect(
            self._on_context_menu)

    def _doubleClicked(self, index):
        """
            Opens representation dialog with all files after doubleclick
        """
        _id = self.table_view.model().data(index, Qt.UserRole)
        detail_window = SyncServerDetailWindow(_id, self.project)
        detail_window.exec()

    def _on_context_menu(self, point):
        """
            Shows menu with loader actions on Right-click.
        """
        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return


class SyncRepresentationModel(QtCore.QAbstractTableModel):
    PAGE_SIZE = 30
    DEFAULT_SORT = {
        "context.asset": 1,
        "context.subset": 1,
        "context.version": 1,
    }
    SORT_BY_COLUMN = [
        "context.asset",            # asset
        "context.subset",           # subset
        "context.version",          # version
        "context.representation",   # representation
        "updated_dt_local",         # local created_dt
        "updated_dt_remote",        # remote created_dt
        "avg_progress_local",       # local progress
        "avg_progress_remote",      # remote progress
        "files_count",              # count of files
        "files_size",               # file size of all files
        "context.asset",            # priority TODO
        "status"                    # state
    ]
    DEFAULT_QUERY = {
        "type": "representation",
    }

    numberPopulated = QtCore.Signal(int)

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
        files_count = attr.ib(default=None)
        files_size = attr.ib(default=None)
        priority = attr.ib(default=None)
        state = attr.ib(default=None)

    def __init__(self, header, project=None):
        super(SyncRepresentationModel, self).__init__()
        self._header = header
        self._data = []
        self._project = project
        self._rec_loaded = 0
        self._buffer = []  # stash one page worth of records (actually cursor)
        self.filter = None

        self._initialized = False

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()
        self.dbcon.Session["AVALON_PROJECT"] = self._project or 'petr_test'  # TEMP

        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        # TODO think about admin mode
        # this is for regular user, always only single local and single remote
        self.local_site, self.remote_site = \
            sync_server.get_sites_for_project('petr_test')

        self.query = self.DEFAULT_QUERY

        self.projection = {
            "context.subset": 1,
            "context.asset": 1,
            "context.version": 1,
            "context.representation": 1,
            "files": 1,
            'files_count': 1,
            "files_size": 1,
            'avg_progress_remote': 1,
            'avg_progress_local': 1,
            'updated_dt_remote': 1,
            'updated_dt_local': 1,
            'status': {
                '$switch': {
                    'branches': [
                        {
                            'case': {
                                '$or': [{'$eq': ['$avg_progress_remote', 0]},
                                        {'$eq': ['$avg_progress_local', 0]}]},
                            'then': 0
                        },
                        {
                            'case': {
                                '$or': ['$failed_remote', '$failed_local']},
                            'then': 1
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
                            'then': 2
                        },
                        {
                            'case': {'$eq': ['dummy_placeholder', 'paused']},
                            'then': 3
                        },
                        {
                            'case': {'$and': [
                                {'$eq': ['$avg_progress_remote', 1]},
                                {'$eq': ['$avg_progress_local', 1]}
                            ]},
                            'then': 4
                        },
                    ],
                    'default': -1
                }
            }
        }

        self.sort = self.DEFAULT_SORT

        self.query = self.get_default_query()
        self.default_query = list(self.get_default_query())
        log.debug("!!! init query: {}".format(json.dumps(self.query, indent=4)))
        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

    def data(self, index, role):
        item = self._data[index.row()]

        if role == Qt.DisplayRole:
            return attr.asdict(item)[self._header[index.column()]]
        if role == Qt.UserRole:
            return item._id

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self._header)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._header[section])

    def refresh(self, representations=None):
        self.beginResetModel()
        self._data = []
        self._rec_loaded = 0
        log.debug("!!! refresh sort {}".format(self.sort))
        if not representations:
            self.query = self.get_default_query()
            log.debug(
                "!!! init query: {}".format(json.dumps(self.query, indent=4)))
            representations = self.dbcon.aggregate(self.query)

        self._add_page_records(self.local_site, self.remote_site,
                               representations)
        self.endResetModel()

    def _add_page_records(self, local_site, remote_site, representations):
        log.debug("!!! representations:: {}".format(representations))
        #log.debug("!!! representations:: {}".format(len(representations)))
        for repre in representations:
            context = repre.get("context").pop()
            # log.debug("!!! context:: {}".format(context))
            # log.info("!!! repre:: {}".format(repre))
            # log.debug("!!! repre:: {}".format(type(repre)))
            created = {}
            # log.debug("!!! files:: {}".format(repre.get("files", [])))
            # log.debug("!!! files:: {}".format(type(repre.get("files", []))))
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

            avg_progress_remote = repre.get('avg_progress_remote', '')
            avg_progress_local = repre.get('avg_progress_local', '')

            item = self.SyncRepresentation(
                repre.get("_id"),
                context.get("asset"),
                context.get("subset"),
                "v{:0>3d}".format(context.get("version", 1)),
                context.get("representation"),
                local_updated,
                remote_updated,
                '{} {}'.format(local_site, avg_progress_local),
                '{} {}'.format(remote_site, avg_progress_remote),
                repre.get("files_count", 1),
                repre.get("files_size", 0),
                1,
                STATUS[repre.get("status", -1)]
            )

            self._data.append(item)
            self._rec_loaded += 1

    def canFetchMore(self, index):
        """
            Check if there are more records than currently loaded
        """
        log.debug("!!! canFetchMore _rec_loaded:: {}".format(self._rec_loaded))
        # 'skip' might be suboptimal when representation hits 500k+
        self._buffer = list(self.dbcon.aggregate(self.query))
        # log.debug("!!! self._buffer.count():: {}".format(len(self._buffer)))
        return len(self._buffer) > self._rec_loaded

    def fetchMore(self, index):
        """
            Add more record to model.

            Called when 'canFetchMore' returns true, which means there are
            more records in DB than loaded.
            'self._buffer' is used to stash cursor to limit requery
        """
        log.debug("fetchMore")
        # cursor.count() returns always total number, not only skipped + limit
        remainder = len(self._buffer) - self._rec_loaded
        items_to_fetch = min(self.PAGE_SIZE, remainder)
        self.beginInsertRows(index,
                             self._rec_loaded,
                             self._rec_loaded + items_to_fetch - 1)

        self._add_page_records(self.local_site, self.remote_site, self._buffer)

        self.endInsertRows()

        self.numberPopulated.emit(items_to_fetch)  # ??

    def sort(self, index, order):
        """
            Summary sort per representation

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

        self.sort = {self.SORT_BY_COLUMN[index]: order}
        self.query = self.get_default_query()

        log.debug("!!! sort {}".format(self.sort))
        log.debug("!!! query {}".format(json.dumps(self.query, indent=4)))
        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

    def set_filter(self, filter):
        self.filter = filter
        self.refresh()

    def get_default_query(self):
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
                    0 - queued
                    1 - failed
                    2 - paused (not implemented yet)
                    3 - in progress
                    4 - finished on both sides

                are calculated and must be calculated in DB because of
                pagination
        """
        return [
            {"$match": self._get_match_part()},
            {'$unwind': '$files'},
            # merge potentially unwinded records back to single per repre
            {'$addFields': {
                'order_remote': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.remote_site]}
                                }}
                , 'order_local': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.local_site]}
                                }}
            }},
            {'$addFields': {
                # prepare progress per file, presence of 'created_dt' denotes
                # successfully finished load/download
                'progress_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.progress"},
                              "$order_remote.progress", {'$cond': [
                                {'$size': "$order_remote.created_dt"}, [1],
                                [0]]}]}}
                , 'progress_local': {'$first': {
                    '$cond': [{'$size': "$order_local.progress"},
                              "$order_local.progress", {'$cond': [
                                {'$size': "$order_local.created_dt"}, [1],
                                [0]]}]}}
                # file might be successfully created or failed, not both
                , 'updated_dt_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.created_dt"},
                              "$order_remote.created_dt",
                              {'$cond': [
                                {'$size': "$order_remote.last_failed_dt"},
                                "$order_remote.last_failed_dt",
                                []]
                               }]}}
                , 'updated_dt_local': {'$first': {
                    '$cond': [{'$size': "$order_local.created_dt"},
                              "$order_local.created_dt",
                              {'$cond': [
                                {'$size': "$order_local.last_failed_dt"},
                                "$order_local.last_failed_dt",
                                []]
                              }]}}
                , 'files_size': {'$ifNull': ["$files.size", 0]}
                , 'failed_remote': {
                    '$cond': [{'$size': "$order_remote.last_failed_dt"}, 1, 0]}
                , 'failed_local': {
                    '$cond': [{'$size': "$order_local.last_failed_dt"}, 1, 0]}
            }},
            {'$group': {
                '_id': '$_id'
                # pass through context - same for representation
                , 'context': {'$addToSet': '$context'}
                # pass through files as a list
                , 'files': {'$addToSet': '$files'}
                # count how many files
                , 'files_count': {'$sum': 1}
                , 'files_size': {'$sum': '$files_size'}
                # sum avg progress, finished = 1
                , 'avg_progress_remote': {'$avg': "$progress_remote"}
                , 'avg_progress_local': {'$avg': "$progress_local"}
                # select last touch of file
                , 'updated_dt_remote': {'$max': "$updated_dt_remote"}
                , 'failed_remote': {'$sum': '$failed_remote'}
                , 'failed_local': {'$sum': '$failed_local'}
                , 'updated_dt_local': {'$max': "$updated_dt_local"}
            }},
            {"$sort": self.sort},
            {"$limit": self.PAGE_SIZE},
            {"$skip": self._rec_loaded},
            {"$project": self.projection}
        ]

    def _get_match_part(self):
        """
            Extend match part with filter if present.

            Filter is set by user input. Each model has different fields to be
            checked.
            If performance issues are found, '$text' and text indexes should
            be investigated.
        """
        if not self.filter:
            return {
                "type": "representation",
                'files.sites': {
                    '$elemMatch': {
                        '$or': [
                            {'name': self.local_site},
                            {'name': self.remote_site}
                        ]
                    }
                }
            }
        else:
            regex_str = '.*{}.*'.format(self.filter)
            return {
                "type": "representation",
                '$or': [{'context.subset':  {'$regex': regex_str,
                                             '$options': 'i'}},
                        {'context.asset': {'$regex': regex_str,
                                           '$options': 'i'}},
                        {'context.representation': {'$regex': regex_str,
                                                    '$options': 'i'}}],
                'files.sites': {
                    '$elemMatch': {
                        '$or': [
                            {'name': self.local_site},
                            {'name': self.remote_site}
                        ]
                    }
                }
            }


class SyncServerDetailWindow(QtWidgets.QDialog):
    def __init__(self, _id, project,  parent=None):
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

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()
        self.dbcon.Session["AVALON_PROJECT"] = None

        container = SyncRepresentationDetailWidget(_id, project, parent=self)
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
        self.setWindowTitle("Sync Representation Detail")


class SyncRepresentationDetailWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal()    # active index changed

    default_widths = (
        ("file", 290),
        ("created_dt", 120),
        ("sync_dt", 120),
        ("local_site", 60),
        ("remote_site", 60),
        ("size", 60),
        ("priority", 20),
        ("state", 50)
    )

    def __init__(self, _id=None, project=None, parent=None):
        super(SyncRepresentationDetailWidget, self).__init__(parent)
        log.debug(
            "!!! SyncRepresentationDetailWidget _id:: {}".format(_id))
        self.filter = QtWidgets.QLineEdit()
        self.filter.setPlaceholderText("Filter representation..")

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(self.filter)

        self.table_view = QtWidgets.QTableView()
        headers = [item[0] for item in self.default_widths]
        log.debug("!!! SyncRepresentationDetailWidget headers:: {}".format(headers))

        model = SyncRepresentationDetailModel(headers, _id, project)
        self.table_view.setModel(model)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(
            QtWidgets.QTableView.SelectRows)
        self.table_view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().hide()

        time_delegate = PrettyTimeDelegate(self)
        column = self.table_view.model()._header.index("created_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)
        column = self.table_view.model()._header.index("sync_dt")
        self.table_view.setItemDelegateForColumn(column, time_delegate)

        column = self.table_view.model()._header.index("local_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model()._header.index("remote_site")
        delegate = ImageDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        column = self.table_view.model()._header.index("size")
        delegate = SizeDelegate(self)
        self.table_view.setItemDelegateForColumn(column, delegate)

        for column_name, width in self.default_widths:
            idx = model._header.index(column_name)
            self.table_view.setColumnWidth(idx, width)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(self.table_view)

        self.filter.textChanged.connect(lambda: model.set_filter(
            self.filter.text()))
        self.table_view.customContextMenuRequested.connect(
            self._on_context_menu)

    def _show_detail(self):
        pass

    def _on_context_menu(self, point):
        """
            Shows menu with loader actions on Right-click.
        """
        point_index = self.table_view.indexAt(point)
        if not point_index.isValid():
            return

        item = self.table_view.model()._data[point_index.row()]
        log.info('item:: {}'.format(item))

        menu = QtWidgets.QMenu()
        actions_mapping = {}
        if item.state == STATUS[1]:
            action = QtWidgets.QAction("Open detail")
            actions_mapping[action] = self._show_detail
            menu.addAction(action)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()
                to_run()


class SyncRepresentationDetailModel(QtCore.QAbstractTableModel):
    PAGE_SIZE = 30
    # TODO add filename to sort
    DEFAULT_SORT = {
        "files.path": 1
    }
    SORT_BY_COLUMN = [
        "files.path",
        "updated_dt_local",     # local created_dt
        "updated_dt_remote",    # remote created_dt
        "progress_local",       # local progress
        "progress_remote",      # remote progress
        "size",                 # remote progress
        "context.asset",        # priority TODO
        "status"                # state
    ]

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
        size = attr.ib(default=None)
        priority = attr.ib(default=None)
        state = attr.ib(default=None)

    def __init__(self, header, _id, project=None):
        super(SyncRepresentationDetailModel, self).__init__()
        self._header = header
        self._data = []
        self._project = project
        self._rec_loaded = 0
        self.filter = None
        self._buffer = []  # stash one page worth of records (actually cursor)
        self._id = _id
        log.debug("!!! init _id: {}".format(self._id))
        self._initialized = False

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()
        self.dbcon.Session["AVALON_PROJECT"] = self._project or 'petr_test'  # TEMP

        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        # TODO think about admin mode
        # this is for regular user, always only single local and single remote
        self.local_site, self.remote_site = \
            sync_server.get_sites_for_project('petr_test')

        self.sort = self.DEFAULT_SORT

        # in case we would like to hide/show some columns
        self.projection = {
            "files": 1,
            'progress_remote': 1,
            'progress_local': 1,
            'updated_dt_remote': 1,
            'updated_dt_local': 1,
            'status': {
                '$switch': {
                    'branches': [
                        {
                            'case': {
                                '$or': [{'$eq': ['$progress_remote', 0]},
                                        {'$eq': ['$progress_local', 0]}]},
                            'then': 0
                        },
                        {
                            'case': {
                                '$or': ['$failed_remote', '$failed_local']},
                            'then': 1
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
                            'then': 2
                        },
                        {
                            'case': {'$eq': ['dummy_placeholder', 'paused']},
                            'then': 3
                        },
                        {
                            'case': {'$and': [
                                {'$eq': ['$progress_remote', 1]},
                                {'$eq': ['$progress_local', 1]}
                            ]},
                            'then': 4
                        },
                    ],
                    'default': -1
                }
            }
        }

        self.query = self.get_default_query()
        log.debug("!!! init query: {}".format(self.query))
        representations = self.dbcon.aggregate(self.query)
        self.refresh(representations)

    def data(self, index, role):
        item = self._data[index.row()]
        if role == Qt.DisplayRole:
            return attr.asdict(item)[self._header[index.column()]]
        if role == Qt.UserRole:
            return item._id

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self._header)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._header[section])

    def refresh(self, representations=None):
        self.beginResetModel()
        self._data = []
        self._rec_loaded = 0

        if not representations:
            self.query = self.get_default_query()
            log.debug("!!! init query: {}".format(self.query))
            representations = self.dbcon.aggregate(self.query)

        self._add_page_records(self.local_site, self.remote_site,
                               representations)
        self.endResetModel()

    def _add_page_records(self, local_site, remote_site, representations):
        """
            Process all records from 'representation' and add them to storage.

            Args:
                local_site (str): name of local site (mine)
                remote_site (str): name of cloud provider (theirs)
                representations (Mongo Cursor)
        """
        for repre in representations:
            # log.info("!!! repre:: {}".format(repre))

            # log.debug("!!! files:: {}".format(repre.get("files", [])))
            files = repre.get("files", [])
            if isinstance(files, dict):  # aggregate returns dictionary
                files = [files]

            for file in files:
                created = {}
                # log.info("!!! file:: {}".format(file))
                sites = file.get("sites")
                # log.debug("!!! sites:: {}".format(sites))

                local_updated = remote_updated = None
                if repre.get('updated_dt_local'):
                    local_updated = \
                        repre.get('updated_dt_local').strftime(
                            "%Y%m%dT%H%M%SZ")

                if repre.get('updated_dt_remote'):
                    remote_updated = \
                        repre.get('updated_dt_remote').strftime(
                            "%Y%m%dT%H%M%SZ")

                progress_remote = repre.get('progress_remote', '')
                progress_local = repre.get('progress_local', '')

                item = self.SyncRepresentationDetail(
                    repre.get("_id"),
                    os.path.basename(file["path"]),
                    local_updated,
                    remote_updated,
                    '{} {}'.format(local_site, progress_local),
                    '{} {}'.format(remote_site, progress_remote),
                    file.get('size', 0),
                    1,
                    STATUS[repre.get("status", -1)]
                )
                self._data.append(item)
                self._rec_loaded += 1

        # log.info("!!! _add_page_records _rec_loaded:: {}".format(self._rec_loaded))

    def canFetchMore(self, index):
        """
            Check if there are more records than currently loaded
        """
        # 'skip' might be suboptimal when representation hits 500k+
        self._buffer = list(self.dbcon.aggregate(self.query))
        return len(self._buffer) > self._rec_loaded

    def fetchMore(self, index):
        """
            Add more record to model.

            Called when 'canFetchMore' returns true, which means there are
            more records in DB than loaded.
            'self._buffer' is used to stash cursor to limit requery
        """
        log.debug("fetchMore")
        # cursor.count() returns always total number, not only skipped + limit
        remainder = len(self._buffer) - self._rec_loaded
        items_to_fetch = min(self.PAGE_SIZE, remainder)

        self.beginInsertRows(index,
                             self._rec_loaded,
                             self._rec_loaded + items_to_fetch - 1)
        self._add_page_records(self.local_site, self.remote_site, self._buffer)

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

    def get_default_query(self):
        """
            Gets query that gets used when no extra sorting, filtering or
            projecting is needed.

            Called for basic table view.

            Returns:
                [(dict)] - list with single dict - appropriate for aggregate
                    function for MongoDB
        """
        return [
            {"$match": self._get_match_part()},
            {"$unwind": "$files"},
            {'$addFields': {
                'order_remote': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.remote_site]}
                                }}
                , 'order_local': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', self.local_site]}
                                }}
            }},
            {'$addFields': {
                # prepare progress per file, presence of 'created_dt' denotes
                # successfully finished load/download
                'progress_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.progress"},
                              "$order_remote.progress", {'$cond': [
                            {'$size': "$order_remote.created_dt"}, [1],
                            [0]]}]}}
                , 'progress_local': {'$first': {
                    '$cond': [{'$size': "$order_local.progress"},
                              "$order_local.progress", {'$cond': [
                            {'$size': "$order_local.created_dt"}, [1],
                            [0]]}]}}
                # file might be successfully created or failed, not both
                , 'updated_dt_remote': {'$first': {
                    '$cond': [{'$size': "$order_remote.created_dt"},
                              "$order_remote.created_dt",
                              {'$cond': [
                                  {'$size': "$order_remote.last_failed_dt"},
                                  "$order_remote.last_failed_dt",
                                  []]
                              }]}}
                , 'updated_dt_local': {'$first': {
                    '$cond': [{'$size': "$order_local.created_dt"},
                              "$order_local.created_dt",
                              {'$cond': [
                                  {'$size': "$order_local.last_failed_dt"},
                                  "$order_local.last_failed_dt",
                                  []]
                              }]}}
                , 'failed_remote': {
                    '$cond': [{'$size': "$order_remote.last_failed_dt"}, 1, 0]}
                , 'failed_local': {
                    '$cond': [{'$size': "$order_local.last_failed_dt"}, 1, 0]}
            }},
            {"$sort": self.sort},
            {"$limit": self.PAGE_SIZE},
            {"$skip": self._rec_loaded},
            {"$project": self.projection}
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
                '$or': [{'files.path': {'$regex': regex_str,
                                            '$options': 'i'}}]
            }


class ImageDelegate(QtWidgets.QStyledItemDelegate):
    """
        Prints icon of site and progress of synchronization
    """
    def __init__(self, parent=None):
        super(ImageDelegate, self).__init__(parent)

    def paint(self, painter, option, index):
        d = index.data(QtCore.Qt.DisplayRole)
        if d:
            provider, value = d.split()
        else:
            return

        # log.info("data:: {} - {}".format(provider, value))
        pix_url = "../providers/resources/{}.png".format(provider)
        pixmap = QtGui.QPixmap(pix_url)

        point = QtCore.QPoint(option.rect.x() +
                              (option.rect.width() - pixmap.width()) / 2,
                              option.rect.y() +
                              (option.rect.height() - pixmap.height()) / 2)
        painter.drawPixmap(point, pixmap)

        painter.setOpacity(0.5)
        overlay_rect = option.rect
        overlay_rect.setHeight(overlay_rect.height() * (1.0 - float(value)))
        #painter.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationOver)
        #painter.setBrush(painter.brush(Qt.white))
        painter.fillRect(overlay_rect,  QtGui.QBrush(QtGui.QColor(0,0,0,200)))


class SizeDelegate(QtWidgets.QStyledItemDelegate):
    """
        Pretty print for file size
    """
    def __init__(self, parent=None):
        super(SizeDelegate, self).__init__(parent)

    def displayText(self, value, locale):
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


# Back up the reference to the exceptionhook
sys._excepthook = sys.excepthook

def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)

# Set the exception hook to our wrapping function
sys.excepthook = my_exception_hook

if __name__ == '__main__':
    import sys
    from time import sleep
    app = QtWidgets.QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
    os.environ["PYPE_MONGO"] = "mongodb://localhost:27017"
    os.environ["AVALON_MONGO"] = "mongodb://localhost:27017"
    os.environ["AVALON_DB"] = "avalon"
    os.environ["AVALON_TIMEOUT"] = '3000'

    widget = SyncServerWindow()
    widget.show()

    # while True:
    #     # run some codes that use QAxWidget.dynamicCall() function
    #     # print some results
    #     sleep(30)

    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")
