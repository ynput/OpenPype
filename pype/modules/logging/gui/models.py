import collections
from Qt import QtCore, QtGui
from pype.api import Logger
from pypeapp.lib.log import _bootstrap_mongo_log, LOG_COLLECTION_NAME

log = Logger().get_logger("LogModel", "LoggingModule")


class LogModel(QtGui.QStandardItemModel):
    COLUMNS = (
        "process_name",
        "hostname",
        "hostip",
        "username",
        "system_name",
        "started"
    )
    colums_mapping = {
        "process_name": "Process Name",
        "process_id": "Process Id",
        "hostname": "Hostname",
        "hostip": "Host IP",
        "username": "Username",
        "system_name": "System name",
        "started": "Started at"
    }
    process_keys = (
        "process_id", "hostname", "hostip",
        "username", "system_name", "process_name"
    )
    log_keys = (
        "timestamp", "level", "thread", "threadName", "message", "loggerName",
        "fileName", "module", "method", "lineNumber"
    )
    default_value = "- Not set -"

    ROLE_LOGS = QtCore.Qt.UserRole + 2
    ROLE_PROCESS_ID = QtCore.Qt.UserRole + 3

    def __init__(self, parent=None):
        super(LogModel, self).__init__(parent)

        self.log_by_process = None
        self.dbcon = None

        # Crash if connection is not possible to skip this module
        database = _bootstrap_mongo_log()
        if LOG_COLLECTION_NAME in database.list_collection_names():
            self.dbcon = database[LOG_COLLECTION_NAME]

    def headerData(self, section, orientation, role):
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
        ):
            if section < len(self.COLUMNS):
                key = self.COLUMNS[section]
                return self.colums_mapping.get(key, key)

        super(LogModel, self).headerData(section, orientation, role)

    def add_process_logs(self, process_logs):
        items = []
        first_item = True
        for key in self.COLUMNS:
            display_value = str(process_logs[key])
            item = QtGui.QStandardItem(display_value)
            if first_item:
                first_item = False
                item.setData(process_logs["_logs"], self.ROLE_LOGS)
                item.setData(process_logs["process_id"], self.ROLE_PROCESS_ID)
            items.append(item)
        self.appendRow(items)

    def refresh(self):
        self.log_by_process = collections.defaultdict(list)
        self.process_info = {}

        self.clear()
        self.beginResetModel()
        if self.dbcon:
            result = self.dbcon.find({})
            for item in result:
                process_id = item.get("process_id")
                # backwards (in)compatibility
                if not process_id:
                    continue

                if process_id not in self.process_info:
                    proc_dict = {"_logs": []}
                    for key in self.process_keys:
                        proc_dict[key] = (
                            item.get(key) or self.default_value
                        )
                    self.process_info[process_id] = proc_dict

                log_item = {}
                for key in self.log_keys:
                    log_item[key] = item.get(key) or self.default_value

                if "exception" in item:
                    log_item["exception"] = item["exception"]

                self.process_info[process_id]["_logs"].append(log_item)

        for item in self.process_info.values():
            item["_logs"] = sorted(
                item["_logs"], key=lambda item: item["timestamp"]
            )
            item["started"] = item["_logs"][0]["timestamp"]
            self.add_process_logs(item)

        self.endResetModel()


class LogsFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(LogsFilterProxy, self).__init__(*args, **kwargs)
        self.col_usernames = None
        self.filter_usernames = set()

    def update_users_filter(self, users):
        self.filter_usernames = set()
        for user in users or tuple():
            self.filter_usernames.add(user)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if self.col_usernames is not None:
            index = self.sourceModel().index(
                source_row, self.col_usernames, source_parent
            )
            user = index.data(QtCore.Qt.DisplayRole)
            if user not in self.filter_usernames:
                return False
        return True
