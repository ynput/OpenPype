import os
import sys
import app
import signal
from Qt import QtWidgets
from avalon import style


if __name__ == "__main__":
    qt_app = QtWidgets.QApplication([])
    # app.setQuitOnLastWindowClosed(False)
    qt_app.setStyleSheet(style.load_stylesheet())

    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        qt_app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    window = app.Window(sys.argv[-1].split(os.pathsep))
    window.show()

    sys.exit(qt_app.exec_())
