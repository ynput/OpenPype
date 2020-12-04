from avalon import api
from avalon.vendor import Qt
from avalon import aftereffects

import logging

log = logging.getLogger(__name__)


class CreateRender(api.Creator):
    """Render folder for publish."""

    name = "renderDefault"
    label = "Render on Farm"
    family = "render"

    def process(self):
        stub = aftereffects.stub()  # only after After Effects is up
        if (self.options or {}).get("useSelection"):
            items = stub.get_selected_items(comps=True,
                                            folders=False,
                                            footages=False)
        else:
            self._show_msg("Please select only single composition at time.")
            return False

        if not items:
            self._show_msg("Nothing to create. Select composition " +
                           "if 'useSelection' or create at least " +
                           "one composition.")
            return False

        for item in items:
            txt = "Instance with name \"{}\" already exists.".format(self.name)
            if self.name.lower() == item.name.lower():
                self._show_msg(txt)
                return False
            self.data["members"] = [item.id]
            stub.imprint(item, self.data)
            stub.set_label_color(item.id, 14)  # Cyan options 0 - 16
            stub.rename_item(item, self.data["subset"])

    def _show_msg(self, txt):
        msg = Qt.QtWidgets.QMessageBox()
        msg.setIcon(Qt.QtWidgets.QMessageBox.Warning)
        msg.setText(txt)
        msg.exec_()
