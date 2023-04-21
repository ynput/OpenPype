import os
import nuke
from openpype.pipeline import registered_host
from openpype.lib import Logger
from openpype.hosts.nuke.api.lib import WorkfileSettings

log = Logger().get_logger(__name__)


def script_create():
    log.info("_______ Callback started _______")

    last_workfile_path = os.getenv("AVALON_LAST_WORKFILE")
    log.info("Nuke script created: {}".format(last_workfile_path))

    host = registered_host()

    # set workfile properties
    workfile_settings = WorkfileSettings()
    workfile_settings.set_context_settings()


    # save workfile
    host.save_file(last_workfile_path)


def close_script():
    log.info("_______ Closing script _______")
    nuke.scriptExit()


nuke.addOnUserCreate(script_create, nodeClass="Root")
nuke.removeOnCreate(script_create, nodeClass="Root")
nuke.addOnScriptSave(close_script)
