import os
from openpype.api import get_project_settings
from openpype.pipeline import install_host
from openpype.hosts.maya import api
from maya import cmds

install_host(api)


print("starting OpenPype usersetup")

# build a shelf
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

    cmds.evalDeferred("mlib.shelf(name=shelf_preset['name'], iconPath=icon_path, preset=shelf_preset)")


print("finished OpenPype usersetup")
