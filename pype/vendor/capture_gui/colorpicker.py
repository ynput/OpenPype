from capture_gui.vendor.Qt import QtCore, QtWidgets, QtGui


class ColorPicker(QtWidgets.QPushButton):
    """Custom color pick button to store and retrieve color values"""

    valueChanged = QtCore.Signal()

    def __init__(self):
        QtWidgets.QPushButton.__init__(self)

        self.clicked.connect(self.show_color_dialog)
        self._color = None

        self.color = [1, 1, 1]

    # region properties
    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, values):
        """Set the color value and update the stylesheet

        Arguments:
            values (list): the color values; red, green, blue

        Returns:
            None

        """
        self._color = values
        self.valueChanged.emit()

        values = [int(x*255) for x in values]
        self.setStyleSheet("background: rgb({},{},{})".format(*values))

    # endregion properties

    def show_color_dialog(self):
        """Display a color picker to change color.

        When a color has been chosen this updates the color of the button
        and its current value

        :return: the red, green and blue values
        :rtype: list
        """
        current = QtGui.QColor()
        current.setRgbF(*self._color)
        colors = QtWidgets.QColorDialog.getColor(current)
        if not colors:
            return
        self.color = [colors.redF(), colors.greenF(), colors.blueF()]
