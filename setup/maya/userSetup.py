import os
import sys
from pypeapp import config
from pype.maya import lib
reload(lib)

presets = config.get_presets()
shelf_preset = presets['maya']['project_shelf']
project = os.environ["AVALON_PROJECT"]

modules = {}
for k, v in shelf_preset['imports'].items():
    sys.modules[k] = __import__(v, fromlist=[project])

projectShelf = lib.shelf(name=shelf_preset['name'], preset=shelf_preset)
