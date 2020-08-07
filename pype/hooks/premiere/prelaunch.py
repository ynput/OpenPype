import os
import traceback
import winreg
from avalon import api, io, lib
from pype.lib import PypeHook
from pype.api import Logger, Anatomy
from pype.hosts.premiere import lib as prlib


class PremierePrelaunch(PypeHook):
    """
    This hook will check if current workfile path has Adobe Premiere
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Premiere launcher
    shell script.
    """
    project_code = None
    reg_string_value = [{
        "path": r"Software\Adobe\CSXS.9",
        "name": "PlayerDebugMode",
        "type": winreg.REG_SZ,
        "value": "1"
    }]

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:

        if not env:
            env = os.environ

        # initialize
        self._S = api.Session

        # get context variables
        self._S["AVALON_PROJECT"] = env["AVALON_PROJECT"]
        self._S["AVALON_ASSET"] = env["AVALON_ASSET"]
        task = self._S["AVALON_TASK"] = env["AVALON_TASK"]

        # get workfile path
        anatomy_filled = self.get_anatomy_filled()

        # if anatomy template should have different root for particular task
        # just add for example > work[conforming]:
        workfile_search_key = f"work[{task.lower()}]"
        workfile_key = anatomy_filled.get(
            workfile_search_key,
            anatomy_filled.get("work")
        )
        workdir = env["AVALON_WORKDIR"] = workfile_key["folder"]

        # create workdir if doesn't exist
        os.makedirs(workdir, exist_ok=True)
        self.log.info(f"Work dir is: `{workdir}`")

        # adding project code to env
        env["AVALON_PROJECT_CODE"] = self.project_code

        # add keys to registry
        self.modify_registry()

        # start avalon
        try:
            __import__("pype.hosts.premiere")
            __import__("pyblish")

        except ImportError as e:
            print(traceback.format_exc())
            print("pyblish: Could not load integration: %s " % e)

        else:
            # Premiere Setup integration
            prlib.setup(env)

        return True

    def modify_registry(self):
        # adding key to registry
        for key in self.reg_string_value:
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, key["path"])
            rg_key = winreg.OpenKey(
                key=winreg.HKEY_CURRENT_USER,
                sub_key=key["path"],
                reserved=0,
                access=winreg.KEY_ALL_ACCESS)

            winreg.SetValueEx(
                rg_key,
                key["name"],
                0,
                key["type"],
                key["value"]
            )

    def get_anatomy_filled(self):
        root_path = api.registered_root()
        project_name = self._S["AVALON_PROJECT"]
        asset_name = self._S["AVALON_ASSET"]

        io.install()
        project_entity = io.find_one({
            "type": "project",
            "name": project_name
        })
        assert project_entity, (
            "Project '{0}' was not found."
        ).format(project_name)
        self.log.debug("Collected Project \"{}\"".format(project_entity))

        asset_entity = io.find_one({
            "type": "asset",
            "name": asset_name,
            "parent": project_entity["_id"]
        })
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        project_name = project_entity["name"]
        self.project_code = project_entity["data"].get("code")

        self.log.info(
            "Anatomy object collected for project \"{}\".".format(project_name)
        )

        hierarchy_items = asset_entity["data"]["parents"]
        hierarchy = ""
        if hierarchy_items:
            hierarchy = os.path.join(*hierarchy_items)

        template_data = {
            "root": root_path,
            "project": {
                "name": project_name,
                "code": self.project_code
            },
            "asset": asset_entity["name"],
            "hierarchy": hierarchy.replace("\\", "/"),
            "task": self._S["AVALON_TASK"],
            "ext": "ppro",
            "version": 1,
            "username": os.getenv("PYPE_USERNAME", "").strip()
        }

        avalon_app_name = os.environ.get("AVALON_APP_NAME")
        if avalon_app_name:
            application_def = lib.get_application(avalon_app_name)
            app_dir = application_def.get("application_dir")
            if app_dir:
                template_data["app"] = app_dir

        anatomy = Anatomy(project_name)
        anatomy_filled = anatomy.format_all(template_data).get_solved()

        return anatomy_filled
