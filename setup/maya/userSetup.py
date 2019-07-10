import os
import sys
from pypeapp import config
from pype.maya import lib
from maya import cmds

def build_shelf():
    presets = config.get_presets()
    shelf_preset = presets['maya'].get('project_shelf')
    if shelf_preset:
        project = os.environ["AVALON_PROJECT"]

        for k, v in shelf_preset['imports'].items():
            sys.modules[k] = __import__(v, fromlist=[project])

        lib.shelf(name=shelf_preset['name'], preset=shelf_preset)

cmds.evalDeferred("build_shelf()")
