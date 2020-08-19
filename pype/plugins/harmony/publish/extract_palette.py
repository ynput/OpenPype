import os

from avalon import harmony
import pype.api
import pype.hosts.harmony


class ExtractPalette(pype.api.Extractor):
    """Extract palette."""

    label = "Extract Palette"
    hosts = ["harmony"]
    families = ["harmony.palette"]

    def process(self, instance):
        func = """function func(args)
        {
            var palette_list = PaletteObjectManager.getScenePaletteList();
            var palette = palette_list.getPaletteById(args[0]);
            return (palette.getPath() + "/" + palette.getName() + ".plt");
        }
        func
        """
        palette_file = harmony.send(
            {"function": func, "args": [instance.data["id"]]}
        )["result"]

        representation = {
            "name": "plt",
            "ext": "plt",
            "files": os.path.basename(palette_file),
            "stagingDir": os.path.dirname(palette_file)
        }
        instance.data["representations"] = [representation]
