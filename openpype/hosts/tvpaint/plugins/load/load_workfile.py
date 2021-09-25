import getpass
import os

from avalon.tvpaint import lib, pipeline, get_current_workfile_context
from avalon import api, io
import openpype


class LoadWorkfile(pipeline.Loader):
    """Load workfile."""

    families = ["workfile"]
    representations = ["tvpp"]

    label = "Load Workfile"

    def load(self, context, name, namespace, options):
        filepath = self.fname.replace("\\", "/")

        if not os.path.exists(filepath):
            raise FileExistsError(
                "The loaded file does not exist. Try downloading it first."
            )

        george_script = "tv_LoadProject '\"'\"{}\"'\"'".format(
            filepath
        )
        lib.execute_george_through_file(george_script)

        # Save workfile.
        host = api.registered_host()

        project = io.find_one({
            "type": "project"
        })
        context = get_current_workfile_context()
        template_key = openpype.lib.get_workfile_template_key_from_context(
            context["asset"],
            context["task"],
            host,
            project_name=project["name"]
        )
        anatomy = openpype.Anatomy(project["name"])
        data = {
            "project": {
                "name": project["name"],
                "code": project["data"].get("code")
            },
            "asset": context["asset"],
            "task": context["task"],
            "version": 1,
            "user": getpass.getuser(),
            "root": {
                template_key: anatomy.roots[template_key]
            },
            "hierarchy": openpype.lib.get_hierarchy()
        }
        template = anatomy.templates[template_key]["file"]

        # Define saving file extension
        current_file = host.current_file()
        if current_file:
            # Match the extension of current file
            _, extension = os.path.splitext(current_file)
        else:
            # Fall back to the first extension supported for this host.
            extension = host.file_extensions()[0]

        data["ext"] = extension

        work_root = api.format_template_with_optional_keys(
            data, anatomy.templates[template_key]["folder"]
        )
        version = api.last_workfile_with_version(
            work_root, template, data, [data["ext"]]
        )[1]

        if version is None:
            version = 1
        else:
            version += 1

        data["version"] = version

        path = os.path.join(
            work_root,
            api.format_template_with_optional_keys(data, template)
        )
        host.save_file(path)
