from avalon import api
from avalon.vendor.Qt import QtGui, QtWidgets

import avalon.fusion


class FusionSelectLoaderColor(api.InventoryAction):

    label = "Select Loader Color"
    icon = "plus"
    color = "#d8d8d8"

    def process(self, containers):

        comp = avalon.fusion.get_current_comp()

        # Get color of selected container
        _tool = containers[0]["_tool"]
        table = _tool.TileColor
        if table:
            color = QtGui.QColor.fromRgbF(table["R"], table["G"], table["B"])
        else:
            color = QtGui.QColor.fromRgbF(0.0, 0.0, 0.0)

        # Launch pick color
        picked_color = QtWidgets.QColorDialog().getColor(color)
        with avalon.fusion.comp_lock_and_undo_chunk(comp):
            for container in containers:
                # Convert color to 0-1 floats
                rgb_f = picked_color.getRgbF()
                rgb_f_table = {"R": rgb_f[0], "G": rgb_f[1], "B": rgb_f[2]}

                # Update tool
                tool = container["_tool"]
                tool.TileColor = rgb_f_table
