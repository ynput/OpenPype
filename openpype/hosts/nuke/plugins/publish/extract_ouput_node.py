import nuke
import pyblish.api
from openpype.hosts.nuke.api.lib import maintained_selection


class CreateOutputNode(pyblish.api.ContextPlugin):
    """Adding output node for each output write node
    So when latly user will want to Load .nk as LifeGroup or Precomp
    Nuke will not complain about missing Output node
    """
    label = 'Output Node Create'
    order = pyblish.api.ExtractorOrder + 0.4
    families = ["workfile"]
    hosts = ['nuke']

    def process(self, context):
        # capture selection state
        with maintained_selection():

            active_node = [
                inst.data.get("transientData", {}).get("node")
                for inst in context
                if inst.data.get("transientData", {}).get("node")
                if inst.data.get(
                    "transientData", {}).get("node").Class() != "Root"
            ]

            if active_node:
                active_node = active_node.pop()
                self.log.debug("Active node: {}".format(active_node))
                active_node['selected'].setValue(True)

            # select only instance render node
            output_node = nuke.createNode("Output")

            # deselect all and select the original selection
            output_node['selected'].setValue(False)

            # save script
            nuke.scriptSave()

            # add node to instance node list
            context.data["outputNode"] = output_node
