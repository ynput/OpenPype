import os
import shutil
import uuid

from bson.objectid import ObjectId

from avalon import api, harmony


class ImportPaletteLoader(api.Loader):
    """Import palettes."""

    families = ["harmony.palette"]
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
        name += "_{}".format(uuid.uuid4())

        # Import new palette.
        scene_path = harmony.send(
            {"function": "scene.currentProjectPath"}
        )["result"]
        src = api.get_representation_path(representation)
        dst = os.path.join(
            scene_path,
            "palette-library",
            "{}.plt".format(name)
        )
        shutil.copy(src, dst)

        func = """function func(args)
        {
            var palette_list = PaletteObjectManager.getScenePaletteList();
            var palette = palette_list.addPaletteAtLocation(
                PaletteObjectManager.Constants.Location.SCENE, 0, args[0]
            );
            for(var i=0; i < palette_list.numPalettes; ++i)
            {
                palette_list.movePaletteUp(palette.id);
            }
            return palette.id;
        }
        func
        """
        harmony.send({"function": func, "args": [name]})

        return name

    def remove(self, container):
        # Replace any palettes with same name.
        func = """function func(args)
        {
            var pom = PaletteObjectManager;
            var palette_list = pom.getScenePaletteList();
            for(var i=0; i < palette_list.numPalettes; ++i)
            {
                var palette = palette_list.getPaletteByIndex(i);
                if(palette.getName() == args[0])
                    pom.removePaletteReferencesAndDeleteOnDisk(palette.id);
            }
        }
        func
        """
        harmony.send({"function": func, "args": [container["name"]]})

        harmony.remove(container["name"])

        harmony.save_scene()

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        self.remove(container)
        name = self.load_palette(representation)

        container["representation"] = str(representation["_id"])
        container["name"] = name
        harmony.imprint(name, container)
