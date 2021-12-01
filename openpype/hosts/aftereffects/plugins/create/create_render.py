import openpype.api
from Qt import QtWidgets
from avalon import aftereffects

import logging

log = logging.getLogger(__name__)


class CreateRender(openpype.api.Creator):
    """Render folder for publish.

        Creates subsets in format 'familyTaskSubsetname',
        eg 'renderCompositingMain'.

        Create only single instance from composition at a time.
    """

    name = "renderDefault"
    label = "Render on Farm"
    family = "render"

    def process(self):
        stub = aftereffects.stub()  # only after After Effects is up
        if (self.options or {}).get("useSelection"):
            items = stub.get_selected_items(comps=True,
                                            folders=False,
                                            footages=False)
        if len(items) > 1:
            self._show_msg("Please select only single composition at time.")
            return False

        if not items:
            self._show_msg("Nothing to create. Select composition " +
                           "if 'useSelection' or create at least " +
                           "one composition.")
            return False

        existing_subsets = [instance['subset'].lower()
                            for instance in aftereffects.list_instances()]

        item = items.pop()
        if self.name.lower() in existing_subsets:
            txt = "Instance with name \"{}\" already exists.".format(self.name)
            self._show_msg(txt)
            return False

        self.data["members"] = [item.id]
        self.data["uuid"] = item.id  # for SubsetManager
        self.data["subset"] = self.data["subset"]\
            .replace(stub.PUBLISH_ICON, '')\
            .replace(stub.LOADED_ICON, '')

        stub.imprint(item, self.data)
        stub.set_label_color(item.id, 14)  # Cyan options 0 - 16
        stub.rename_item(item.id, stub.PUBLISH_ICON + self.data["subset"])

    def _show_msg(self, txt):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText(txt)
        msg.exec_()
