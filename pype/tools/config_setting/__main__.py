import sys

import config_setting
from Qt import QtWidgets, QtGui


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    stylesheet = config_setting.style.load_stylesheet()
    app.setStyleSheet(stylesheet)
    app.setWindowIcon(QtGui.QIcon(config_setting.style.app_icon_path()))

    develop = "-dev" in sys.argv
    widget = config_setting.MainWidget(develop)
    widget.show()

    sys.exit(app.exec_())
