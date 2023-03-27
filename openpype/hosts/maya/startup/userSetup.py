import os
from functools import partial

from openpype.settings import get_project_settings
from openpype.pipeline import install_host, get_current_project_name
from openpype.hosts.maya.api import MayaHost

from maya import cmds


host = MayaHost()
install_host(host)

print("Starting OpenPype usersetup...")


# Open Workfile Post Initialization.
key = "OPENPYPE_OPEN_WORKFILE_POST_INITIALIZATION"
if bool(int(os.environ.get(key, "0"))):
    cmds.evalDeferred(
        partial(
            cmds.file,
            os.environ["AVALON_LAST_WORKFILE"],
            open=True,
            force=True
        ),
        lowestPriority=True
    )


# Build a shelf.
project_name = get_current_project_name()
settings = get_project_settings(project_name)
shelf_preset = settings['maya'].get('project_shelf')

if shelf_preset:
    icon_path = os.path.join(
        os.environ['OPENPYPE_PROJECT_SCRIPTS'],
        project_name,
        "icons")
    icon_path = os.path.abspath(icon_path)

    for i in shelf_preset['imports']:
        import_string = "from {} import {}".format(project_name, i)
        print(import_string)
        exec(import_string)

    cmds.evalDeferred(
        "mlib.shelf(name=shelf_preset['name'], iconPath=icon_path,"
        " preset=shelf_preset)"
    )


print("Finished OpenPype usersetup.")
