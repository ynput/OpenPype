import copy
import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop
from openpype.hosts.houdini.api.usd import remap_paths

import hou


class ExtractUSD(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract USD"
    hosts = ["houdini"]
    families = ["usd",
                "usdModel",
                "usdSetDress"]

    def process(self, instance):

        # TODO: Clean this up - for now this is used for runtime upstream
        #   instances (explicit save path layers) from `collect_usd_layers.py`
        if not instance.data.get("render", True):
            return

        ropnode = hou.node(instance.data.get("instance_node"))

        # Get the filename from the filename parameter
        output = ropnode.evalParm("lopoutput")
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        self.log.info("Writing USD '%s' to '%s'" % (file_name, staging_dir))

        mapping = self.get_source_to_publish_paths(instance.context)
        with remap_paths(ropnode, mapping):
            render_rop(ropnode)

        assert os.path.exists(output), "Output does not exist: %s" % output

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'usd',
            'ext': 'usd',
            'files': file_name,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

    def get_source_to_publish_paths(self, context):
        """Define a mapping of all current instances in context from source
        file to publish file so this can be used on the USD save to remap
        asset layer paths on publish via AyonRemapPaths output processor"""

        mapping = {}
        for instance in context:

            if not instance.data.get("active", True):
                continue

            if not instance.data.get("publish", True):
                continue

            for repre in instance.data.get("representations", []):
                name = repre.get("name")
                ext = repre.get("ext")

                # TODO: The remapping might need to get more involved if the
                #   asset paths that are set use e.g. $F
                # TODO: If the representation has multiple files we might need
                #   to define the path remapping per file of the sequence
                path = get_instance_expected_output_path(
                    instance, representation_name=name, ext=ext
                )
                for source_path in get_source_paths(instance, repre):
                    source_path = os.path.normpath(source_path)
                    mapping[source_path] = path

        return mapping


def get_source_paths(instance, repre):
    """Return the full source filepath for an instance's representations"""

    staging = repre.get("stagingDir", instance.data.get("stagingDir"))
    files = repre.get("files", [])
    if isinstance(files, list):
        return [os.path.join(staging, fname) for fname in files]
    else:
        # Single file
        return [os.path.join(staging, files)]


def get_instance_expected_output_path(instance, representation_name, ext=None):
    """Return expected publish filepath for representation in instance"""

    if ext is None:
        ext = representation_name

    context = instance.context
    anatomy = context.data["anatomy"]
    path_template_obj = anatomy.templates_obj["publish"]["path"]
    template_data = copy.deepcopy(instance.data["anatomyData"])
    template_data.update({
        "ext": ext,
        "representation": representation_name,
        "subset": instance.data["subset"],
        "asset": instance.data["asset"],
        "variant": instance.data.get("variant"),
        "version": instance.data["version"]
    })

    template_filled = path_template_obj.format_strict(template_data)
    return os.path.normpath(template_filled)
