import copy
import os
import re

import pyblish.api

from openpype.pipeline.create import get_subset_name
from openpype.client import get_asset_by_name
import openpype.hosts.houdini.api.usd as usdlib

import hou


def copy_instance_data(instance_src, instance_dest, attr):
    """Copy instance data from `src` instance to `dest` instance.

    Examples:
        >>> copy_instance_data(instance_src, instance_dest,
        >>>                    attr="publish_attributes.CollectRopFrameRange")

    Arguments:
        instance_src (pyblish.api.Instance): Source instance to copy from
        instance_dest (pyblish.api.Instance): Target instance to copy to
        attr (str): Attribute on the source instance to copy. This can be
            a nested key joined by `.` to only copy sub entries of dictionaries
            in the source instance's data.

    Raises:
        KeyError: If the key does not exist on the source instance.
        AssertionError: If a parent key already exists on the destination
            instance but is not of the correct type (= is not a dict)

    """

    src_data = instance_src.data
    dest_data = instance_dest.data
    keys = attr.split(".")
    for i, key in enumerate(keys):
        if key not in src_data:
            break

        src_value = src_data[key]
        if i != len(key):
            dest_data = dest_data.setdefault(key, {})
            assert isinstance(dest_data, dict), "Destination must be a dict"
            src_data = src_value
        else:
            # Last iteration - assign the value
            dest_data[key] = copy.deepcopy(src_value)


class CollectUsdLayers(pyblish.api.InstancePlugin):
    """Collect the USD Layers that have configured save paths."""

    order = pyblish.api.CollectorOrder + 0.35
    label = "Collect USD Layers"
    hosts = ["houdini"]
    families = ["usd"]

    def process(self, instance):
        # TODO: Replace this with a Hidden Creator so we collect these BEFORE
        #   starting the publish so the user sees them before publishing
        #   - however user should not be able to individually enable/disable
        #   this from the main ROP its created from?

        output = instance.data.get("output_node")
        if not output:
            self.log.debug("No output node found..")
            return

        rop_node = hou.node(instance.data["instance_node"])

        save_layers = []
        for layer in usdlib.get_configured_save_layers(rop_node):

            info = layer.rootPrims.get("HoudiniLayerInfo")
            save_path = info.customData.get("HoudiniSavePath")
            creator = info.customData.get("HoudiniCreatorNode")
            self.log.info(info.customData)

            self.log.debug("Found configured save path: "
                           "%s -> %s", layer, save_path)

            # Log node that configured this save path
            creator_node = hou.nodeBySessionId(creator) if creator else None
            if creator_node:
                self.log.debug(
                    "Created by: %s", creator_node.path()
                )

            save_layers.append((layer, save_path, creator_node))

        # Store on the instance
        instance.data["usdConfiguredSavePaths"] = save_layers

        # Create configured layer instances so User can disable updating
        # specific configured layers for publishing.
        context = instance.context
        for layer, save_path, creator_node in save_layers:
            name = os.path.basename(save_path)
            layer_inst = context.create_instance(name)

            # include same USD ROP
            layer_inst.append(rop_node)

            staging_dir, fname = os.path.split(save_path)
            fname_no_ext, ext = os.path.splitext(fname)

            variant = fname_no_ext

            # Strip off any trailing version number in the form of _v[0-9]+
            variant = re.sub("_v[0-9]+$", "", variant)

            layer_inst.data["usd_layer"] = layer
            layer_inst.data["usd_layer_save_path"] = save_path

            project_name = context.data["projectName"]
            asset_doc = get_asset_by_name(project_name,
                                          asset_name=instance.data["asset"])
            variant_base = instance.data["variant"]
            subset = get_subset_name(
                family="usd",
                variant=variant_base + "_" + variant,
                task_name=context.data["anatomyData"]["task"]["name"],
                asset_doc=asset_doc,
                project_name=project_name,
                host_name=context.data["hostName"],
                project_settings=context.data["project_settings"]
            )

            label = "{0} -> {1}".format(instance.data["name"], subset)
            family = "usd"
            layer_inst.data["family"] = family
            layer_inst.data["families"] = [family]
            layer_inst.data["subset"] = subset
            layer_inst.data["label"] = label
            layer_inst.data["asset"] = instance.data["asset"]
            layer_inst.data["instance_node"] = instance.data["instance_node"]
            layer_inst.data["render"] = False
            layer_inst.data["output_node"] = creator_node

            # Inherit "use handles" from the source instance
            # TODO: Do we want to maybe copy full `publish_attributes` instead?
            copy_instance_data(
                instance, layer_inst,
                attr="publish_attributes.CollectRopFrameRange.use_handles"
            )

            # Allow this subset to be grouped into a USD Layer on creation
            layer_inst.data["subsetGroup"] = "USD Layer"

            # For now just assume the representation will get published
            representation = {
                "name": "usd",
                "ext": ext.lstrip("."),
                "stagingDir": staging_dir,
                "files": fname
            }
            layer_inst.data.setdefault("representations", []).append(
                representation)
