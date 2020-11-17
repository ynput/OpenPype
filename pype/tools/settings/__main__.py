import sys

import settings
from Qt import QtWidgets, QtGui


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    stylesheet = settings.style.load_stylesheet()
    app.setStyleSheet(stylesheet)
    app.setWindowIcon(QtGui.QIcon(settings.style.app_icon_path()))

    _develop = "-d" in sys.argv or "--develop" in sys.argv
    _user = "-m" in sys.argv or "--manager" in sys.argv
    if _develop:
        user_role = "developer"
    elif _user:
        user_role = "manager"
    else:
        user_role = "artist"

    widget = settings.MainWidget(user_role)
    widget.show()

    sys.exit(app.exec_())
