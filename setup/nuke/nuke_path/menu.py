import os
import sys
import atom_server

from pype.nuke.lib import (
    writes_version_sync,
    onScriptLoad,
    checkInventoryVersions
)

import nuke
from pypeapp import Logger

log = Logger().get_logger(__name__, "nuke")


# nuke.addOnScriptSave(writes_version_sync)
nuke.addOnScriptSave(onScriptLoad)
nuke.addOnScriptLoad(checkInventoryVersions)
nuke.addOnScriptSave(checkInventoryVersions)
nuke.addOnScriptSave(writes_version_sync)

log.info('Automatic syncing of write file knob to script version')

def adding_knobscripter_to_nukepath():
    nuke_path_dir = os.path.dirname(__file__)
    knobscripter_path = os.path.join(nuke_path_dir, "KnobScripter-github")
    sys.path.append(knobscripter_path)
    import KnobScripter
    log.info('Adding `KnobScripter`')

adding_knobscripter_to_nukepath()
