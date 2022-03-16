import os

from openpype.api import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)

from maya import cmds

# List of 3rd Party Channels Mapping names for VRayVolumeGrid
# See: https://docs.chaosgroup.com/display/VRAY4MAYA/Input
#      #Input-3rdPartyChannelsMapping
THIRD_PARTY_CHANNELS = {
    2: "Smoke",
    1: "Temperature",
    10: "Fuel",
    4: "Velocity.x",
    5: "Velocity.y",
    6: "Velocity.z",
    7: "Red",
    8: "Green",
    9: "Blue",
    14: "Wavelet Energy",
    19: "Wavelet.u",
    20: "Wavelet.v",
    21: "Wavelet.w",
    # These are not in UI or documentation but V-Ray does seem to set these.
    15: "AdvectionOrigin.x",
    16: "AdvectionOrigin.y",
    17: "AdvectionOrigin.z",

}


def _fix_duplicate_vvg_callbacks():
    """Workaround to kill duplicate VRayVolumeGrids attribute callbacks.

    This fixes a huge lag in Maya on switching 3rd Party Channels Mappings
    or to different .vdb file paths because it spams an attribute changed
    callback: `vvgUserChannelMappingsUpdateUI`.

    ChaosGroup bug ticket: 154-008-9890

    Found with:
        - Maya 2019.2 on Windows 10
        - V-Ray: V-Ray Next for Maya, update 1 version 4.12.01.00001

    Bug still present in:
        - Maya 2022.1 on Windows 10
        - V-Ray 5 for Maya, Update 2.1 (v5.20.01 from Dec 16 2021)

    """
    # todo(roy): Remove when new V-Ray release fixes duplicate calls

    jobs = cmds.scriptJob(listJobs=True)

    matched = set()
    for entry in jobs:
        # Remove the number
        index, callback = entry.split(":", 1)
        callback = callback.strip()

        # Detect whether it is a `vvgUserChannelMappingsUpdateUI`
        # attribute change callback
        if callback.startswith('"-runOnce" 1 "-attributeChange" "'):
            if '"vvgUserChannelMappingsUpdateUI(' in callback:
                if callback in matched:
                    # If we've seen this callback before then
                    # delete the duplicate callback
                    cmds.scriptJob(kill=int(index))
                else:
                    matched.add(callback)


