import os

import nuke
import pyblish.api


class Extract(pyblish.api.InstancePlugin):
    """Super class for write and writegeo extractors."""

    order = pyblish.api.ExtractorOrder
    optional = True
    label = "Extract Nuke [super]"
    hosts = ["nuke"]
    match = pyblish.api.Subset

    # targets = ["process.local"]

    def execute(self, instance):
        # Get frame range
        node = instance[0]
        first_frame = nuke.root()["first_frame"].value()
        last_frame = nuke.root()["last_frame"].value()

        if node["use_limit"].value():
            first_frame = node["first"].value()
            last_frame = node["last"].value()

        # Render frames
        nuke.execute(node.name(), int(first_frame), int(last_frame))


class ExtractNukeWrite(Extract):
    """ Extract output from write nodes. """

    families = ["write", "local"]
    label = "Extract Write"

    def process(self, instance):

        self.execute(instance)

        # Validate output
        for filename in list(instance.data["collection"]):
            if not os.path.exists(filename):
                instance.data["collection"].remove(filename)
                self.log.warning("\"{0}\" didn't render.".format(filename))


class ExtractNukeCache(Extract):

    label = "Cache"
    families = ["cache", "local"]

    def process(self, instance):

        self.execute(instance)

        # Validate output
        msg = "\"{0}\" didn't render.".format(instance.data["output_path"])
        assert os.path.exists(instance.data["output_path"]), msg


class ExtractNukeCamera(Extract):

    label = "Camera"
    families = ["camera", "local"]

    def process(self, instance):

        node = instance[0]
        node["writeGeometries"].setValue(False)
        node["writePointClouds"].setValue(False)
        node["writeAxes"].setValue(False)

        file_path = node["file"].getValue()
        node["file"].setValue(instance.data["output_path"])

        self.execute(instance)

        node["writeGeometries"].setValue(True)
        node["writePointClouds"].setValue(True)
        node["writeAxes"].setValue(True)

        node["file"].setValue(file_path)

        # Validate output
        msg = "\"{0}\" didn't render.".format(instance.data["output_path"])
        assert os.path.exists(instance.data["output_path"]), msg


class ExtractNukeGeometry(Extract):

    label = "Geometry"
    families = ["geometry", "local"]

    def process(self, instance):

        node = instance[0]
        node["writeCameras"].setValue(False)
        node["writePointClouds"].setValue(False)
        node["writeAxes"].setValue(False)

        file_path = node["file"].getValue()
        node["file"].setValue(instance.data["output_path"])

        self.execute(instance)

        node["writeCameras"].setValue(True)
        node["writePointClouds"].setValue(True)
        node["writeAxes"].setValue(True)

        node["file"].setValue(file_path)

        # Validate output
        msg = "\"{0}\" didn't render.".format(instance.data["output_path"])
        assert os.path.exists(instance.data["output_path"]), msg
