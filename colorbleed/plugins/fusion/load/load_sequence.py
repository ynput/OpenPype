from avalon import api
import os


class FusionLoadSequence(api.Loader):
    """Load image sequence into Fusion"""

    families = ["colorbleed.imagesequence"]
    representations = ["*"]

    label = "Load sequence"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):

        from avalon.fusion import (
            imprint_container,
            get_current_comp,
            comp_lock_and_undo_chunk
        )

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        # Use the first file for now
        path = self._get_first_image(self.fname)

        # Create the Loader with the filename path set
        comp = get_current_comp()
        with comp_lock_and_undo_chunk(comp, "Create Loader"):

            args = (-32768, -32768)
            tool = comp.AddTool("Loader", *args)
            tool["Clip"] = path

            imprint_container(tool,
                              name=name,
                              namespace=namespace,
                              context=context,
                              loader=self.__class__.__name__)

    def _get_first_image(self, root):
        """Get first file in representation root"""
        files = sorted(os.listdir(root))
        return os.path.join(root, files[0])

    def update(self, container, representation):
        """Update the Loader's path

        Fusion automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:
            - ClipTimeStart (if duration changes)
            - ClipTimeEnd (if duration changes)
            - GlobalIn (if duration changes)
            - GlobalEnd (if duration changes)
            - Reverse (sometimes?)
            - Loop (sometimes?)
            - Depth (always resets to "Format")
            - KeyCode (always resets to "")
            - TimeCodeOffset (always resets to 0)

        """

        from avalon.fusion import comp_lock_and_undo_chunk

        root = api.get_representation_path(representation)
        path = self._get_first_image(root)

        tool = container["_tool"]
        assert tool.ID == "Loader", "Must be Loader"
        comp = tool.Comp()

        with comp_lock_and_undo_chunk(comp, "Update Loader"):
            tool["Clip"] = path

            # Update the imprinted representation
            tool.SetData("avalon.representation", str(representation["_id"]))

    def remove(self, container):

        from avalon.fusion import comp_lock_and_undo_chunk

        tool = container["_tool"]
        assert tool.ID == "Loader", "Must be Loader"
        comp = tool.Comp()
        with comp_lock_and_undo_chunk(comp, "Remove Loader"):
            tool.Delete()
