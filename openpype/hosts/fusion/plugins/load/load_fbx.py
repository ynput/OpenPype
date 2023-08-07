from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.fusion.api import (
    imprint_container,
    get_current_comp,
    comp_lock_and_undo_chunk,
)


class FusionLoadFBXMesh(load.LoaderPlugin):
    """Load FBX mesh into Fusion"""

    families = ["*"]
    representations = ["*"]
    extensions = {
        "3ds",
        "amc",
        "aoa",
        "asf",
        "bvh",
        "c3d",
        "dae",
        "dxf",
        "fbx",
        "htr",
        "mcd",
        "obj",
        "trc",
    }

    label = "Load FBX mesh"
    order = -10
    icon = "code-fork"
    color = "orange"

    tool_type = "SurfaceFBXMesh"

    def load(self, context, name, namespace, data):
        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context["asset"]["name"]

        # Create the Loader with the filename path set
        comp = get_current_comp()
        with comp_lock_and_undo_chunk(comp, "Create tool"):
            path = self.filepath_from_context(context)

            args = (-32768, -32768)
            tool = comp.AddTool(self.tool_type, *args)
            tool["ImportFile"] = path

            imprint_container(
                tool,
                name=name,
                namespace=namespace,
                context=context,
                loader=self.__class__.__name__,
            )

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Update path"""

        tool = container["_tool"]
        assert tool.ID == self.tool_type, f"Must be {self.tool_type}"
        comp = tool.Comp()

        path = get_representation_path(representation)

        with comp_lock_and_undo_chunk(comp, "Update tool"):
            tool["ImportFile"] = path

            # Update the imprinted representation
            tool.SetData("avalon.representation", str(representation["_id"]))

    def remove(self, container):
        tool = container["_tool"]
        assert tool.ID == self.tool_type, f"Must be {self.tool_type}"
        comp = tool.Comp()

        with comp_lock_and_undo_chunk(comp, "Remove tool"):
            tool.Delete()
