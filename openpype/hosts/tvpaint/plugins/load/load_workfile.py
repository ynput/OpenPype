import getpass
import os

from avalon.tvpaint import lib, pipeline
from avalon import api, io

from openpype import Anatomy


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
        session = api.Session
        data = {
            "project": {
                "name": project["name"],
                "code": project["data"].get("code")
            },
            "asset": session["AVALON_ASSET"],
            "task": session["AVALON_TASK"],
            "version": 1,
            "user": getpass.getuser()
        }
        anatomy = Anatomy(project["name"])
        template = anatomy.templates["work"]["file"]

        # Define saving file extension
        current_file = host.current_file()
        if current_file:
            # Match the extension of current file
            _, extension = os.path.splitext(current_file)
        else:
            # Fall back to the first extension supported for this host.
            extension = host.file_extensions()[0]

        data["ext"] = extension

        version = api.last_workfile_with_version(
            host.work_root(session), template, data, [data["ext"]]
        )[1]

        if version is None:
            version = 1
        else:
            version += 1

        data["version"] = version

        path = os.path.join(
            host.work_root(session),
            api.format_template_with_optional_keys(data, template)
        )
        host.save_file(path)
