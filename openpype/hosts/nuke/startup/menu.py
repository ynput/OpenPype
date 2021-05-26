from openpype.hosts.nuke.api.lib import (
    on_script_load,
    check_inventory_versions,
    WorkfileSettings
)

import nuke
from openpype.api import Logger

log = Logger().get_logger(__name__)


# fix ffmpeg settings on script
nuke.addOnScriptLoad(on_script_load)

# set checker for last versions on loaded containers
nuke.addOnScriptLoad(check_inventory_versions)
nuke.addOnScriptSave(check_inventory_versions)

# # set apply all workfile settings on script load and save
nuke.addOnScriptLoad(WorkfileSettings().set_context_settings)

log.info('Automatic syncing of write file knob to script version')
