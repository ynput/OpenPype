#TODO:
# - add 'process start time' column (+get info) (?)

from Qt import QtWidgets, QtGui, QtCore

from openpype import resources
from openpype.lib import Logger
from openpype.style import load_stylesheet

from .model import ProcessModel
from .view import ProcessView


class ProcessMonitorDialog(QtWidgets.QDialog):
    signal_update_table = QtCore.Signal(dict, int)
    signal_select_task = QtCore.Signal()

    def __init__(self, module):
        super(ProcessMonitorDialog, self).__init__()

        self._log = None
        self._module = module

        self.setWindowTitle("Process Monitor")
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        main_layout = QtWidgets.QVBoxLayout(self)

        ########
        # Process table
        process_view = ProcessView(self)
        process_model = ProcessModel()

        # Create proxy model to be able to sort and filter
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(process_model)
        proxy_model.setDynamicSortFilter(True)
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        process_view.setModel(proxy_model)
        process_view.setSortingEnabled(True)
        process_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        process_view.setIndentation(3)

        #TODO: delegates? (=> could use for 'started time')
        '''
        # Date modified delegate
        time_delegate = PrettyTimeDelegate()
        process_view.setItemDelegateForColumn(1, time_delegate)
        '''


        #TODO: move elsewhere (as dictionary with names definition)
        default_widths = (
            ("application", 150),
            ("project", 150),
            ("context", 300),
            ("task", 100),
            ("pid", 85),
            ("status", 32)
        )
        for column_name, width in default_widths:
            index = process_model.Columns.index(column_name)
            process_view.setColumnWidth(index, width)


        process_view.doubleClickedLeft.connect(self.start_timer)
        process_view.customContextMenuRequested.connect(self.on_context_menu)
        #TODO: want?
        '''
        process_view.selectionModel().selectionChanged.connect(
            self.on_process_select
        )
        '''

        main_layout.addWidget(process_view)

        self._process_view = process_view
        self._process_model = process_model
        ########


        # Buttons
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch(1)
        main_layout.addLayout(buttons_layout)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self._on_close_clicked)
        buttons_layout.addWidget(close_button)


        self.setStyleSheet(load_stylesheet())
        self.signal_update_table.connect(self.update_running_processes)
        self.signal_select_task.connect(self.show_selector)
        
        self.resize(1024, self.height())

        self._process_model.update({})


    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def _get_selected_pid(self):
        """Return process ID currently selected in view"""
        selection = self._process_view.selectionModel()
        index = selection.currentIndex()
        if not index.isValid():
            return

        return index.data(self._process_model.PidRole)

    def _get_selected_status(self):
        """Return status currently selected in view"""
        selection = self._process_view.selectionModel()
        index = selection.currentIndex()
        if not index.isValid():
            return

        return index.data(self._process_model.StatusRole)

    def start_timer(self):
        pid = self._get_selected_pid()
        if not pid:
            self.log.warning("No Process ID selected")
            return

        self._module.request_start_timer(pid)

    def stop_timer(self):
        pid = self._get_selected_pid()
        if not pid:
            self.log.warning("No Process ID selected")
            return

        status = self._get_selected_status()
        if not status:
            return

        self._module.request_start_timer(None)


    def on_context_menu(self, point):
        index = self._process_view.indexAt(point)
        if not index.isValid():
            return

        is_enabled = index.data(ProcessModel.IsEnabled)
        if not is_enabled:
            return

        menu = QtWidgets.QMenu(self)

        #TODO: hide or disable option?
        status = index.data(ProcessModel.StatusRole)

        # Start
        action = QtWidgets.QAction("Start timer", menu)
        if status:
            action.setDisabled(True)
        else:
            tip = "Start timer for process"
            action.setToolTip(tip)
            action.setStatusTip(tip)
            action.triggered.connect(self.start_timer)
        menu.addAction(action)

        # Stop
        action = QtWidgets.QAction("Stop timer", menu)
        if status:
            tip = "Stop timer for process"
            action.setToolTip(tip)
            action.setStatusTip(tip)
            action.triggered.connect(self.stop_timer)
        else:
            action.setDisabled(True)
        menu.addAction(action)

        # Show the context action menu
        global_point = self._process_view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action:
            return

    def _on_close_clicked(self):
        self.done(1)

    def update_running_processes(self, running_processes, current_pid):
        self._process_model.update(running_processes, current_pid)

    def show_selector(self):
        # Make sure process monitor window is displayed
        self.show()
        self.activateWindow()

        # Show warning dialog
        msg = ("More than 1 process is running.\n"
               "Please specify the current task in the 'Process Monitor'.")
        detail = ("In the 'Process Monitor' window,"
                  " activate the timer for the current task.\n\n"
                  "To activate a timer, determine the row associated to the task, and either:\n"
                  "- double-click on the row\n"
                  "Or:\n"
                  "- right-click on the row and select 'Start timer'")
        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Warning,
            "Error",
            msg,
            parent=self)
        dialog.setMinimumWidth(500)
        dialog.setDetailedText(detail)


        dialog.setWindowTitle("OpenPype - Select current task")

        '''
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        dialog.setWindowIcon(icon)
        '''

        flags = dialog.windowFlags()
        dialog.setWindowFlags(
            flags
            | QtCore.Qt.WindowStaysOnTopHint
        )

        dialog.exec_()
