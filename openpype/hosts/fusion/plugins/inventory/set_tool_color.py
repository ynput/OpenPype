from avalon import api
from Qt import QtGui, QtWidgets

from openpype import style
from openpype.hosts.fusion.api import (
    get_current_comp,
    comp_lock_and_undo_chunk
)


class FusionSetToolColor(api.InventoryAction):
    """Update the color of the selected tools"""

    label = "Set Tool Color"
    icon = "plus"
    color = "#d8d8d8"
    _fallback_color = QtGui.QColor(1.0, 1.0, 1.0)

    def process(self, containers):
        """Color all selected tools the selected colors"""

        result = []
        comp = get_current_comp()

        # Get tool color
        first = containers[0]
        tool = first["_tool"]
        color = tool.TileColor

        if color is not None:
            qcolor = QtGui.QColor().fromRgbF(color["R"], color["G"], color["B"])
        else:
            qcolor = self._fallback_color

        # Launch pick color
        picked_color = self.get_color_picker(qcolor)
        if not picked_color:
            return

        with comp_lock_and_undo_chunk(comp):
            for container in containers:
                # Convert color to RGB 0-1 floats
                rgb_f = picked_color.getRgbF()
                rgb_f_table = {"R": rgb_f[0], "G": rgb_f[1], "B": rgb_f[2]}

                # Update tool
                tool = container["_tool"]
                tool.TileColor = rgb_f_table

                result.append(container)

        return result

    def get_color_picker(self, color):
        """Launch color picker and return chosen color

        Args:
            color(QtGui.QColor): Start color to display

        Returns:
            QtGui.QColor

        """

        color_dialog = QtWidgets.QColorDialog(color)
        color_dialog.setStyleSheet(style.load_stylesheet())

        accepted = color_dialog.exec_()
        if not accepted:
            return

        return color_dialog.selectedColor()
