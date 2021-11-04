from maya import cmds
from avalon import maya
from openpype.plugins.load.abstract_load_template import AbstractTemplateLoader


class TemplateLoader(AbstractTemplateLoader):
    """Import action for Maya (unmanaged)

    Warning:
        The loaded content will be unmanaged and is *not* visible in the
        scene inventory. It's purely intended to merge content into your scene
        so you could also use it as a new base.

    """
    representations = ["ma", "mb"]
    families = ["*"]

    label = "Import"
    order = 10
    icon = "arrow-circle-down"
    color = "#775555"

    def load_template(self):

        choice = self.display_warning()
        if choice is False:
            return

        with maya.maintained_selection():
            cmds.file(
                self.template_path,
                i=True,
                preserveReferences=True,
                returnNewNodes=True,
                groupReference=True,
            )

    def load(self, context, name=None, namespace=None, data=None):

        # super().load(context, name, namespace, data)

        choice = self.display_warning()
        if choice is False:
            return

        return

    def display_warning(self):
        """Show warning to ensure the user can't import models by accident

        Returns:
            bool

        """
        return True  # Court circuit ici
        # TODO: Recoder le display warning pour vérifier task in progress,
        # les publish manquant, etc
        from avalon.vendor.Qt import QtWidgets

        accept = QtWidgets.QMessageBox.Ok
        buttons = accept | QtWidgets.QMessageBox.Cancel

        message = "Are you sure you want import this"
        state = QtWidgets.QMessageBox.warning(None,
                                              "Are you sure?",
                                              message,
                                              buttons=buttons,
                                              defaultButton=accept)

        return state == accept
