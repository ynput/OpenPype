from Qt import QtCore, QtGui, QtWidgets
from openpype import resources, style


class WidgetUserIdle(QtWidgets.QWidget):
    SIZE_W = 300
    SIZE_H = 160

    def __init__(self, module):
        super(WidgetUserIdle, self).__init__()

        self.bool_is_showed = False
        self.bool_not_stopped = True

        self.module = module
        self.setWindowTitle("OpenPype - Stop timers")

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        self._is_showed = False
        self._timer_stopped = False
        msg_info = "You didn't work for a long time."
        msg_question = "Would you like to stop Timers?"
        msg_stopped = (
            "Your Timers were stopped. Do you want to start them again?"
        )

        lbl_info = QtWidgets.QLabel(msg_info, self)
        lbl_info.setTextFormat(QtCore.Qt.RichText)
        lbl_info.setWordWrap(True)

        lbl_question = QtWidgets.QLabel(msg_question, self)
        lbl_question.setTextFormat(QtCore.Qt.RichText)
        lbl_question.setWordWrap(True)

        lbl_stopped = QtWidgets.QLabel(msg_stopped, self)
        lbl_stopped.setTextFormat(QtCore.Qt.RichText)
        lbl_stopped.setWordWrap(True)

        lbl_rest_time = QtWidgets.QLabel(self)
        lbl_rest_time.setTextFormat(QtCore.Qt.RichText)
        lbl_rest_time.setWordWrap(True)
        lbl_rest_time.setAlignment(QtCore.Qt.AlignCenter)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(10, 15, 10, 5)

        form.addRow(lbl_info)
        form.addRow(lbl_question)
        form.addRow(lbl_stopped)
        form.addRow(lbl_rest_time)

        btn_stop = QtWidgets.QPushButton("Stop timer", self)
        btn_stop.setToolTip("Stop's All timers")

        btn_continue = QtWidgets.QPushButton("Continue", self)
        btn_continue.setToolTip("Timer won't stop")

        btn_close = QtWidgets.QPushButton("Close", self)
        btn_close.setToolTip("Close window")

        btn_restart = QtWidgets.QPushButton("Start timers", self)
        btn_restart.setToolTip("Timer will be started again")

        group_layout = QtWidgets.QHBoxLayout()
        group_layout.addStretch(1)
        group_layout.addWidget(btn_continue)
        group_layout.addWidget(btn_stop)
        group_layout.addWidget(btn_restart)
        group_layout.addWidget(btn_close)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(group_layout)

        self.lbl_info = lbl_info
        self.lbl_question = lbl_question
        self.lbl_stopped = lbl_stopped
        self.lbl_rest_time = lbl_rest_time

        self.btn_stop = btn_stop
        self.btn_continue = btn_continue
        self.btn_close = btn_close
        self.btn_restart = btn_restart

        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))
        self.setStyleSheet(style.load_stylesheet())


    def _refresh_context(self):
        self.lbl_question.setVisible(not self._timer_stopped)
        self.lbl_rest_time.setVisible(not self._timer_stopped)
        self.lbl_stopped.setVisible(self._timer_stopped)

        self.btn_continue.setVisible(not self._timer_stopped)
        self.btn_stop.setVisible(not self._timer_stopped)
        self.btn_restart.setVisible(self._timer_stopped)
        self.btn_close.setVisible(self._timer_stopped)

    def _close_widget(self):
        self._is_showed = False
        self._timer_stopped = False
        self._refresh_context()
        self.hide()

    def showEvent(self, event):
        if not self._is_showed:
            self._is_showed = True
            self._refresh_context()
        super(WidgetUserIdle, self).showEvent(event)

    def closeEvent(self, event):
        event.ignore()
        if self._timer_stopped:
            self._close_widget()
        else:
            self._on_continue_clicked()


class SignalHandler(QtCore.QObject):
    signal_show_message = QtCore.Signal()
    signal_change_label = QtCore.Signal()
    signal_stop_timers = QtCore.Signal()

    def __init__(self, module):
        super(SignalHandler, self).__init__()
        self.module = module
        self.signal_show_message.connect(module.show_message)
        self.signal_change_label.connect(module.change_label)
        self.signal_stop_timers.connect(module.stop_timers)
