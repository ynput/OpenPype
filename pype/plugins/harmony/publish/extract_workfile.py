import os
import shutil

from avalon import harmony

import pype.api
import pype.hosts.harmony


class ExtractWorkfile(pype.api.Extractor):
    """Extract the connected nodes to the composite instance."""

    label = "Extract Workfile"
    hosts = ["harmony"]
    families = ["workfile"]

    def process(self, instance):
        # Export template.
        backdrops = harmony.send(
            {"function": "Backdrop.backdrops", "args": ["Top"]}
        )["result"]
        nodes = harmony.send(
            {"function": "node.subNodes", "args": ["Top"]}
        )["result"]
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, "{}.tpl".format(instance.name))

        pype.hosts.harmony.export_template(backdrops, nodes, filepath)

        # Prep representation.
        os.chdir(staging_dir)
        shutil.make_archive(
            "{}".format(instance.name),
            "zip",
            os.path.join(staging_dir, "{}.tpl".format(instance.name))
        )

        representation = {
            "name": "tpl",
            "ext": "zip",
            "files": "{}.zip".format(instance.name),
            "stagingDir": staging_dir
        }
        instance.data["representations"] = [representation]
