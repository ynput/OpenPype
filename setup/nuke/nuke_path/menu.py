
from pype.nuke.lib import writes_version_sync, onScriptLoad
import nuke
from pypeapp import Logger

log = Logger().get_logger(__name__, "nuke")


nuke.addOnScriptSave(writes_version_sync)
nuke.addOnScriptSave(onScriptLoad)

log.info('Automatic syncing of write file knob to script version')
