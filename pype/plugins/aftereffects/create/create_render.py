from avalon import api
from avalon.vendor import Qt
from avalon import aftereffects

import logging

log = logging.getLogger(__name__)


class CreateRender(api.Creator):
    """Render folder for publish."""

    name = "renderDefault"
    label = "Render"
    family = "render"

    def process(self):
        # Photoshop can have multiple LayerSets with the same name, which does
        # not work with Avalon.
        txt = "Instance with name \"{}\" already exists.".format(self.name)
        stub = aftereffects.stub()  # only after After Effects is up
        for layer in stub.get_items(comps=True,
                                    folders=False,
                                    footages=False):
            if self.name.lower() == layer.name.lower():
                msg = Qt.QtWidgets.QMessageBox()
                msg.setIcon(Qt.QtWidgets.QMessageBox.Warning)
                msg.setText(txt)
                msg.exec_()
                return False
        log.debug("options:: {}".format(self.options))
        print("options:: {}".format(self.options))
        if (self.options or {}).get("useSelection"):
            log.debug("useSelection")
            print("useSelection")
            items = stub.get_selected_items(comps=True,
                                            folders=False,
                                            footages=False)
        else:
            items = stub.get_items(comps=True,
                                   folders=False,
                                   footages=False)
        log.debug("items:: {}".format(items))
        print("items:: {}".format(items))
        if not items:
            raise ValueError("Nothing to create. Select composition " +
                             "if 'useSelection' or create at least " +
                             "one composition.")

        for item in items:
            stub.imprint(item, self.data)
            stub.set_label_color(item.id, 14)  # Cyan options 0 - 16
