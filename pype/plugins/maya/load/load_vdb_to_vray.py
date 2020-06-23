from avalon import api
from pype.api import config
import os


class LoadVDBtoVRay(api.Loader):

    families = ["vdbcache"]
    representations = ["vdb"]

    label = "Load VDB to VRay"
    icon = "cloud"
    color = "orange"

    def load(self, context, name, namespace, data):

        from maya import cmds
        import avalon.maya.lib as lib
        from avalon.maya.pipeline import containerise

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vdbcache"

        # Check if viewport drawing engine is Open GL Core (compat)
        render_engine = None
        compatible = "OpenGLCoreProfileCompat"
        if cmds.optionVar(exists="vp2RenderingEngine"):
            render_engine = cmds.optionVar(query="vp2RenderingEngine")

        if not render_engine or render_engine != compatible:
            raise RuntimeError("Current scene's settings are incompatible."
                               "See Preferences > Display > Viewport 2.0 to "
                               "set the render engine to '%s'" % compatible)

        asset = context['asset']
        version = context["version"]

        asset_name = asset["name"]
        namespace = namespace or lib.unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(root + ".useOutlinerColor", 1)
            cmds.setAttr(root + ".outlinerColor",
                         c[0], c[1], c[2])

        # Create VR
        grid_node = cmds.createNode("VRayVolumeGrid",
                                    name="{}VVGShape".format(label),
                                    parent=root)

        # Set attributes
        cmds.setAttr("{}.inFile".format(grid_node), self.fname, type="string")
        cmds.setAttr("{}.inReadOffset".format(grid_node),
                     version["startFrames"])

        nodes = [root, grid_node]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)
