from avalon import api, io
from avalon.nuke import lib as anlib
from avalon.nuke import containerise, update_container
import nuke


class AlembicCameraLoader(api.Loader):
    """
    This will load alembic camera into script.
    """

    families = ["camera"]
    representations = ["abc"]

    label = "Load Alembic Camera"
    icon = "camera"
    color = "orange"
    node_color = "0x3469ffff"

    def load(self, context, name, namespace, data):
        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        fps = version_data.get("fps") or nuke.root()["fps"].getValue()
        namespace = namespace or context['asset']['name']
        object_name = "{}_{}".format(name, namespace)

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["source", "author", "fps"]

        data_imprint = {"frameStart": first,
                        "frameEnd": last,
                        "version": vname,
                        "objectName": object_name}

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = self.fname.replace("\\", "/")

        with anlib.maintained_selection():
            camera_node = nuke.createNode(
                "Camera2",
                "name {} file {} read_from_file True".format(
                    object_name, file),
                inpanel=False
            )
            camera_node.forceValidate()
            camera_node["frame_rate"].setValue(float(fps))

            # workaround because nuke's bug is not adding
            # animation keys properly
            xpos = camera_node.xpos()
            ypos = camera_node.ypos()
            nuke.nodeCopy("%clipboard%")
            nuke.delete(camera_node)
            nuke.nodePaste("%clipboard%")
            camera_node = nuke.toNode(object_name)
            camera_node.setXYpos(xpos, ypos)

        # color node by correct color by actual version
        self.node_version_color(version, camera_node)

        return containerise(
            node=camera_node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__,
            data=data_imprint)
