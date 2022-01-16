import avalon.api
from .launch_logic import get_stub


class AfterEffectsLoader(avalon.api.Loader):
    @staticmethod
    def get_stub():
        return get_stub()


# @iLLiCiTiT QUESTION is this used anywhere?
class Creator(avalon.api.Creator):
    """Creator plugin to create instances in After Effects

    A LayerSet is created to support any number of layers in an instance. If
    the selection is used, these layers will be added to the LayerSet.
    """

    def process(self):
        # Photoshop can have multiple LayerSets with the same name, which does
        # not work with Avalon.
        txt = "Instance with name \"{}\" already exists.".format(self.name)
        stub = get_stub()  # only after After Effects is up
        for layer in stub.get_items(
            comps=True, folders=False, footages=False
        ):
            if self.name.lower() == layer.name.lower():
                from Qt import QtWidgets

                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setText(txt)
                msg.exec_()
                return False

        if (self.options or {}).get("useSelection"):
            items = stub.get_selected_items(
                comps=True, folders=False, footages=False
            )
        else:
            items = stub.get_items(
                comps=True, folders=False, footages=False
            )

        for item in items:
            stub.imprint(item, self.data)
