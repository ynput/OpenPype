import os
import shutil

from openpype.pipeline import (
    load,
    get_representation_path,
)
import openpype.hosts.harmony.api as harmony


class ImportPaletteLoader(load.LoaderPlugin):
    """Import palettes."""

    families = ["palette", "harmony.palette"]
    representations = ["plt"]
    label = "Import Palette"

    def load(self, context, name=None, namespace=None, data=None):
        name = self.load_palette(context["representation"])

        return harmony.containerise(
            name,
            namespace,
            name,
            context,
            self.__class__.__name__
        )

    def load_palette(self, representation):
        subset_name = representation["context"]["subset"]
        name = subset_name.replace("palette", "")

        # Overwrite palette on disk.
        scene_path = harmony.send(
            {"function": "scene.currentProjectPath"}
        )["result"]
        src = get_representation_path(representation)
        dst = os.path.join(
            scene_path,
            "palette-library",
            "{}.plt".format(name)
        )
        shutil.copy(src, dst)

        harmony.save_scene()

        msg = "Updated {}.".format(subset_name)
        msg += " You need to reload the scene to see the changes.\n"
        msg += "Please save workfile when ready and use Workfiles "
        msg += "to reopen it."

        harmony.send(
            {
                "function": "PypeHarmony.message",
                "args": msg
            })
        return name

    def remove(self, container):
        harmony.remove(container["name"])

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        self.remove(container)
        name = self.load_palette(representation)

        container["representation"] = str(representation["_id"])
        container["name"] = name
        harmony.imprint(name, container)
