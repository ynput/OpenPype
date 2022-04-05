import os
import re
import sys
import collections
from code import InteractiveInterpreter

import appdirs
from Qt import QtCore, QtWidgets, QtGui

from openpype import resources
from openpype.style import load_stylesheet
from openpype.lib import JSONSettingRegistry


openpype_art = """
             . .   ..     .    ..
        _oOOP3OPP3Op_. .
     .PPpo~.   ..   ~2p.  ..  ....  .  .
    .Ppo . .pPO3Op.. . O:. . . .
   .3Pp . oP3'. 'P33. . 4 ..   .  .   . .. .  .  .
  .~OP    3PO.  .Op3    : . ..  _____  _____  _____
  .P3O  . oP3oP3O3P' . . .   . /    /./    /./    /
   O3:.   O3p~ .       .:. . ./____/./____/ /____/
   'P .   3p3.  oP3~. ..P:. .  . ..  .   . .. .  .  .
  . ':  . Po'  .Opo'. .3O. .  o[ by Pype Club ]]]==- - - .  .
    . '_ ..  .    . _OP3..  .  .https://openpype.io.. .
         ~P3.OPPPO3OP~ . ..  .
           .  ' '. .  .. . . . ..  .


"""


class PythonInterpreterRegistry(JSONSettingRegistry):
    """Class handling OpenPype general settings registry.

    Attributes:
        vendor (str): Name used for path construction.
        product (str): Additional name used for path construction.

    """

    def __init__(self):
        self.vendor = "pypeclub"
        self.product = "openpype"
        name = "python_interpreter_tool"
        path = appdirs.user_data_dir(self.product, self.vendor)
        super(PythonInterpreterRegistry, self).__init__(name, path)


class StdOEWrap:
    def __init__(self):
        self._origin_stdout_write = None
        self._origin_stderr_write = None
        self._listening = False
        self.lines = collections.deque()

        if not sys.stdout:
            sys.stdout = open(os.devnull, "w")

        if not sys.stderr:
            sys.stderr = open(os.devnull, "w")

        if self._origin_stdout_write is None:
            self._origin_stdout_write = sys.stdout.write

        if self._origin_stderr_write is None:
            self._origin_stderr_write = sys.stderr.write

        self._listening = True
        sys.stdout.write = self._stdout_listener
        sys.stderr.write = self._stderr_listener

    def stop_listen(self):
        self._listening = False

    def _stdout_listener(self, text):
        if self._listening:
            self.lines.append(text)
        if self._origin_stdout_write is not None:
            self._origin_stdout_write(text)

    def _stderr_listener(self, text):
        if self._listening:
            self.lines.append(text)
        if self._origin_stderr_write is not None:
            self._origin_stderr_write(text)


