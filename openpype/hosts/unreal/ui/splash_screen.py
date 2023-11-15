from qtpy import QtWidgets, QtCore, QtGui
from openpype import style, resources


class SplashScreen(QtWidgets.QDialog):
    """Splash screen for executing a process on another thread. It is able
    to inform about the progress of the process and log given information.
    """

    splash_icon = None
    top_label = None
    show_log_btn: QtWidgets.QLabel = None
    progress_bar = None
    log_text: QtWidgets.QLabel = None
    scroll_area: QtWidgets.QScrollArea = None
    close_btn: QtWidgets.QPushButton = None
    scroll_bar: QtWidgets.QScrollBar = None

    is_log_visible = False
    is_scroll_auto = True

    thread_return_code = None
    q_thread: QtCore.QThread = None

    def __init__(self,
                 window_title: str,
                 splash_icon=None,
                 window_icon=None):
        """
        Args:
            window_title (str): String which sets the window title
            splash_icon (str | bytes | None): A resource (pic) which is used
                for the splash icon
            window_icon (str | bytes | None: A resource (pic) which is used for
                the window's icon
        """
        super(SplashScreen, self).__init__()

        if splash_icon is None:
            splash_icon = resources.get_openpype_icon_filepath()

        if window_icon is None:
            window_icon = resources.get_openpype_icon_filepath()

        self.splash_icon = splash_icon
        self.setWindowIcon(QtGui.QIcon(window_icon))
        self.setWindowTitle(window_title)
        self.init_ui()

    def was_proc_successful(self) -> bool:
        return self.thread_return_code == 0

    def start_thread(self, q_thread: QtCore.QThread):
        """Saves the reference to this thread and starts it.

        Args:
            q_thread (QtCore.QThread): A QThread containing a given worker
                (QtCore.QObject)

        Returns:
            None
        """
        if not q_thread:
            raise RuntimeError("Failed to run a worker thread! "
                               "The thread is null!")

        self.q_thread = q_thread
        self.q_thread.start()

    @QtCore.Slot()
    def quit_and_close(self):
        """Quits the thread and closes the splash screen. Note that this means
        the thread has exited with the return code 0!

        Returns:
            None
        """
        self.thread_return_code = 0
        self.q_thread.quit()

        if not self.q_thread.wait(5000):
            raise RuntimeError("Failed to quit the QThread! "
                               "The deadline has been reached! The thread "
                               "has not finished it's execution!.")
        self.close()


    @QtCore.Slot()
    def toggle_log(self):
        if self.is_log_visible:
            self.scroll_area.hide()
            width = self.width()
            self.adjustSize()
            self.resize(width, self.height())
        else:
            self.scroll_area.show()
            self.scroll_bar.setValue(self.scroll_bar.maximum())
            self.resize(self.width(), 300)

        self.is_log_visible = not self.is_log_visible

    def show_ui(self):
        """Shows the splash screen. BEWARE THAT THIS FUNCTION IS BLOCKING
        (The execution of code can not proceed further beyond this function
        until the splash screen is closed!)

        Returns:
            None
        """
        self.show()
        self.exec_()

    def init_ui(self):
        self.resize(450, 100)
        self.setMinimumWidth(250)
        self.setStyleSheet(style.load_stylesheet())

        # Top Section
        self.top_label = QtWidgets.QLabel(self)
        self.top_label.setText("Starting process ...")
        self.top_label.setWordWrap(True)

        icon = QtWidgets.QLabel(self)
        icon.setPixmap(QtGui.QPixmap(self.splash_icon))
        icon.setFixedHeight(45)
        icon.setFixedWidth(45)
        icon.setScaledContents(True)

        self.close_btn = QtWidgets.QPushButton(self)
        self.close_btn.setText("Quit")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setFixedWidth(80)
        self.close_btn.hide()

        self.show_log_btn = QtWidgets.QPushButton(self)
        self.show_log_btn.setText("Show log")
        self.show_log_btn.setFixedWidth(80)
        self.show_log_btn.clicked.connect(self.toggle_log)

        button_layout = QtWidgets.QVBoxLayout()
        button_layout.addWidget(self.show_log_btn)
        button_layout.addWidget(self.close_btn)

        # Progress Bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(QtCore.Qt.AlignTop)

        # Log Content
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.hide()
        log_widget = QtWidgets.QWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOn
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOn
        )
        self.scroll_area.setWidget(log_widget)

        self.scroll_bar = self.scroll_area.verticalScrollBar()
        self.scroll_bar.sliderMoved.connect(self.on_scroll)

        self.log_text = QtWidgets.QLabel(self)
        self.log_text.setText('')
        self.log_text.setAlignment(QtCore.Qt.AlignTop)

        log_layout = QtWidgets.QVBoxLayout(log_widget)
        log_layout.addWidget(self.log_text)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setAlignment(QtCore.Qt.AlignTop)
        top_layout.addWidget(icon)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.top_label)
        top_layout.addSpacing(10)
        top_layout.addLayout(button_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(top_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.progress_bar)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.scroll_area)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        desktop_rect = QtWidgets.QApplication.desktop().availableGeometry(self)
        center = desktop_rect.center()
        self.move(
            center.x() - (self.width() * 0.5),
            center.y() - (self.height() * 0.5)
        )

    @QtCore.Slot(int)
    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    @QtCore.Slot(str)
    def update_top_label_text(self, text: str):
        self.top_label.setText(text)

    @QtCore.Slot(str, str)
    def append_log(self, text: str, end: str = ''):
        """A slot used for receiving log info and appending it to scroll area's
            content.
        Args:
            text (str): A log text that will append to the current one in the
                scroll area.
            end (str): end string which can be appended to the end of the given
                line (for ex. a line break).

        Returns:
            None
        """
        self.log_text.setText(self.log_text.text() + text + end)
        if self.is_scroll_auto:
            self.scroll_bar.setValue(self.scroll_bar.maximum())

    @QtCore.Slot(int)
    def on_scroll(self, position: int):
        """
        A slot for the vertical scroll bar's movement. This ensures the
        auto-scrolling feature of the scroll area when the scroll bar is at its
        maximum value.

        Args:
            position (int): Position value of the scroll bar.

        Returns:
             None
        """
        if self.scroll_bar.maximum() == position:
            self.is_scroll_auto = True
            return

        self.is_scroll_auto = False

    @QtCore.Slot(str, int)
    def fail(self, text: str, return_code: int = 1):
        """
        A slot used for signals which can emit when a worker (process) has
        failed. at this moment the splash screen doesn't close by itself.
        it has to be closed by the user.

        Args:
            text (str): A text which can be set to the top label.

        Returns:
            return_code (int): Return code of the thread's code
        """
        self.top_label.setText(text)
        self.close_btn.show()
        self.thread_return_code = return_code
        self.q_thread.exit(return_code)
        self.q_thread.wait()
