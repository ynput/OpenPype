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
            active_node = [node for inst in context
                           for node in inst
                           if "ak:family" in node.knobs()]

            if active_node:
                self.log.info(active_node)
                active_node = active_node[0]
                self.log.info(active_node)
                active_node['selected'].setValue(True)

            # select only instance render node
            output_node = nuke.createNode("Output")

            # deselect all and select the original selection
            output_node['selected'].setValue(False)

            # save script
            nuke.scriptSave()

            # add node to instance node list
            context.data["outputNode"] = output_node