class PythonCodeEditor(QtWidgets.QPlainTextEdit):
    execute_requested = QtCore.Signal()

    def __init__(self, parent):
        super(PythonCodeEditor, self).__init__(parent)

        self.setObjectName("PythonCodeEditor")

        self._indent = 4

    def _tab_shift_right(self):
        cursor = self.textCursor()
        selected_text = cursor.selectedText()
        if not selected_text:
            cursor.insertText(" " * self._indent)
            return

        sel_start = cursor.selectionStart()
        sel_end = cursor.selectionEnd()
        cursor.setPosition(sel_end)
        end_line = cursor.blockNumber()
        cursor.setPosition(sel_start)
        while True:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            text = cursor.block().text()
            spaces = len(text) - len(text.lstrip(" "))
            new_spaces = spaces % self._indent
            if not new_spaces:
                new_spaces = self._indent

            cursor.insertText(" " * new_spaces)
            if cursor.blockNumber() == end_line:
                break

            cursor.movePosition(QtGui.QTextCursor.NextBlock)

    def _tab_shift_left(self):
        tmp_cursor = self.textCursor()
        sel_start = tmp_cursor.selectionStart()
        sel_end = tmp_cursor.selectionEnd()

        cursor = QtGui.QTextCursor(self.document())
        cursor.setPosition(sel_end)
        end_line = cursor.blockNumber()
        cursor.setPosition(sel_start)
        while True:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            text = cursor.block().text()
            spaces = len(text) - len(text.lstrip(" "))
            if spaces:
                spaces_to_remove = (spaces % self._indent) or self._indent
                if spaces_to_remove > spaces:
                    spaces_to_remove = spaces

                cursor.setPosition(
                    cursor.position() + spaces_to_remove,
                    QtGui.QTextCursor.KeepAnchor
                )
                cursor.removeSelectedText()

            if cursor.blockNumber() == end_line:
                break

            cursor.movePosition(QtGui.QTextCursor.NextBlock)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Backtab:
            self._tab_shift_left()
            event.accept()
            return

        if event.key() == QtCore.Qt.Key_Tab:
            if event.modifiers() == QtCore.Qt.NoModifier:
                self._tab_shift_right()
            event.accept()
            return

        if (
            event.key() == QtCore.Qt.Key_Return
            and event.modifiers() == QtCore.Qt.ControlModifier
        ):
            self.execute_requested.emit()
            event.accept()
            return

        super(PythonCodeEditor, self).keyPressEvent(event)


class PythonTabWidget(QtWidgets.QWidget):
    add_tab_requested = QtCore.Signal()
    before_execute = QtCore.Signal(str)

    def __init__(self, parent):
        super(PythonTabWidget, self).__init__(parent)

        code_input = PythonCodeEditor(self)

        self.setFocusProxy(code_input)

        add_tab_btn = QtWidgets.QPushButton("Add tab...", self)
        add_tab_btn.setToolTip("Add new tab")

        execute_btn = QtWidgets.QPushButton("Execute", self)
        execute_btn.setToolTip("Execute command (Ctrl + Enter)")

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addWidget(add_tab_btn)
        btns_layout.addStretch(1)
        btns_layout.addWidget(execute_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(code_input, 1)
        layout.addLayout(btns_layout, 0)

        add_tab_btn.clicked.connect(self._on_add_tab_clicked)
        execute_btn.clicked.connect(self._on_execute_clicked)
        code_input.execute_requested.connect(self.execute)

        self._code_input = code_input
        self._interpreter = InteractiveInterpreter()

    def _on_add_tab_clicked(self):
        self.add_tab_requested.emit()

    def _on_execute_clicked(self):
        self.execute()

    def get_code(self):
        return self._code_input.toPlainText()

    def set_code(self, code_text):
        self._code_input.setPlainText(code_text)

    def execute(self):
        code_text = self._code_input.toPlainText()
        self.before_execute.emit(code_text)
        self._interpreter.runcode(code_text)


class TabNameDialog(QtWidgets.QDialog):
    default_width = 330
    default_height = 85

    def __init__(self, parent):
        super(TabNameDialog, self).__init__(parent)

        self.setWindowTitle("Enter tab name")

        name_label = QtWidgets.QLabel("Tab name:", self)
        name_input = QtWidgets.QLineEdit(self)

        inputs_layout = QtWidgets.QHBoxLayout()
        inputs_layout.addWidget(name_label)
        inputs_layout.addWidget(name_input)

        ok_btn = QtWidgets.QPushButton("Ok", self)
        cancel_btn = QtWidgets.QPushButton("Cancel", self)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn)
        btns_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(inputs_layout)
        layout.addStretch(1)
        layout.addLayout(btns_layout)

        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        self._name_input = name_input
        self._ok_btn = ok_btn
        self._cancel_btn = cancel_btn

        self._result = None

        self.resize(self.default_width, self.default_height)

    def set_tab_name(self, name):
        self._name_input.setText(name)

    def result(self):
        return self._result

    def showEvent(self, event):
        super(TabNameDialog, self).showEvent(event)
        btns_width = max(
            self._ok_btn.width(),
            self._cancel_btn.width()
        )

        self._ok_btn.setMinimumWidth(btns_width)
        self._cancel_btn.setMinimumWidth(btns_width)

    def _on_ok_clicked(self):
        self._result = self._name_input.text()
        self.accept()

    def _on_cancel_clicked(self):
        self._result = None
        self.reject()


