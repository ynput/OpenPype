import os

from avalon import api, io
from openpype.lib import (
    StringTemplate,
    get_workfile_template_key_from_context,
    get_workdir_data,
    get_last_workfile_with_version,
)
from openpype.api import Anatomy
from openpype.hosts.tvpaint.api import lib, pipeline, plugin


class LoadWorkfile(plugin.Loader):
    """Load workfile."""

    families = ["workfile"]
    representations = ["tvpp"]

    label = "Load Workfile"

    def load(self, context, name, namespace, options):
        # Load context of current workfile as first thing
        #   - which context and extension has
        host = api.registered_host()
        current_file = host.current_file()

        context = pipeline.get_current_workfile_context()

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
        host_name = "tvpaint"
        asset_name = context.get("asset")
        task_name = context.get("task")
        # Far cases when there is workfile without context
        if not asset_name:
            asset_name = io.Session["AVALON_ASSET"]
            task_name = io.Session["AVALON_TASK"]

        project_doc = io.find_one({
            "type": "project"
        })
        asset_doc = io.find_one({
            "type": "asset",
            "name": asset_name
        })
        project_name = project_doc["name"]

        template_key = get_workfile_template_key_from_context(
            asset_name,
            task_name,
            host_name,
            project_name=project_name,
            dbcon=io
        )
        anatomy = Anatomy(project_name)

        data = get_workdir_data(project_doc, asset_doc, task_name, host_name)
        data["root"] = anatomy.roots

        file_template = anatomy.templates[template_key]["file"]

        # Define saving file extension
        if current_file:
            # Match the extension of current file
            _, extension = os.path.splitext(current_file)
        else:
            # Fall back to the first extension supported for this host.
            extension = host.file_extensions()[0]

        data["ext"] = extension

        folder_template = anatomy.templates[template_key]["folder"]
        work_root = StringTemplate.format_strict_template(
            folder_template, data
        )
        version = get_last_workfile_with_version(
            work_root, file_template, data, host.file_extensions()
        )[1]

        if version is None:
            version = 1
        else:
            version += 1

        data["version"] = version

        filename = StringTemplate.format_strict_template(
            file_template, data
        )
        path = os.path.join(work_root, filename)
        host.save_file(path)