class LoadVDBtoVRay(load.LoaderPlugin):

    families = ["vdbcache"]
    representations = ["vdb"]

    label = "Load VDB to VRay"
    icon = "cloud"
    color = "orange"

    def load(self, context, name, namespace, data):

        from openpype.hosts.maya.api.lib import unique_namespace
        from openpype.hosts.maya.api.pipeline import containerise

        assert os.path.exists(self.fname), (
            "Path does not exist: %s" % self.fname
        )

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vdbcache"

        # Ensure V-ray is loaded with the vrayvolumegrid
        if not cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            cmds.loadPlugin("vrayformaya")
        if not cmds.pluginInfo("vrayvolumegrid", query=True, loaded=True):
            cmds.loadPlugin("vrayvolumegrid")

        # Check if viewport drawing engine is Open GL Core (compat)
        render_engine = None
        compatible = "OpenGLCoreProfileCompat"
        if cmds.optionVar(exists="vp2RenderingEngine"):
            render_engine = cmds.optionVar(query="vp2RenderingEngine")

        if not render_engine or render_engine != compatible:
            self.log.warning("Current scene's settings are incompatible."
                             "See Preferences > Display > Viewport 2.0 to "
                             "set the render engine to '%s'" % compatible)

        asset = context['asset']
        asset_name = asset["name"]
        namespace = namespace or unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Root group
        label = "{}:{}_VDB".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        colors = settings['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(root + ".useOutlinerColor", 1)
            cmds.setAttr(root + ".outlinerColor",
                         float(c[0]) / 255,
                         float(c[1]) / 255,
                         float(c[2]) / 255)

        # Create VRayVolumeGrid
        grid_node = cmds.createNode("VRayVolumeGrid",
                                    name="{}Shape".format(label),
                                    parent=root)

        # Ensure .currentTime is connected to time1.outTime
        cmds.connectAttr("time1.outTime", grid_node + ".currentTime")

        # Set path
        self._set_path(grid_node, self.fname, show_preset_popup=True)

        # Lock the shape node so the user can't delete the transform/shape
        # as if it was referenced
        cmds.lockNode(grid_node, lock=True)

        nodes = [root, grid_node]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def _set_path(self, grid_node, path, show_preset_popup=True):

        from openpype.hosts.maya.api.lib import attribute_values
        from maya import cmds

        def _get_filename_from_folder(path):
            # Using the sequence of .vdb files we check the frame range, etc.
            # to set the filename with #### padding.
            files = sorted(x for x in os.listdir(path) if x.endswith(".vdb"))
            if not files:
                raise RuntimeError("Couldn't find .vdb files in: %s" % path)

            if len(files) == 1:
                # Ensure check for single file is also done in folder
                fname = files[0]
            else:
                # Sequence
                import clique
                # todo: check support for negative frames as input
                collections, remainder = clique.assemble(files)
                assert len(collections) == 1, (
                    "Must find a single image sequence, "
                    "found: %s" % (collections,)
                )
                collection = collections[0]

                fname = collection.format('{head}{{padding}}{tail}')
                padding = collection.padding
                if padding == 0:
                    # Clique doesn't provide padding if the frame number never
                    # starts with a zero and thus has never any visual padding.
                    # So we fall back to the smallest frame number as padding.
                    padding = min(len(str(i)) for i in collection.indexes)

                # Supply frame/padding with # signs
                padding_str = "#" * padding
                fname = fname.format(padding=padding_str)

            return os.path.join(path, fname)

        # The path is either a single file or sequence in a folder so
        # we do a quick lookup for our files
        if os.path.isfile(path):
            path = os.path.dirname(path)
        path = _get_filename_from_folder(path)

        # Even when not applying a preset V-Ray will reset the 3rd Party
        # Channels Mapping of the VRayVolumeGrid when setting the .inPath
        # value. As such we try and preserve the values ourselves.
        # Reported as ChaosGroup bug ticket: 154-011-2909 
        # todo(roy): Remove when new V-Ray release preserves values
        original_user_mapping = cmds.getAttr(grid_node + ".usrchmap") or ""

        # Workaround for V-Ray bug: fix lag on path change, see function
        _fix_duplicate_vvg_callbacks()

        # Suppress preset pop-up if we want.
        popup_attr = "{0}.inDontOfferPresets".format(grid_node)
        popup = {popup_attr: not show_preset_popup}
        with attribute_values(popup):
            cmds.setAttr(grid_node + ".inPath", path, type="string")

        # Reapply the 3rd Party channels user mapping when no preset popup
        # was shown to the user
        if not show_preset_popup:
            channels = cmds.getAttr(grid_node + ".usrchmapallch").split(";")
            channels = set(channels)  # optimize lookup
            restored_mapping = ""
            for entry in original_user_mapping.split(";"):
                if not entry:
                    # Ignore empty entries
                    continue

                # If 3rd Party Channels selection channel still exists then
                # add it again.
                index, channel = entry.split(",")
                attr = THIRD_PARTY_CHANNELS.get(int(index),
                                                # Fallback for when a mapping
                                                # was set that is not in the
                                                # documentation
                                                "???")
                if channel in channels:
                    restored_mapping += entry + ";"
                else:
                    self.log.warning("Can't preserve '%s' mapping due to "
                                     "missing channel '%s' on node: "
                                     "%s" % (attr, channel, grid_node))

            if restored_mapping:
                cmds.setAttr(grid_node + ".usrchmap",
                             restored_mapping,
                             type="string")

    def update(self, container, representation):

        path = get_representation_path(representation)

        # Find VRayVolumeGrid
        members = cmds.sets(container['objectName'], query=True)
        grid_nodes = cmds.ls(members, type="VRayVolumeGrid", long=True)
        assert len(grid_nodes) > 0, "This is a bug"

        # Update the VRayVolumeGrid
        for grid_node in grid_nodes:
            self._set_path(grid_node, path=path, show_preset_popup=False)

        # Update container representation
        cmds.setAttr(container["objectName"] + ".representation",
                     str(representation["_id"]),
                     type="string")

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):

        # Get all members of the avalon container, ensure they are unlocked
        # and delete everything
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
