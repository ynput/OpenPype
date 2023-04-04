import os

from openpype.settings import get_project_settings
from openpype.pipeline import install_host, get_current_project_name
from openpype.hosts.maya.api import MayaHost

from maya import cmds


host = MayaHost()
install_host(host)

print("Starting OpenPype usersetup...")

project_name = get_current_project_name()
settings = get_project_settings(project_name)

# Loading plugins explicitly.
explicit_plugins_loading = project_settings["maya"]["explicit_plugins_loading"]
if explicit_plugins_loading["enabled"]:
    def _explicit_load_plugins():
        for plugin in explicit_plugins_loading["plugins_to_load"]:
            if plugin["enabled"]:
                print("Loading plug-in: " + plugin["name"])
                try:
                    cmds.loadPlugin(plugin["name"], quiet=True)
                except RuntimeError as e:
                    print(e)

    # We need to load plugins deferred as loading them directly does not work
    # correctly due to Maya's initialization.
    cmds.evalDeferred(
        _explicit_load_plugins,
        lowestPriority=True
    )

# Open Workfile Post Initialization.
key = "OPENPYPE_OPEN_WORKFILE_POST_INITIALIZATION"
if bool(int(os.environ.get(key, "0"))):
    def _log_and_open():
        path = os.environ["AVALON_LAST_WORKFILE"]
        print("Opening \"{}\"".format(path))
        cmds.file(path, open=True, force=True)
    cmds.evalDeferred(
        _log_and_open,
        lowestPriority=True
    )

# Build a shelf.
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
