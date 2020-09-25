from avalon import api
import nuke
from pprint import pformat

class AlembicCameraLoader(api.Loader):
    """
    This will load alembic camera into script.
    """

    families = ["camera"]
    representations = ["abc"]

    label = "Load Alembic Camera"
    icon = "camera"
    color = "orange"

    def load(self, context, name, namespace, data):

        # import dependencies
        from avalon.nuke import containerise

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
        add_keys = ["frameStart", "frameEnd", "source", "author", "fps"]

        data_imprint = {"frameStart": first,
                        "frameEnd": last,
                        "version": vname,
                        "objectName": object_name}

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = self.fname.replace("\\", "/")

        camera_node = nuke.createNode(
            "Camera2",
            "file {} read_from_file True".format(file),
            inpanel=False
        )
        camera_node.forceValidate()
        # camera_node["read_from_file"].setValue(True)
        # camera_node["file"].setValue(file)
        camera_node["frame_rate"].setValue(float(fps))
        camera_node["tile_color"].setValue(int("0x3469ffff", 16))

        return containerise(
            node=camera_node,
            name=name,
            namespace=namespace,
            context=context,
            loader=self.__class__.__name__,
            data=data_imprint)
