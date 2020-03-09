import os
import sys
import KnobScripter

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
# nuke.addOnScriptSave(writes_version_sync)

log.info('Automatic syncing of write file knob to script version')
