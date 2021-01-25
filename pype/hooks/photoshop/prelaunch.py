import os
import pype.lib
from pype.api import Logger, Anatomy
import shutil
import getpass
import avalon.api


class PhotoshopPrelaunch(pype.lib.PypeHook):
    """This hook will check for the existence of PyWin

    PyWin is a requirement for the Photoshop integration.
    """
    project_code = None
    host_name = "photoshop"

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:
        output = pype.lib._subprocess(["pip", "install", "pywin32==227"])
        self.log.info(output)

        workfile_path = self.get_workfile_plath(env, self.host_name)

        # adding compulsory environment var for openting file
        env["PYPE_WORKFILE_PATH"] = workfile_path

        return True

    def get_anatomy_filled(self, workdir, project_name, asset_name,
                           task_name, host_name, extension):
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
            "app": host_name,
            "hierarchy": hierarchy
        }
        anatomy = Anatomy(project_name)
        file_template = anatomy.templates["work"]["file"]
        data.update({
            "version": 1,
            "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
            "ext": extension
        })

        return avalon.api.last_workfile(
            workdir, file_template, data,
            avalon.api.HOST_WORKFILE_EXTENSIONS[host_name], True
        )

    def get_workfile_plath(self, env, host_name):
        # get context variables
        project_name = env["AVALON_PROJECT"]
        asset_name = env["AVALON_ASSET"]
        task_name = env["AVALON_TASK"]
        workdir = env["AVALON_WORKDIR"]
        extension = avalon.api.HOST_WORKFILE_EXTENSIONS[host_name][0]
        template_env_key = "{}_TEMPLATE".format(host_name.upper())

        # get workfile path
        workfile_path = self.get_anatomy_filled(
            workdir, project_name, asset_name, task_name, host_name, extension)

        # create workdir if doesn't exist
        os.makedirs(workdir, exist_ok=True)
        self.log.info("Work dir is: `{}`".format(workdir))

        # get last version of workfile
        workfile_last = env.get("AVALON_LAST_WORKFILE")
        self.log.debug("_ workfile_last: `{}`".format(workfile_last))

        if workfile_last:
            workfile = workfile_last
            workfile_path = os.path.join(workdir, workfile)

        # copy workfile from template if doesnt exist any on path
        if not os.path.isfile(workfile_path):
            # try to get path from environment or use default
            # from `pype.hosts.<host_name>` dir
            template_path = env.get(template_env_key) or os.path.join(
                env.get("PYPE_MODULE_ROOT"),
                "pype/hosts/{}/template{}".format(host_name, extension)
            )

            # try to get template from project config folder
            proj_config_path = os.path.join(
                env["PYPE_PROJECT_CONFIGS"], project_name)
            if os.path.exists(proj_config_path):

                template_file = None
                for f in os.listdir(proj_config_path):
                    if extension in os.path.splitext(f):
                        template_file = f

                if template_file:
                    template_path = os.path.join(
                        proj_config_path, template_file)
            self.log.info(
                "Creating workfile from template: `{}`".format(template_path))

            # copy template to new destinantion
            shutil.copy2(
                os.path.normpath(template_path),
                os.path.normpath(workfile_path)
            )

        self.log.info("Workfile to open: `{}`".format(workfile_path))
        return workfile_path
