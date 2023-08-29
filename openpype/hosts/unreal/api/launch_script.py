import os
import sys
import signal
import traceback
import ctypes
import platform
import logging

from Qt import QtWidgets, QtCore, QtGui

from openpype.hosts.unreal.api.communication_server import (
    CommunicationWrapper
)
from openpype.hosts.unreal.api import UnrealHost
from openpype.pipeline import install_host
from openpype.tools.utils import get_openpype_qt_app
from openpype import style

logging.basicConfig(level=logging.DEBUG)


def safe_excepthook(*args):
    traceback.print_exception(*args)


def main(launch_args):

    # Be sure server won't crash at any moment but just print traceback
    sys.excepthook = safe_excepthook

    # Create QtApplication for tools
    # - QApplicaiton is also main thread/event loop of the server
    qt_app = get_openpype_qt_app()

    unreal_host = UnrealHost()
    install_host(unreal_host)

    # Create Communicator object and trigger launch
    # - this must be done before anything is processed
    communicator = CommunicationWrapper.create_qt_communicator(qt_app)
    communicator.launch(launch_args)

    # subprocess.Popen(launch_args)

    def process_in_main_thread():
        """Execution of `MainThreadItem`."""
        item = communicator.main_thread_listen()
        if item:
            item.execute()

    timer = QtCore.QTimer()
    timer.setInterval(100)
    timer.timeout.connect(process_in_main_thread)
    timer.start()

    # Register terminal signal handler
    def signal_handler(*_args):
        print("You pressed Ctrl+C. Process ended.")
        communicator.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setStyleSheet(style.load_stylesheet())

    # Load avalon icon
    icon_path = style.app_icon_path()
    if icon_path:
        icon = QtGui.QIcon(icon_path)
        qt_app.setWindowIcon(icon)

    # Set application name to be able show application icon in task bar
    if platform.system().lower() == "windows":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            u"WebsocketServer"
        )

    # Run Qt application event processing
    sys.exit(qt_app.exec_())


if __name__ == "__main__":
    args = list(sys.argv)
    if os.path.abspath(__file__) == os.path.normpath(args[0]):
        # Pop path to script
        args.pop(0)
    main(args)
