from avalon import api
import maya.app.renderSetup.model.renderSetup as renderSetup
from avalon.maya import lib
from maya import cmds
import json


class RenderSetupLoader(api.Loader):
    """
    This will load json preset for RenderSetup, overwriting current one.
    """

    families = ["rendersetup"]
    representations = ["json"]
    defaults = ['Main']

    label = "Load RenderSetup template"
    icon = "tablet"
    color = "orange"

    def load(self, context, name, namespace, data):

        from avalon.maya.pipeline import containerise
        # from pype.hosts.maya.lib import namespaced

        asset = context['asset']['name']
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        with open(self.fname, "r") as file:
            renderSetup.instance().decode(
                json.load(file), renderSetup.DECODE_AND_OVERWRITE, None)

        nodes = []
        null = cmds.sets(name="null_SET", empty=True)
        nodes.append(null)

        self[:] = nodes
        if not nodes:
            return

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)
