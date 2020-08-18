import os
import json

import pyblish.api
from avalon import harmony


class CollectPalettes(pyblish.api.ContextPlugin):
    """Gather palettes from scene when publishing templates."""

    label = "Palettes"
    order = pyblish.api.CollectorOrder
    hosts = ["harmony"]

    def process(self, context):
        func = """function func()
        {
            var palette_list = PaletteObjectManager.getScenePaletteList();

            var palettes = {};
            for(var i=0; i < palette_list.numPalettes; ++i)
            {
                var palette = palette_list.getPaletteByIndex(i);
                palettes[palette.getName()] = palette.id;
            }

            return palettes;
        }
        func
        """
        palettes = harmony.send({"function": func})["result"]
        task = os.getenv("AVALON_TASK", None)
        # basename = os.path.basename(context.data["currentFile"])
        # subset = basename.split("_")[2]
        # if subset == task:
        #     subset = "Main"

        for name, id in palettes.items():
            instance = context.create_instance(name)
            instance.data["publish"] = False
            instance.data.update({
                "id": id,
                "family": "palette",
                "asset": os.environ["AVALON_ASSET"],
                "subset":  "palette" + task.capitalize(),
                "families": ["palette", "ftrack"]
            })
            self.log.info(
                "Created instance:\n" + json.dumps(
                    instance.data, sort_keys=True, indent=4
                )
            )
