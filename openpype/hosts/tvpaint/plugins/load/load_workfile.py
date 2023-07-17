import os

from openpype.lib import StringTemplate
from openpype.pipeline import (
    registered_host,
    get_current_context,
    Anatomy,
)
from openpype.pipeline.workfile import (
    get_workfile_template_key_from_context,
    get_last_workfile_with_version,
)
from openpype.pipeline.template_data import get_template_data_with_names
from openpype.hosts.tvpaint.api import plugin
from openpype.hosts.tvpaint.api.lib import (
    execute_george_through_file,
)
from openpype.hosts.tvpaint.api.pipeline import (
    get_current_workfile_context,
)
from openpype.pipeline import get_current_versioning_start


class LoadWorkfile(plugin.Loader):
    """Load workfile."""

    families = ["workfile"]
    representations = ["tvpp"]

    label = "Load Workfile"

    def load(self, context, name, namespace, options):
        # Load context of current workfile as first thing
        #   - which context and extension has
        filepath = self.filepath_from_context(context)
        filepath = filepath.replace("\\", "/")

        if not os.path.exists(filepath):
            raise FileExistsError(
                "The loaded file does not exist. Try downloading it first."
            )

        host = registered_host()
        current_file = host.get_current_workfile()
        work_context = get_current_workfile_context()

        george_script = "tv_LoadProject '\"'\"{}\"'\"'".format(
            filepath
        )
        execute_george_through_file(george_script)

        # Save workfile.
        host_name = "tvpaint"
        project_name = work_context.get("project")
        asset_name = work_context.get("asset")
        task_name = work_context.get("task")
        # Far cases when there is workfile without work_context
        if not asset_name:
            context = get_current_context()
            project_name = context["project_name"]
            asset_name = context["asset_name"]
            task_name = context["task_name"]

        template_key = get_workfile_template_key_from_context(
            asset_name,
            task_name,
            host_name,
            project_name=project_name
        )
        anatomy = Anatomy(project_name)

        data = get_template_data_with_names(
            project_name, asset_name, task_name, host_name
        )
        data["root"] = anatomy.roots

        file_template = anatomy.templates[template_key]["file"]

        # Define saving file extension
        extensions = host.get_workfile_extensions()
        if current_file:
            # Match the extension of current file
            _, extension = os.path.splitext(current_file)
        else:
            # Fall back to the first extension supported for this host.
            extension = extensions[0]

        data["ext"] = extension

        folder_template = anatomy.templates[template_key]["folder"]
        work_root = StringTemplate.format_strict_template(
            folder_template, data
        )
        version = get_last_workfile_with_version(
            work_root, file_template, data, extensions
        )[1]

        if version is None:
            version = get_current_versioning_start(
                host="tvpaint",
                task_name=task_name,
                task_type=data["task"]["type"],
                family="workfile"
            )
        else:
            version += 1

        data["version"] = version

        filename = StringTemplate.format_strict_template(
            file_template, data
        )
        path = os.path.join(work_root, filename)
        host.save_workfile(path)
