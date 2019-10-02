import os
from pypeapp import config
import pype.maya.lib as mlib
from maya import cmds


print("starting PYPE usersetup")

# build a shelf
presets = config.get_presets()
shelf_preset = presets['maya'].get('project_shelf')


if shelf_preset:
    project = os.environ["AVALON_PROJECT"]

    for i in shelf_preset['imports']:
        import_string = "from {} import {}".format(project, i)
        print(import_string)
        exec(import_string)

cmds.evalDeferred("mlib.shelf(name=shelf_preset['name'], preset=shelf_preset)")


print("finished PYPE usersetup")
