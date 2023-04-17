import os

import pyblish.api

from openpype.pipeline import (
    publish,
    OptionalPyblishPluginMixin
)
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractOpenGL(publish.Extractor,
                    OptionalPyblishPluginMixin):

    order = pyblish.api.ExtractorOrder - 0.01
    label = "Extract OpenGL"
    families = ["review"]
    hosts = ["houdini"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        ropnode = hou.node(instance.data.get("instance_node"))

        output = ropnode.evalParm("picture")
        staging_dir = os.path.normpath(os.path.dirname(output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        self.log.info("Extracting '%s' to '%s'" % (file_name,
                                                   staging_dir))

        render_rop(ropnode)

        output = instance.data["frames"]

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        representation = {
            "name": instance.data["imageFormat"],
            "ext": instance.data["imageFormat"],
            "files": output,
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "tags": tags,
            "preview": True,
            "camera_name": instance.data.get("review_camera")
        }

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(representation)
