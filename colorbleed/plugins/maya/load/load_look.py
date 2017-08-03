import os
import json

from maya import cmds
from avalon import api, maya
import colorbleed.maya.lib as lib


class LookLoader(api.Loader):
    """Specific loader for lookdev"""

    families = ["colorbleed.lookdev"]
    representations = ["ma"]

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):
        """
        Load and try to ssign Lookdev to nodes based on relationship data
        Args:
            name:
            namespace:
            context:
            data:

        Returns:

        """

        # improve readability of the namespace
        assetname = context["asset"]["name"]
        ns_assetname = "{}_".format(assetname)

        namespace = maya.unique_namespace(ns_assetname,
                                          format="%03d",
                                          suffix="_look")

        # try / except here is to ensure that the get_reference_node
        # does not fail when the file doesn't exist yet
        reference_node = None
        try:
            reference_node = lib.get_reference_node(self.fname)
        except:
            pass

        if reference_node is None:
            self.log.info("Loading lookdev for the first time ...")
            with maya.maintained_selection():
                nodes = cmds.file(self.fname,
                                  namespace=namespace,
                                  reference=True,
                                  returnNewNodes=True)
        else:
            self.log.info("Reusing existing lookdev ...")
            nodes = cmds.referenceQuery(reference_node, nodes=True)

        # Assign shaders
        self.fname = self.fname.rsplit(".", 1)[0] + ".json"
        if not os.path.isfile(self.fname):
            self.log.warning("Look development asset "
                             "has no relationship data.")
            return nodes

        with open(self.fname) as f:
            relationships = json.load(f)

        # Get all nodes which belong to a matching name space
        # Currently this is the safest way to get all the nodes
        lib.apply_shaders(relationships, nodes)

        self[:] = nodes
