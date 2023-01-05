import os

import pyblish.api
import openpype.hosts.houdini.api.usd as usdlib


class CollectUsdLayers(pyblish.api.InstancePlugin):
    """Collect the USD Layers that have configured save paths."""

    order = pyblish.api.CollectorOrder + 0.35
    label = "Collect USD Layers"
    hosts = ["houdini"]
    families = ["usd"]

    def process(self, instance):

        output = instance.data.get("output_node")
        if not output:
            self.log.debug("No output node found..")
            return

        rop_node = instance[0]

        save_layers = []
        for layer in usdlib.get_configured_save_layers(rop_node):

            info = layer.rootPrims.get("HoudiniLayerInfo")
            save_path = info.customData.get("HoudiniSavePath")
            creator = info.customData.get("HoudiniCreatorNode")

            self.log.debug("Found configured save path: "
                           "%s -> %s" % (layer, save_path))

            # Log node that configured this save path
            if creator:
                self.log.debug("Created by: %s" % creator)

            save_layers.append((layer, save_path))

        # Store on the instance
        instance.data["usdConfiguredSavePaths"] = save_layers

        # Create configured layer instances so User can disable updating
        # specific configured layers for publishing.
        context = instance.context
        for layer, save_path in save_layers:
            name = os.path.basename(save_path)
            label = "{0} -> {1}".format(instance.data["name"], name)
            layer_inst = context.create_instance(name)

            family = "usdlayer"
            layer_inst.data["family"] = family
            layer_inst.data["families"] = [family]
            layer_inst.data["subset"] = "__stub__"
            layer_inst.data["label"] = label
            layer_inst.data["asset"] = instance.data["asset"]
            layer_inst.append(instance[0])              # include same USD ROP
            layer_inst.append((layer, save_path))       # include layer data

            # Allow this subset to be grouped into a USD Layer on creation
            layer_inst.data["subsetGroup"] = "USD Layer"
