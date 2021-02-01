import nuke
from pype.api import Logger
import KnobScripter

from pype.hosts.nuke.lib import (
    on_script_load,
    check_inventory_versions
)

log = Logger().get_logger(__name__, "nuke")


nuke.addOnScriptSave(on_script_load)
nuke.addOnScriptLoad(check_inventory_versions)
nuke.addOnScriptSave(check_inventory_versions)

log.info('Automatic syncing of write file knob to script version')
