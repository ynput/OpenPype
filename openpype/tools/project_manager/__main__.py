import sys

from project_manager import Window

from Qt import QtWidgets


def main():
    app = QtWidgets.QApplication([])

    window = Window()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
