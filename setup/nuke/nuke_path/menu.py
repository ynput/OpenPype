
from pype.nuke.lib import writes_version_sync, onScriptLoad
import nuke
from pype.api import Logger

log = Logger.getLogger(__name__, "nuke")


# nuke.addOnScriptSave(writes_version_sync)
# nuke.addOnScriptSave(onScriptLoad)

log.info('Automatic syncing of write file knob to script version')
