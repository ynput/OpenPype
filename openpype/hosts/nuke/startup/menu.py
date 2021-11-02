import os
from openpype.hosts.nuke.api.lib import (
    on_script_load,
    check_inventory_versions,
    WorkfileSettings
)
from openpype.lib.path_tools import HostDirmap
from openpype.settings import get_project_settings
from openpype.modules import ModulesManager

import nuke
from openpype.api import Logger

log = Logger().get_logger(__name__)


class NukeDirmap(HostDirmap):
    def __init__(self, host_name, project_settings, sync_module, file_name):
        """
            Args:
                host_name (str): Nuke
                project_settings (dict): settings of current project
                sync_module (SyncServerModule): to limit reinitialization
                file_name (str): full path of referenced file from workfiles
        """
        self.host_name = host_name
        self.project_settings = project_settings
        self.file_name = file_name
        self.sync_module = sync_module

    def on_enable_dirmap(self):
        pass

    def dirmap_routine(self, source_path, destination_path):
        log.debug("{}: {}->{}".format(self.file_name,
                                      source_path, destination_path))
        self.file_name = self.file_name.replace(source_path, destination_path)


# fix ffmpeg settings on script
nuke.addOnScriptLoad(on_script_load)

# set checker for last versions on loaded containers
nuke.addOnScriptLoad(check_inventory_versions)
nuke.addOnScriptSave(check_inventory_versions)

# # set apply all workfile settings on script load and save
nuke.addOnScriptLoad(WorkfileSettings().set_context_settings)


project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
manager = ModulesManager()
sync_module = manager.modules_by_name["sync_server"]


def myFilenameFilter(file_name):
    dirmap_processor = NukeDirmap("nuke", project_settings, sync_module,
                                  file_name)
    dirmap_processor.process_dirmap()
    return dirmap_processor.file_name


nuke.addFilenameFilter(myFilenameFilter)

log.info('Automatic syncing of write file knob to script version')