class OutputTextWidget(QtWidgets.QTextEdit):
    v_max_offset = 4

    def vertical_scroll_at_max(self):
        v_scroll = self.verticalScrollBar()
        return v_scroll.value() > v_scroll.maximum() - self.v_max_offset

    def scroll_to_bottom(self):
        v_scroll = self.verticalScrollBar()
        return v_scroll.setValue(v_scroll.maximum())


class EnhancedTabBar(QtWidgets.QTabBar):
    double_clicked = QtCore.Signal(QtCore.QPoint)
    right_clicked = QtCore.Signal(QtCore.QPoint)
    mid_clicked = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent):
        super(EnhancedTabBar, self).__init__(parent)

        self.setDrawBase(False)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(event.globalPos())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.right_clicked.emit(event.globalPos())
            event.accept()
            return

        elif event.button() == QtCore.Qt.MidButton:
            self.mid_clicked.emit(event.globalPos())
            event.accept()

        else:
            super(EnhancedTabBar, self).mouseReleaseEvent(event)


class PythonInterpreterWidget(QtWidgets.QWidget):
    default_width = 1000
    default_height = 600

    def __init__(self, parent=None):
        super(PythonInterpreterWidget, self).__init__(parent)

        self.setWindowTitle("OpenPype Console")
        self.setWindowIcon(QtGui.QIcon(resources.get_openpype_icon_filepath()))

        self.ansi_escape = re.compile(
            r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]"
        )

        self._tabs = []

        self._stdout_err_wrapper = StdOEWrap()

        output_widget = OutputTextWidget(self)
        output_widget.setObjectName("PythonInterpreterOutput")
        output_widget.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        output_widget.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        tab_widget = QtWidgets.QTabWidget(self)
        tab_bar = EnhancedTabBar(tab_widget)
        tab_widget.setTabBar(tab_bar)
        tab_widget.setTabsClosable(False)
        tab_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        widgets_splitter = QtWidgets.QSplitter(self)
        widgets_splitter.setOrientation(QtCore.Qt.Vertical)
        widgets_splitter.addWidget(output_widget)
        widgets_splitter.addWidget(tab_widget)
        widgets_splitter.setStretchFactor(0, 1)
        widgets_splitter.setStretchFactor(1, 1)
        height = int(self.default_height / 2)
        widgets_splitter.setSizes([height, self.default_height - height])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(widgets_splitter)

        line_check_timer = QtCore.QTimer()
        line_check_timer.setInterval(200)

        line_check_timer.timeout.connect(self._on_timer_timeout)
        tab_bar.right_clicked.connect(self._on_tab_right_click)
        tab_bar.double_clicked.connect(self._on_tab_double_click)
        tab_bar.mid_clicked.connect(self._on_tab_mid_click)
        tab_widget.tabCloseRequested.connect(self._on_tab_close_req)

        self._widgets_splitter = widgets_splitter
        self._output_widget = output_widget
        self._tab_widget = tab_widget
        self._line_check_timer = line_check_timer

        self._append_lines([openpype_art])

        self._first_show = True
        self._splitter_size_ratio = None

        self._init_from_registry()

        if self._tab_widget.count() < 1:
            self.add_tab("Python")

    def _init_from_registry(self):
        setting_registry = PythonInterpreterRegistry()
        width = None
        height = None
        try:
            width = setting_registry.get_item("width")
            height = setting_registry.get_item("height")

        except ValueError:
            pass

        if width is None or width < 200:
            width = self.default_width

        if height is None or height < 200:
            height = self.default_height

        self.resize(width, height)

        try:
            self._splitter_size_ratio = (
                setting_registry.get_item("splitter_sizes")
            )

        except ValueError:
            pass

        try:
            tab_defs = setting_registry.get_item("tabs") or []
            for tab_def in tab_defs:
                widget = self.add_tab(tab_def["name"])
                widget.set_code(tab_def["code"])

        except ValueError:
            pass

    def save_registry(self):
        setting_registry = PythonInterpreterRegistry()

        setting_registry.set_item("width", self.width())
        setting_registry.set_item("height", self.height())

        setting_registry.set_item(
            "splitter_sizes", self._widgets_splitter.sizes()
        )

        tabs = []
        for tab_idx in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(tab_idx)
            tab_code = widget.get_code()
            tab_name = self._tab_widget.tabText(tab_idx)
            tabs.append({
                "name": tab_name,
                "code": tab_code
            })

        setting_registry.set_item("tabs", tabs)

    def _on_tab_right_click(self, global_point):
        point = self._tab_widget.mapFromGlobal(global_point)
        tab_bar = self._tab_widget.tabBar()
        tab_idx = tab_bar.tabAt(point)
        last_index = tab_bar.count() - 1
        if tab_idx < 0 or tab_idx > last_index:
            return

        menu = QtWidgets.QMenu(self._tab_widget)

        add_tab_action = QtWidgets.QAction("Add tab...", menu)
        add_tab_action.setToolTip("Add new tab")

        rename_tab_action = QtWidgets.QAction("Rename...", menu)
        rename_tab_action.setToolTip("Rename tab")

        duplicate_tab_action = QtWidgets.QAction("Duplicate...", menu)
        duplicate_tab_action.setToolTip("Duplicate code to new tab")

        close_tab_action = QtWidgets.QAction("Close", menu)
        close_tab_action.setToolTip("Close tab and lose content")
        close_tab_action.setEnabled(self._tab_widget.tabsClosable())

        menu.addAction(add_tab_action)
        menu.addAction(rename_tab_action)
        menu.addAction(duplicate_tab_action)
        menu.addAction(close_tab_action)

        result = menu.exec_(global_point)
        if result is None:
            return

        if result is rename_tab_action:
            self._rename_tab_req(tab_idx)

        elif result is add_tab_action:
            self._on_add_requested()

        elif result is duplicate_tab_action:
            self._duplicate_requested(tab_idx)

        elif result is close_tab_action:
            self._on_tab_close_req(tab_idx)

    def _rename_tab_req(self, tab_idx):
        dialog = TabNameDialog(self)
        dialog.set_tab_name(self._tab_widget.tabText(tab_idx))
        dialog.exec_()
        tab_name = dialog.result()
        if tab_name:
            self._tab_widget.setTabText(tab_idx, tab_name)

    def _duplicate_requested(self, tab_idx=None):
        if tab_idx is None:
            tab_idx = self._tab_widget.currentIndex()

        src_widget = self._tab_widget.widget(tab_idx)
        dst_widget = self._add_tab()
        if dst_widget is None:
            return
        dst_widget.set_code(src_widget.get_code())

    def _on_tab_mid_click(self, global_point):
        point = self._tab_widget.mapFromGlobal(global_point)
        tab_bar = self._tab_widget.tabBar()
        tab_idx = tab_bar.tabAt(point)
        last_index = tab_bar.count() - 1
        if tab_idx < 0 or tab_idx > last_index:
            return

        self._on_tab_close_req(tab_idx)

    def _on_tab_double_click(self, global_point):
        point = self._tab_widget.mapFromGlobal(global_point)
        tab_bar = self._tab_widget.tabBar()
        tab_idx = tab_bar.tabAt(point)
        last_index = tab_bar.count() - 1
        if tab_idx < 0 or tab_idx > last_index:
            return

        self._rename_tab_req(tab_idx)

    def _on_tab_close_req(self, tab_index):
        if self._tab_widget.count() == 1:
            return

        widget = self._tab_widget.widget(tab_index)
        if widget in self._tabs:
            self._tabs.remove(widget)
        self._tab_widget.removeTab(tab_index)

        if self._tab_widget.count() == 1:
            self._tab_widget.setTabsClosable(False)

    def _append_lines(self, lines):
        at_max = self._output_widget.vertical_scroll_at_max()
        tmp_cursor = QtGui.QTextCursor(self._output_widget.document())
        tmp_cursor.movePosition(QtGui.QTextCursor.End)
        for line in lines:
            tmp_cursor.insertText(line)

        if at_max:
            self._output_widget.scroll_to_bottom()

    def _on_timer_timeout(self):
        if self._stdout_err_wrapper.lines:
            lines = []
            while self._stdout_err_wrapper.lines:
                line = self._stdout_err_wrapper.lines.popleft()
                lines.append(self.ansi_escape.sub("", line))
            self._append_lines(lines)

    def _on_add_requested(self):
        self._add_tab()

    def _add_tab(self):
        dialog = TabNameDialog(self)
        dialog.exec_()
        tab_name = dialog.result()
        if tab_name:
            return self.add_tab(tab_name)

        return None

    def _on_before_execute(self, code_text):
        at_max = self._output_widget.vertical_scroll_at_max()
        document = self._output_widget.document()
        tmp_cursor = QtGui.QTextCursor(document)
        tmp_cursor.movePosition(QtGui.QTextCursor.End)
        tmp_cursor.insertText("{}\nExecuting command:\n".format(20 * "-"))

        code_block_format = QtGui.QTextFrameFormat()
        code_block_format.setBackground(QtGui.QColor(27, 27, 27))
        code_block_format.setPadding(4)

        tmp_cursor.insertFrame(code_block_format)
        char_format = tmp_cursor.charFormat()
        char_format.setForeground(
            QtGui.QBrush(QtGui.QColor(114, 224, 198))
        )
        tmp_cursor.setCharFormat(char_format)
        tmp_cursor.insertText(code_text)

        # Create new cursor
        tmp_cursor = QtGui.QTextCursor(document)
        tmp_cursor.movePosition(QtGui.QTextCursor.End)
        tmp_cursor.insertText("{}\n".format(20 * "-"))

        if at_max:
            self._output_widget.scroll_to_bottom()

    def add_tab(self, tab_name, index=None):
        widget = PythonTabWidget(self)
        widget.before_execute.connect(self._on_before_execute)
        widget.add_tab_requested.connect(self._on_add_requested)
        if index is None:
            if self._tab_widget.count() > 0:
                index = self._tab_widget.currentIndex() + 1
            else:
                index = 0

        self._tabs.append(widget)
        self._tab_widget.insertTab(index, widget, tab_name)
        self._tab_widget.setCurrentIndex(index)

        if self._tab_widget.count() > 1:
            self._tab_widget.setTabsClosable(True)
        widget.setFocus()
        return widget

    def showEvent(self, event):
        self._line_check_timer.start()
        super(PythonInterpreterWidget, self).showEvent(event)
        # First show setup
        if self._first_show:
            self._first_show = False
            self._on_first_show()

        self._output_widget.scroll_to_bottom()

    def _on_first_show(self):
        # Change stylesheet
        self.setStyleSheet(load_stylesheet())
        # Check if splitter size raio is set
        # - first store value to local variable and then unset it
        splitter_size_ratio = self._splitter_size_ratio
        self._splitter_size_ratio = None
        # Skip if is not set
        if not splitter_size_ratio:
            return

        # Skip if number of size items does not match to splitter
        splitters_count = len(self._widgets_splitter.sizes())
        if len(splitter_size_ratio) == splitters_count:
            self._widgets_splitter.setSizes(splitter_size_ratio)

    def closeEvent(self, event):
        self.save_registry()
        super(PythonInterpreterWidget, self).closeEvent(event)
        self._line_check_timer.stop()
