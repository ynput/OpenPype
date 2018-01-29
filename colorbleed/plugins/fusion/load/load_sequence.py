from avalon import api
import fusionless
import fusionless.context as fuCtx
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

        from avalon.fusion.pipeline import imprint_container

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        # Use the first file for now
        root = self.fname
        files = os.listdir(root)
        path = os.path.join(root, files[0])

        # Create the Loader with the filename path set
        comp = fusionless.Comp()
        with fuCtx.lock_and_undo_chunk(comp, "Create Loader"):
            tool = comp.create_tool("Loader")
            tool.input("Clip").set_value(path)

            imprint_container(tool,
                              name=name,
                              namespace=namespace,
                              context=context,
                              loader=self.__class__.__name__)
