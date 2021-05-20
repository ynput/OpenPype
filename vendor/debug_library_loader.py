import os
import pyblish
import pyblish.cli
import pyblish.plugin

os.environ["AVALON_MONGO"] = "mongodb://localhost:27017"
os.environ["OPENPYPE_MONGO"] = "mongodb://localhost:27017"
os.environ["AVALON_DB"] = "avalon"
os.environ["OPENPYPE_DATABASE_NAME"] = "avalon"
os.environ["AVALON_TIMEOUT"] = '3000'
os.environ["OPENPYPE_DEBUG"] = "3"
os.environ["AVALON_CONFIG"] = "pype"
os.environ["AVALON_ASSET"] = "Jungle"
os.environ["AVALON_PROJECT"] = "petr_second"

from avalon.tools.libraryloader import show
import openpype
openpype.install()

# REGISTERED = pyblish.plugin.registered_paths()
# PACKAGEPATH = pyblish.lib.main_package_path()
# ENVIRONMENT = os.environ.get("PYBLISHPLUGINPATH", "")
# PLUGINPATH = os.path.join(PACKAGEPATH, '..', 'tests', 'plugins')
#
# REGISTERED.append("C:\\Users\\petrk\\PycharmProjects\\Pype3.0\\pype\\openpype\\plugins\\load")
# pyblish.plugin.deregister_all_paths()
# for path in REGISTERED:
#     register_plugin_path(avalon.Loader, LOAD_PATH)
#     pyblish.plugin.register_plugin_path(path)

show(debug=True, show_projects=True, show_libraries=True)