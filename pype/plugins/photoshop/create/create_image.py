from avalon import api, photoshop
from avalon.vendor import Qt


class CreateImage(api.Creator):
    """Image folder for publish."""

    name = "imageDefault"
    label = "Image"
    family = "image"

    def process(self):
        groups = []
        layers = []
        create_group = False
        group_constant = photoshop.get_com_objects().constants().psLayerSet
        if (self.options or {}).get("useSelection"):
            multiple_instances = False
            selection = photoshop.get_selected_layers()

            if len(selection) > 1:
                # Ask user whether to create one image or image per selected
                # item.
                msg_box = Qt.QtWidgets.QMessageBox()
                msg_box.setIcon(Qt.QtWidgets.QMessageBox.Warning)
                msg_box.setText(
                    "Multiple layers selected."
                    "\nDo you want to make one image per layer?"
                )
                msg_box.setStandardButtons(
                    Qt.QtWidgets.QMessageBox.Yes |
                    Qt.QtWidgets.QMessageBox.No |
                    Qt.QtWidgets.QMessageBox.Cancel
                )
                ret = msg_box.exec_()
                if ret == Qt.QtWidgets.QMessageBox.Yes:
                    multiple_instances = True
                elif ret == Qt.QtWidgets.QMessageBox.Cancel:
                    return

                if multiple_instances:
                    for item in selection:
                        if item.LayerType == group_constant:
                            groups.append(item)
                        else:
                            layers.append(item)
                else:
                    group = photoshop.group_selected_layers()
                    group.Name = self.name
                    groups.append(group)

            elif len(selection) == 1:
                # One selected item. Use group if its a LayerSet (group), else
                # create a new group.
                if selection[0].LayerType == group_constant:
                    groups.append(selection[0])
                else:
                    layers.append(selection[0])
            elif len(selection) == 0:
                # No selection creates an empty group.
                create_group = True
        else:
            create_group = True

        if create_group:
            group = photoshop.app().ActiveDocument.LayerSets.Add()
            group.Name = self.name
            groups.append(group)

        for layer in layers:
            photoshop.select_layers([layer])
            group = photoshop.group_selected_layers()
            group.Name = layer.Name
            groups.append(group)

        for group in groups:
            photoshop.imprint(group, self.data)
