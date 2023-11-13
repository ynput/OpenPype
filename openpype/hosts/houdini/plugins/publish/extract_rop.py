import pyblish.api

from openpype.hosts.houdini.api.lib import render_rop, get_sorted_rops

import hou


class ExtractROPs(pyblish.api.ContextPlugin):
    """Extract all ROP nodes in order of dependency

    All the active instances' ROP nodes will be sorted by their input
    dependency networks. This way they will render dependencies first.

    Note that dependencies that are not publish instances will *also* be
    rendered. Each dependency is only ever triggered once.

    """

    order = pyblish.api.ExtractorOrder
    label = "Extract ROPs"
    hosts = ["houdini"]
    families = ["*"]

    def process(self, context):

        # Get all ROP instances
        rop_path_to_instance = {}
        rop_nodes = []
        for instance in context:
            if not instance.data.get("instance_node"):
                continue

            if not instance.data.get("publish", True):
                continue

            if not instance.data.get("active", True):
                continue

            if instance.data.get("farm", False):
                # TODO: Currently these will still render however if they
                #   are an input dependency to another ROP instance node to
                #   be rendered this publish session
                self.log.debug(
                    "Ignoring instance %s as it is marked "
                    "for farm rendering...", instance
                )
                continue

            rop_path = instance.data["instance_node"]
            rop_path_to_instance[rop_path] = instance
            rop_nodes.append(hou.node(rop_path))

        sorted_rops = get_sorted_rops(rop_nodes)

        # Log rendering order for debugging
        self.log.debug("Defined rendering order:")
        for i, rop in enumerate(sorted_rops):
            self.log.debug("    %i. %s", i, rop.path())

        for rop in sorted_rops:
            instance = rop_path_to_instance.get(rop.path())
            try:
                self.render_rop(rop, instance)
            except Exception as exc:
                raise RuntimeError(f"Failed to render instance: {instance}") from exc  # noqa: E501

    def render_rop(self, ropnode, instance):
        """Render a single ROP node"""
        self.log.debug("Rendering %s", ropnode.path())

        # Render
        render_rop(ropnode,
                   # We will render them in order ourselves to avoid multiple
                   # nodes having the same dependency but not being in the same
                   # full node tree to process the node twice
                   ignore_inputs=True)

        if instance is None:
            # The ROP node does not belong to an instance and was likely a
            # dependency to another ROP node in an instance or it may have
            # been a disabled instance.
            self.log.debug("Skipping representation for ROP node without "
                           "instance: %s", ropnode.path())
            return

        # Create representation using data collected
        # by `collect_frames` and `collect_asset_handles`
        repre_name = instance.data["representation_name"]
        files = instance.data["frames"]
        representation = {
            "name": repre_name,
            "ext": instance.data["representation_ext"],
            "files": files,
            "stagingDir": instance.data["stagingDir"],
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"]
        }
        instance.data.setdefault("representations", []).append(representation)

        # Log debug message
        num_files = len(files) if isinstance(files, (list, tuple)) else 1
        files_label = "file" if num_files == 1 else "files"
        self.log.debug(
            "Instance %s added representation '%s' with %i %s from '%s'",
            instance, repre_name, num_files, files_label, ropnode.path()
        )
