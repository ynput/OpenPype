import os
import shutil
from functools import partial

from openpype.settings import get_project_settings
from openpype.pipeline import install_host
from openpype.hosts.maya.api import MayaHost, current_file
from openpype.lib import register_event_callback

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


# Setup Xgen save callback.
def xgen_on_save():
    """Increments the xgen side car files .xgen and .xgd

    Only works when incrementing to the same directory.
    """

    file_path = current_file()
    current_dir = os.path.dirname(file_path)
    basename = os.path.basename(file_path).split(".")[0]
    attrs = ["xgFileName", "xgBaseFile"]
    for palette in cmds.ls(type="xgmPalette"):
        for attr in attrs:
            source = os.path.join(
                current_dir, cmds.getAttr(palette + "." + attr)
            )
            if not os.path.exists(source):
                continue

            destination_basename = "{}__{}{}".format(
                basename,
                palette.replace(":", "_"),
                os.path.splitext(source)[1]
            )
            destination = os.path.join(current_dir, destination_basename)

            if source == destination:
                continue

            shutil.copy(source, destination)
            cmds.setAttr(
                palette + "." + attr, destination_basename, type="string"
            )


register_event_callback("save", xgen_on_save)

# Build a shelf.
settings = get_project_settings(os.environ['AVALON_PROJECT'])
shelf_preset = settings['maya'].get('project_shelf')

if shelf_preset:
    project = os.environ["AVALON_PROJECT"]

    icon_path = os.path.join(os.environ['OPENPYPE_PROJECT_SCRIPTS'],
                             project, "icons")
    icon_path = os.path.abspath(icon_path)

    for i in shelf_preset['imports']:
        import_string = "from {} import {}".format(project, i)
        print(import_string)
        exec(import_string)

    cmds.evalDeferred(
        "mlib.shelf(name=shelf_preset['name'], iconPath=icon_path,"
        " preset=shelf_preset)"
    )


print("Finished OpenPype usersetup.")
