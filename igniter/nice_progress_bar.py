from Qt import QtCore, QtGui, QtWidgets  # noqa


class NiceProgressBar(QtWidgets.QProgressBar):
    def __init__(self, parent=None):
        super(NiceProgressBar, self).__init__(parent)
        self._real_value = 0

    def setValue(self, value):
        self._real_value = value
        if value != 0 and value < 11:
            value = 11

        super(NiceProgressBar, self).setValue(value)

    def value(self):
        return self._real_value

    def text(self):
        return "{} %".format(self._real_value)
