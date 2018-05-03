from avalon import api
from avalon.vendor.Qt import QtGui, QtWidgets

import avalon.fusion


class FusionSetToolColor(api.InventoryAction):
    """Update the color of the selected tools"""

    label = "Set Tool Color"
    icon = "plus"
    color = "#d8d8d8"
    _fallback_color = QtGui.QColor(1.0, 1.0, 1.0)

    def process(self, containers):
        """Color all selected tools the selected colors"""

        comp = avalon.fusion.get_current_comp()

        # Launch pick color
        first = containers[0]
        color = QtGui.QColor(first.get("color", self._fallback_color))
        picked_color = QtWidgets.QColorDialog().getColor(color)
        with avalon.fusion.comp_lock_and_undo_chunk(comp):
            for container in containers:
                # Convert color to RGB 0-1 floats
                rgb_f = picked_color.getRgbF()
                rgb_f_table = {"R": rgb_f[0], "G": rgb_f[1], "B": rgb_f[2]}

                # Update tool
                tool = container["_tool"]
                tool.TileColor = rgb_f_table

        self.refresh()

    def refresh(self):
        """Refresh Scene Inventory window"""

        app = QtWidgets.QApplication.instance()
        widgets = dict((w.objectName(), w) for w in app.allWidgets())
        widget = widgets.get("SceneInventory")
        widget.refresh()
