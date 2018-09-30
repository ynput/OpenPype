from avalon import api, style
from avalon.vendor.Qt import QtGui, QtWidgets

import avalon.nuke


class NukeSetToolColor(api.InventoryAction):
    """Update the color of the selected tools"""

    label = "Set Tool Color"
    icon = "plus"
    color = "#d8d8d8"
    _fallback_color = QtGui.QColor(1.0, 1.0, 1.0)

    def process(self, containers):
        """Color all selected tools the selected colors"""

        result = []

        # Get tool color
        first = containers[0]
        node = first["_tool"]
        color = node["tile_color"].value()
        hex = '%08x' % color
        rgba = [
            float(int(hex[0:2], 16)) / 255.0,
            float(int(hex[2:4], 16)) / 255.0,
            float(int(hex[4:6], 16)) / 255.0
        ]

        if color is not None:
            qcolor = QtGui.QColor().fromRgbF(rgba[0], rgba[1], rgba[2])
        else:
            qcolor = self._fallback_color

        # Launch pick color
        picked_color = self.get_color_picker(qcolor)
        if not picked_color:
            return

        with avalon.nuke.viewer_update_and_undo_stop():
            for container in containers:
                # Convert color to RGB 0-1 floats
                rgb_f = picked_color.getRgbF()
                hexColour = int(
                    '%02x%02x%02x%02x' % (
                        rgb_f[0]*255,
                        rgb_f[1]*255,
                        rgb_f[2]*255,
                        1),
                    16
                )
                # Update tool
                node = container["_tool"]
                node['tile_color'].value(hexColour)

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
