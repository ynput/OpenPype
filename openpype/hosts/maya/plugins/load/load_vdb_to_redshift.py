import os

from openpype.api import get_project_settings
from openpype.pipeline import load


class LoadVDBtoRedShift(load.LoaderPlugin):
    """Load OpenVDB in a Redshift Volume Shape"""

    families = ["vdbcache"]
    representations = ["vdb"]

    label = "Load VDB to RedShift"
    icon = "cloud"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        from maya import cmds
        from openpype.hosts.maya.api.pipeline import containerise
        from openpype.hosts.maya.api.lib import unique_namespace

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vdbcache"

        # Check if the plugin for redshift is available on the pc
        try:
            cmds.loadPlugin("redshift4maya", quiet=True)
        except Exception as exc:
            self.log.error("Encountered exception:\n%s" % exc)
            return

        # Check if viewport drawing engine is Open GL Core (compat)
        render_engine = None
        compatible = "OpenGL"
        if cmds.optionVar(exists="vp2RenderingEngine"):
            render_engine = cmds.optionVar(query="vp2RenderingEngine")

        if not render_engine or not render_engine.startswith(compatible):
            raise RuntimeError("Current scene's settings are incompatible."
                               "See Preferences > Display > Viewport 2.0 to "
                               "set the render engine to '%s<type>'"
                               % compatible)

        asset = context['asset']

        asset_name = asset["name"]
        namespace = namespace or unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        colors = settings['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(root + ".useOutlinerColor", 1)
            cmds.setAttr(root + ".outlinerColor",
                (float(c[0])/255),
                (float(c[1])/255),
                (float(c[2])/255)
            )

        # Create VR
        volume_node = cmds.createNode("RedshiftVolumeShape",
                                      name="{}RVSShape".format(label),
                                      parent=root)

        cmds.setAttr("{}.fileName".format(volume_node),
                     self.fname,
                     type="string")

        nodes = [root, volume_node]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)
