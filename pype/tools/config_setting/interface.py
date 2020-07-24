import os
import sys


def folder_up(path, times=1):
    if times <= 0:
        return path
    return folder_up(os.path.dirname(path), times - 1)


PYPE_SETUP_PATH = folder_up(os.path.realpath(__file__), 6)
os.environ["PYPE_CONFIG"] = os.path.join(
    PYPE_SETUP_PATH, "repos", "pype-config"
)
os.environ["AVALON_MONGO"] = "mongodb://localhost:2707"
sys_paths = (
    "C:/Users/Public/pype_env2/Lib/site-packages",
    PYPE_SETUP_PATH,
    os.path.join(PYPE_SETUP_PATH, "repos", "pype"),
    os.path.join(PYPE_SETUP_PATH, "repos", "avalon-core"),
    os.path.join(PYPE_SETUP_PATH, "repos", "pyblish-base")
)
for path in sys_paths:
    sys.path.append(path)

from widgets import main
import style
from Qt import QtWidgets, QtGui


class MyApp(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super(MyApp, self).__init__(*args, **kwargs)
        stylesheet = style.load_stylesheet()
        self.setStyleSheet(stylesheet)
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))


if __name__ == "__main__":
    app = MyApp(sys.argv)

    # main_widget = QtWidgets.QWidget()
    # main_widget.setWindowIcon(QtGui.QIcon(style.app_icon_path()))
    #
    # layout = QtWidgets.QVBoxLayout(main_widget)
    #
    # widget = main.MainWidget(main_widget)

    # layout.addWidget(widget)
    # main_widget.setLayout(layout)
    # main_widget.show()

    widget = main.MainWidget()
    widget.show()

    sys.exit(app.exec_())
