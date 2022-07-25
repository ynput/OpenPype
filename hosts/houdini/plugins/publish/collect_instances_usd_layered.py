import hou
import pyblish.api
from openpype.hosts.houdini.api import lib
import openpype.hosts.houdini.api.usd as hou_usdlib
import openpype.lib.usdlib as usdlib


class CollectInstancesUsdLayered(pyblish.api.ContextPlugin):
    """Collect Instances from a ROP Network and its configured layer paths.

    The output nodes of the ROP node will only be published when *any* of the
    layers remain set to 'publish' by the user.

    This works differently from most of our Avalon instances in the pipeline.
    As opposed to storing `pyblish.avalon.instance` as id on the node we store
    `pyblish.avalon.usdlayered`.

    Additionally this instance has no need for storing family, asset, subset
    or name on the nodes. Instead all information is retrieved solely from
    the output filepath, which is an Avalon URI:
        avalon://{asset}/{subset}.{representation}

    Each final ROP node is considered a dependency for any of the Configured
    Save Path layers it sets along the way. As such, the instances shown in
    the Pyblish UI are solely the configured layers. The encapsulating usd
    files are generated whenever *any* of the dependencies is published.

    These dependency instances are stored in:
        instance.data["publishDependencies"]

    """

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect Instances (USD Configured Layers)"
    hosts = ["houdini"]

    def process(self, context):

        stage = hou.node("/stage")
        if not stage:
            # Likely Houdini version <18
            return

        nodes = stage.recursiveGlob("*", filter=hou.nodeTypeFilter.Rop)
        for node in nodes:

            if not node.parm("id"):
                continue

            if node.evalParm("id") != "pyblish.avalon.usdlayered":
                continue

            has_family = node.evalParm("family")
            assert has_family, "'%s' is missing 'family'" % node.name()

            self.process_node(node, context)

        def sort_by_family(instance):
            """Sort by family"""
            return instance.data.get("families", instance.data.get("family"))

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=sort_by_family)

        return context

    def process_node(self, node, context):

        # Allow a single ROP node or a full ROP network of USD ROP nodes
        # to be processed as a single entry that should "live together" on
        # a publish.
        if node.type().name() == "ropnet":
            # All rop nodes inside ROP Network
            ropnodes = node.recursiveGlob("*", filter=hou.nodeTypeFilter.Rop)
        else:
            # A single node
            ropnodes = [node]

        data = lib.read(node)

        # Don't use the explicit "colorbleed.usd.layered" family for publishing
        # instead use the "colorbleed.usd" family to integrate.
        data["publishFamilies"] = ["colorbleed.usd"]

        # For now group ALL of them into USD Layer subset group
        # Allow this subset to be grouped into a USD Layer on creation
        data["subsetGroup"] = "USD Layer"

        instances = list()
        dependencies = []
        for ropnode in ropnodes:

            # Create a dependency instance per ROP Node.
            lopoutput = ropnode.evalParm("lopoutput")
            dependency_save_data = self.get_save_data(lopoutput)
            dependency = context.create_instance(dependency_save_data["name"])
            dependency.append(ropnode)
            dependency.data.update(data)
            dependency.data.update(dependency_save_data)
            dependency.data["family"] = "colorbleed.usd.dependency"
            dependency.data["optional"] = False
            dependencies.append(dependency)

            # Hide the dependency instance from the context
            context.pop()

            # Get all configured layers for this USD ROP node
            # and create a Pyblish instance for each one
            layers = hou_usdlib.get_configured_save_layers(ropnode)
            for layer in layers:
                save_path = hou_usdlib.get_layer_save_path(layer)
                save_data = self.get_save_data(save_path)
                if not save_data:
                    continue
                self.log.info(save_path)

                instance = context.create_instance(save_data["name"])
                instance[:] = [node]

                # Set the instance data
                instance.data.update(data)
                instance.data.update(save_data)
                instance.data["usdLayer"] = layer

                # Don't allow the Pyblish `instanceToggled` we have installed
                # to set this node to bypass.
                instance.data["_allowToggleBypass"] = False

                instances.append(instance)

        # Store the collected ROP node dependencies
        self.log.debug("Collected dependencies: %s" % (dependencies,))
        for instance in instances:
            instance.data["publishDependencies"] = dependencies

    def get_save_data(self, save_path):

        # Resolve Avalon URI
        uri_data = usdlib.parse_avalon_uri(save_path)
        if not uri_data:
            self.log.warning("Non Avalon URI Layer Path: %s" % save_path)
            return {}

        # Collect asset + subset from URI
        name = "{subset} ({asset})".format(**uri_data)
        fname = "{asset}_{subset}.{ext}".format(**uri_data)

        data = dict(uri_data)
        data["usdSavePath"] = save_path
        data["usdFilename"] = fname
        data["name"] = name
        return data
