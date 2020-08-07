import os
import sys
import KnobScripter

from pype.hosts.nuke.lib import (
    writes_version_sync,
    on_script_load,
    check_inventory_versions
)

import nuke
from pype.api import Logger

log = Logger().get_logger(__name__, "nuke")


# nuke.addOnScriptSave(writes_version_sync)
nuke.addOnScriptSave(on_script_load)
nuke.addOnScriptLoad(check_inventory_versions)
nuke.addOnScriptSave(check_inventory_versions)
# nuke.addOnScriptSave(writes_version_sync)

log.info('Automatic syncing of write file knob to script version')
