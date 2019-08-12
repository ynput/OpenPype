import nuke
import pyblish.api
from avalon.nuke import maintained_selection

class CreateOutputNode(pyblish.api.ContextPlugin):
    """Adding output node for each ouput write node
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
            # deselect all allNodes
            self.log.info(context.data["ActiveViewer"])

            active_viewer = context.data["ActiveViewer"]
            active_input = active_viewer.activeInput()
            active_node = active_viewer.node()


            last_viewer_node = active_node.input(active_input)

            name = last_viewer_node.name()
            self.log.info("Node name: {}".format(name))

            # select only instance render node
            last_viewer_node['selected'].setValue(True)
            output_node = nuke.createNode("Output")

            # deselect all and select the original selection
            output_node['selected'].setValue(False)

            # save script
            nuke.scriptSave()

            # add node to instance node list
            context.data["outputNode"] = output_node
