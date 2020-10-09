import os
import shutil
from pype.lib import PypeHook
from pype.api import (
    Anatomy,
    Logger
)
import getpass
import avalon.api


class TvpaintPrelaunchHook(PypeHook):
    """
    Workfile preparation hook
    """
    host_name = "tvpaint"

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:
        if not env:
            env = os.environ

        # get context variables
        project_name = env["AVALON_PROJECT"]
        asset_name = env["AVALON_ASSET"]
        task_name = env["AVALON_TASK"]
        workdir = env["AVALON_WORKDIR"]
        extension = avalon.api.HOST_WORKFILE_EXTENSIONS[self.host_name][0]

        # get workfile path
        workfile_path = self.get_anatomy_filled(
            workdir, project_name, asset_name, task_name)

        # create workdir if doesn't exist
        os.makedirs(workdir, exist_ok=True)
        self.log.info(f"Work dir is: `{workdir}`")

        # get last version of workfile
        workfile_last = env.get("AVALON_LAST_WORKFILE")
        self.log.debug(f"_ workfile_last: `{workfile_last}`")

        if workfile_last:
            workfile = workfile_last
            workfile_path = os.path.join(workdir, workfile)

        # copy workfile from template if doesnt exist any on path
        if not os.path.isfile(workfile_path):
            # try to get path from environment or use default
            # from `pype.hosts.tvpaint` dir
            template_path = env.get("TVPAINT_TEMPLATE") or os.path.join(
                env.get("PYPE_MODULE_ROOT"),
                "pype/hosts/tvpaint/template.tvpp"
            )

            # try to get template from project config folder
            proj_config_path = os.path.join(
                env["PYPE_PROJECT_CONFIGS"], project_name)
            if os.path.exists(proj_config_path):
                self.log.info(
                    f"extension: `{extension}`")
                template_file = next((
                    f for f in os.listdir(proj_config_path)
                    if extension in os.path.splitext(f)[1]
                ))
                if template_file:
                    template_path = os.path.join(
                        proj_config_path, template_file)
            self.log.info(
                f"Creating workfile from template: `{template_path}`")

            # copy template to new destinantion
            shutil.copy2(
                os.path.normpath(template_path),
                os.path.normpath(workfile_path)
            )

        self.log.info(f"Workfile to open: `{workfile_path}`")

        # adding compulsory environment var for openting file
        env["PYPE_TVPAINT_PROJECT_FILE"] = workfile_path

        return True

    def get_anatomy_filled(self, workdir, project_name, asset_name, task_name):
        dbcon = avalon.api.AvalonMongoDB()
        dbcon.install()
        dbcon.Session["AVALON_PROJECT"] = project_name
        project_document = dbcon.find_one({"type": "project"})
        asset_document = dbcon.find_one({
            "type": "asset",
            "name": asset_name
        })
        dbcon.uninstall()

        asset_doc_parents = asset_document["data"].get("parents")
        hierarchy = "/".join(asset_doc_parents)

        data = {
            "project": {
                "name": project_document["name"],
                "code": project_document["data"].get("code")
            },
            "task": task_name,
            "asset": asset_name,
            "app": self.host_name,
            "hierarchy": hierarchy
        }
        anatomy = Anatomy(project_name)
        extensions = avalon.api.HOST_WORKFILE_EXTENSIONS[self.host_name]
        file_template = anatomy.templates["work"]["file"]
        data.update({
            "version": 1,
            "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
            "ext": extensions[0]
        })

        return avalon.api.last_workfile(
            workdir, file_template, data, extensions, True
        )
