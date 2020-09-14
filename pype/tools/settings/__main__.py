import sys

import settings
from Qt import QtWidgets, QtGui


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    stylesheet = settings.style.load_stylesheet()
    app.setStyleSheet(stylesheet)
    app.setWindowIcon(QtGui.QIcon(settings.style.app_icon_path()))

    develop = "-dev" in sys.argv
    widget = settings.MainWidget(develop)
    widget.show()

    sys.exit(app.exec_())
