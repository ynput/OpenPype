if __name__ == "__main__":
    import sys
    from Qt import QtWidgets

    app = QtWidgets.QApplication([])

    window = ProjectManagerWindow()
    window.show()

    sys.exit(app.exec_())