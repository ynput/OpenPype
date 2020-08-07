import pyblish.api
from avalon.nuke import lib as anlib
from pype.hosts.nuke import lib as pnlib
import nuke
import os
import pype
reload(pnlib)

class ExtractBackdropNode(pype.api.Extractor):
    """Extracting content of backdrop nodes

    Will create nuke script only with containing nodes.
    Also it will solve Input and Output nodes.

    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Backdrop"
    hosts = ["nuke"]
    families = ["nukenodes"]

    def process(self, instance):
        tmp_nodes = list()
        nodes = instance[1:]
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = "{0}.nk".format(instance.name)
        path = os.path.join(stagingdir, filename)

        # maintain selection
        with anlib.maintained_selection():
            # all connections outside of backdrop
            connections_in = instance.data["connections_in"]
            connections_out = instance.data["connections_out"]
            self.log.debug("_ connections_in: `{}`".format(connections_in))
            self.log.debug("_ connections_out: `{}`".format(connections_out))

            # create input nodes and name them as passing node (*_INP)
            for n, inputs in connections_in.items():
                for i, input in inputs:
                    inpn = nuke.createNode("Input")
                    inpn["name"].setValue("{}_{}_INP".format(n.name(), i))
                    n.setInput(i, inpn)
                    inpn.setXYpos(input.xpos(), input.ypos())
                    nodes.append(inpn)
                    tmp_nodes.append(inpn)

            anlib.reset_selection()

            # connect output node
            for n, output in connections_out.items():
                opn = nuke.createNode("Output")
                self.log.info(n.name())
                self.log.info(output.name())
                output.setInput(
                    next((i for i, d in enumerate(output.dependencies())
                          if d.name() in n.name()), 0), opn)
                opn.setInput(0, n)
                opn.autoplace()
                nodes.append(opn)
                tmp_nodes.append(opn)
                anlib.reset_selection()

            # select nodes to copy
            anlib.reset_selection()
            anlib.select_nodes(nodes)
            # create tmp nk file
            # save file to the path
            nuke.nodeCopy(path)

            # Clean up
            for tn in tmp_nodes:
                nuke.delete(tn)

            # restore original connections
            # reconnect input node
            for n, inputs in connections_in.items():
                for i, input in inputs:
                    n.setInput(i, input)

            # reconnect output node
            for n, output in connections_out.items():
                output.setInput(
                    next((i for i, d in enumerate(output.dependencies())
                          if d.name() in n.name()), 0), n)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        # create representation
        representation = {
            'name': 'nk',
            'ext': 'nk',
            'files': filename,
            "stagingDir": stagingdir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '{}' to: {}".format(
            instance.name, path))

        self.log.info("Data {}".format(
            instance.data))
