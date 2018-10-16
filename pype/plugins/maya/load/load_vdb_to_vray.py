from avalon import api


class LoadVDBtoVRay(api.Loader):

    families = ["studio.vdbcache"]
    representations = ["vdb"]

    label = "Load VDB to VRay"
    icon = "cloud"
    color = "orange"

    def load(self, context, name, namespace, data):

        from maya import cmds
        import avalon.maya.lib as lib
        from avalon.maya.pipeline import containerise

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
