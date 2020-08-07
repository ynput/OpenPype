from avalon import style
from Qt import QtCore, QtGui, QtWidgets


class WidgetUserIdle(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 160

    def __init__(self, module, tray_widget):

        super(WidgetUserIdle, self).__init__()

        self.bool_is_showed = False
        self.bool_not_stopped = True

        self.module = module
        self.setWindowIcon(tray_widget.icon)
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        self._translate = QtCore.QCoreApplication.translate

        self.font = QtGui.QFont()
        self.font.setFamily("DejaVu Sans Condensed")
        self.font.setPointSize(9)
        self.font.setBold(True)
        self.font.setWeight(50)
        self.font.setKerning(True)

        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._main())
        self.refresh_context()
        self.setWindowTitle('Pype - Stop timers')

    def _main(self):
        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName('main')

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName('form')

        msg_info = 'You didn\'t work for a long time.'
        msg_question = 'Would you like to stop Timers?'
        msg_stopped = (
            'Your Timers were stopped. Do you want to start them again?'
        )

        self.lbl_info = QtWidgets.QLabel(msg_info)
        self.lbl_info.setFont(self.font)
        self.lbl_info.setTextFormat(QtCore.Qt.RichText)
        self.lbl_info.setObjectName("lbl_info")
        self.lbl_info.setWordWrap(True)

        self.lbl_question = QtWidgets.QLabel(msg_question)
        self.lbl_question.setFont(self.font)
        self.lbl_question.setTextFormat(QtCore.Qt.RichText)
        self.lbl_question.setObjectName("lbl_question")
        self.lbl_question.setWordWrap(True)

        self.lbl_stopped = QtWidgets.QLabel(msg_stopped)
        self.lbl_stopped.setFont(self.font)
        self.lbl_stopped.setTextFormat(QtCore.Qt.RichText)
        self.lbl_stopped.setObjectName("lbl_stopped")
        self.lbl_stopped.setWordWrap(True)

        self.lbl_rest_time = QtWidgets.QLabel("")
        self.lbl_rest_time.setFont(self.font)
        self.lbl_rest_time.setTextFormat(QtCore.Qt.RichText)
        self.lbl_rest_time.setObjectName("lbl_rest_time")
        self.lbl_rest_time.setWordWrap(True)
        self.lbl_rest_time.setAlignment(QtCore.Qt.AlignCenter)

        self.form.addRow(self.lbl_info)
        self.form.addRow(self.lbl_question)
        self.form.addRow(self.lbl_stopped)
        self.form.addRow(self.lbl_rest_time)

        self.group_btn = QtWidgets.QHBoxLayout()
        self.group_btn.addStretch(1)
        self.group_btn.setObjectName("group_btn")

        self.btn_stop = QtWidgets.QPushButton("Stop timer")
        self.btn_stop.setToolTip('Stop\'s All timers')
        self.btn_stop.clicked.connect(self.stop_timer)

        self.btn_continue = QtWidgets.QPushButton("Continue")
        self.btn_continue.setToolTip('Timer won\'t stop')
        self.btn_continue.clicked.connect(self.continue_timer)

        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_close.setToolTip('Close window')
        self.btn_close.clicked.connect(self.close_widget)

        self.btn_restart = QtWidgets.QPushButton("Start timers")
        self.btn_restart.setToolTip('Timer will be started again')
        self.btn_restart.clicked.connect(self.restart_timer)

        self.group_btn.addWidget(self.btn_continue)
        self.group_btn.addWidget(self.btn_stop)
        self.group_btn.addWidget(self.btn_restart)
        self.group_btn.addWidget(self.btn_close)

        self.main.addLayout(self.form)
        self.main.addLayout(self.group_btn)

        return self.main

    def refresh_context(self):
        self.lbl_question.setVisible(self.bool_not_stopped)
        self.lbl_rest_time.setVisible(self.bool_not_stopped)
        self.lbl_stopped.setVisible(not self.bool_not_stopped)

        self.btn_continue.setVisible(self.bool_not_stopped)
        self.btn_stop.setVisible(self.bool_not_stopped)
        self.btn_restart.setVisible(not self.bool_not_stopped)
        self.btn_close.setVisible(not self.bool_not_stopped)

    def change_count_widget(self, time):
        str_time = str(time)
        self.lbl_rest_time.setText(str_time)

    def stop_timer(self):
        self.module.stop_timers()
        self.close_widget()

    def restart_timer(self):
        self.module.restart_timers()
        self.close_widget()

    def continue_timer(self):
        self.close_widget()

    def closeEvent(self, event):
        event.ignore()
        if self.bool_not_stopped is True:
            self.continue_timer()
        else:
            self.close_widget()

    def close_widget(self):
        self.bool_is_showed = False
        self.bool_not_stopped = True
        self.refresh_context()
        self.hide()

    def showEvent(self, event):
        self.bool_is_showed = True


class SignalHandler(QtCore.QObject):
    signal_show_message = QtCore.Signal()
    signal_change_label = QtCore.Signal()
    signal_stop_timers = QtCore.Signal()

    def __init__(self, cls):
        super().__init__()
        self.signal_show_message.connect(cls.show_message)
        self.signal_change_label.connect(cls.change_label)
        self.signal_stop_timers.connect(cls.stop_timers)
