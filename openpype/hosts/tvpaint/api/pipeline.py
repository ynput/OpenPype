import os
import json
import tempfile
import logging

import requests

import pyblish.api

from openpype.client import get_asset_by_name
from openpype.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost
from openpype.hosts.tvpaint import TVPAINT_ROOT_DIR
from openpype.settings import get_current_project_settings
from openpype.lib import register_event_callback
from openpype.pipeline import (
    legacy_io,
    register_loader_plugin_path,
    register_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.context_tools import get_global_context

from .lib import (
    execute_george,
    execute_george_through_file
)

log = logging.getLogger(__name__)


METADATA_SECTION = "avalon"
SECTION_NAME_CONTEXT = "context"
SECTION_NAME_CREATE_CONTEXT = "create_context"
SECTION_NAME_INSTANCES = "instances"
SECTION_NAME_CONTAINERS = "containers"
# Maximum length of metadata chunk string
# TODO find out the max (500 is safe enough)
TVPAINT_CHUNK_LENGTH = 500

"""TVPaint's Metadata

Metadata are stored to TVPaint's workfile.

Workfile works similar to .ini file but has few limitation. Most important
limitation is that value under key has limited length. Due to this limitation
each metadata section/key stores number of "subkeys" that are related to
the section.

Example:
Metadata key `"instances"` may have stored value "2". In that case it is
expected that there are also keys `["instances0", "instances1"]`.

Workfile data looks like:
```
[avalon]
instances0=[{{__dq__}id{__dq__}: {__dq__}pyblish.avalon.instance{__dq__...
instances1=...more data...
instances=2
```
"""


class TVPaintHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "tvpaint"

    def install(self):
        """Install TVPaint-specific functionality."""

        log.info("OpenPype - Installing TVPaint integration")
        legacy_io.install()

        # Create workdir folder if does not exist yet
        workdir = legacy_io.Session["AVALON_WORKDIR"]
        if not os.path.exists(workdir):
            os.makedirs(workdir)

        plugins_dir = os.path.join(TVPAINT_ROOT_DIR, "plugins")
        publish_dir = os.path.join(plugins_dir, "publish")
        load_dir = os.path.join(plugins_dir, "load")
        create_dir = os.path.join(plugins_dir, "create")

        pyblish.api.register_host("tvpaint")
        pyblish.api.register_plugin_path(publish_dir)
        register_loader_plugin_path(load_dir)
        register_creator_plugin_path(create_dir)

        register_event_callback("application.launched", self.initial_launch)
        register_event_callback("application.exit", self.application_exit)

    def get_current_project_name(self):
        """
        Returns:
            Union[str, None]: Current project name.
        """

        return self.get_current_context().get("project_name")

    def get_current_asset_name(self):
        """
        Returns:
            Union[str, None]: Current asset name.
        """

        return self.get_current_context().get("asset_name")

    def get_current_task_name(self):
        """
        Returns:
            Union[str, None]: Current task name.
        """

        return self.get_current_context().get("task_name")

    def get_current_context(self):
        context = get_current_workfile_context()
        if not context:
            return get_global_context()

        if "project_name" in context:
            return context
        # This is legacy way how context was stored
        return {
            "project_name": context.get("project"),
            "asset_name": context.get("asset"),
            "task_name": context.get("task")
        }

    # --- Create ---
    def get_context_data(self):
        return get_workfile_metadata(SECTION_NAME_CREATE_CONTEXT, {})

    def update_context_data(self, data, changes):
        return write_workfile_metadata(SECTION_NAME_CREATE_CONTEXT, data)

    def list_instances(self):
        """List all created instances from current workfile."""
        return list_instances()

    def write_instances(self, data):
        return write_instances(data)

    # --- Workfile ---
    def open_workfile(self, filepath):
        george_script = "tv_LoadProject '\"'\"{}\"'\"'".format(
            filepath.replace("\\", "/")
        )
        return execute_george_through_file(george_script)

    def save_workfile(self, filepath=None):
        if not filepath:
            filepath = self.get_current_workfile()
        context = get_global_context()
        save_current_workfile_context(context)

        # Execute george script to save workfile.
        george_script = "tv_SaveProject {}".format(filepath.replace("\\", "/"))
        return execute_george(george_script)

    def work_root(self, session):
        return session["AVALON_WORKDIR"]

    def get_current_workfile(self):
        return execute_george("tv_GetProjectName")

    def workfile_has_unsaved_changes(self):
        return None

    def get_workfile_extensions(self):
        return [".tvpp"]

    # --- Load ---
    def get_containers(self):
        return get_containers()

    def initial_launch(self):
        # Setup project settings if its the template that's launched.
        # TODO also check for template creation when it's possible to define
        #   templates
        last_workfile = os.environ.get("AVALON_LAST_WORKFILE")
        if not last_workfile or os.path.exists(last_workfile):
            return

        log.info("Setting up project...")
        global_context = get_global_context()
        project_name = global_context.get("project_name")
        asset_name = global_context.get("aset_name")
        if not project_name or not asset_name:
            return

        asset_doc = get_asset_by_name(project_name, asset_name)

        set_context_settings(project_name, asset_doc)

    def application_exit(self):
        """Logic related to TimerManager.

        Todo:
            This should be handled out of TVPaint integration logic.
        """

        data = get_current_project_settings()
        stop_timer = data["tvpaint"]["stop_timer_on_application_exit"]

        if not stop_timer:
            return

        # Stop application timer.
        webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")
        rest_api_url = "{}/timers_manager/stop_timer".format(webserver_url)
        requests.post(rest_api_url)


def containerise(
    name, namespace, members, context, loader, current_containers=None
):
    """Add new container to metadata.

    Args:
        name (str): Container name.
        namespace (str): Container namespace.
        members (list): List of members that were loaded and belongs
            to the container (layer names).
        current_containers (list): Preloaded containers. Should be used only
            on update/switch when containers were modified during the process.

    Returns:
        dict: Container data stored to workfile metadata.
    """

    container_data = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "members": members,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"])
    }
    if current_containers is None:
        current_containers = get_containers()

    # Add container to containers list
    current_containers.append(container_data)

    # Store data to metadata
    write_workfile_metadata(SECTION_NAME_CONTAINERS, current_containers)

    return container_data


def split_metadata_string(text, chunk_length=None):
    """Split string by length.

    Split text to chunks by entered length.
    Example:
        ```python
        text = "ABCDEFGHIJKLM"
        result = split_metadata_string(text, 3)
        print(result)
        >>> ['ABC', 'DEF', 'GHI', 'JKL']
        ```

    Args:
        text (str): Text that will be split into chunks.
        chunk_length (int): Single chunk size. Default chunk_length is
            set to global variable `TVPAINT_CHUNK_LENGTH`.

    Returns:
        list: List of strings with at least one item.
    """
    if chunk_length is None:
        chunk_length = TVPAINT_CHUNK_LENGTH
    chunks = []
    for idx in range(chunk_length, len(text) + chunk_length, chunk_length):
        start_idx = idx - chunk_length
        chunks.append(text[start_idx:idx])
    return chunks


def get_workfile_metadata_string_for_keys(metadata_keys):
    """Read metadata for specific keys from current project workfile.

    All values from entered keys are stored to single string without separator.

    Function is designed to help get all values for one metadata key at once.
    So order of passed keys matteres.

    Args:
        metadata_keys (list, str): Metadata keys for which data should be
            retrieved. Order of keys matters! It is possible to enter only
            single key as string.
    """
    # Add ability to pass only single key
    if isinstance(metadata_keys, str):
        metadata_keys = [metadata_keys]

    output_file = tempfile.NamedTemporaryFile(
        mode="w", prefix="a_tvp_", suffix=".txt", delete=False
    )
    output_file.close()
    output_filepath = output_file.name.replace("\\", "/")

    george_script_parts = []
    george_script_parts.append(
        "output_path = \"{}\"".format(output_filepath)
    )
    # Store data for each index of metadata key
    for metadata_key in metadata_keys:
        george_script_parts.append(
            "tv_readprojectstring \"{}\" \"{}\" \"\"".format(
                METADATA_SECTION, metadata_key
            )
        )
        george_script_parts.append(
            "tv_writetextfile \"strict\" \"append\" '\"'output_path'\"' result"
        )

    # Execute the script
    george_script = "\n".join(george_script_parts)
    execute_george_through_file(george_script)

    # Load data from temp file
    with open(output_filepath, "r") as stream:
        file_content = stream.read()

    # Remove `\n` from content
    output_string = file_content.replace("\n", "")

    # Delete temp file
    os.remove(output_filepath)

    return output_string


def get_workfile_metadata_string(metadata_key):
    """Read metadata for specific key from current project workfile."""
    result = get_workfile_metadata_string_for_keys([metadata_key])
    if not result:
        return None

    stripped_result = result.strip()
    if not stripped_result:
        return None

    # NOTE Backwards compatibility when metadata key did not store range of key
    #   indexes but the value itself
    # NOTE We don't have to care about negative values with `isdecimal` check
    if not stripped_result.isdecimal():
        metadata_string = result
    else:
        keys = []
        for idx in range(int(stripped_result)):
            keys.append("{}{}".format(metadata_key, idx))
        metadata_string = get_workfile_metadata_string_for_keys(keys)

    # Replace quotes plaholders with their values
    metadata_string = (
        metadata_string
        .replace("{__sq__}", "'")
        .replace("{__dq__}", "\"")
    )
    return metadata_string


def get_workfile_metadata(metadata_key, default=None):
    """Read and parse metadata for specific key from current project workfile.

    Pipeline use function to store loaded and created instances within keys
    stored in `SECTION_NAME_INSTANCES` and `SECTION_NAME_CONTAINERS`
    constants.

    Args:
        metadata_key (str): Key defying which key should read. It is expected
            value contain json serializable string.
    """
    if default is None:
        default = []

    json_string = get_workfile_metadata_string(metadata_key)
    if json_string:
        try:
            return json.loads(json_string)
        except json.decoder.JSONDecodeError:
            # TODO remove when backwards compatibility of storing metadata
            # will be removed
            print((
                "Fixed invalid metadata in workfile."
                " Not serializable string was: {}"
            ).format(json_string))
            write_workfile_metadata(metadata_key, default)
    return default


def write_workfile_metadata(metadata_key, value):
    """Write metadata for specific key into current project workfile.

    George script has specific way how to work with quotes which should be
    solved automatically with this function.

    Args:
        metadata_key (str): Key defying under which key value will be stored.
        value (dict,list,str): Data to store they must be json serializable.
    """
    if isinstance(value, (dict, list)):
        value = json.dumps(value)

    if not value:
        value = ""

    # Handle quotes in dumped json string
    # - replace single and double quotes with placeholders
    value = (
        value
        .replace("'", "{__sq__}")
        .replace("\"", "{__dq__}")
    )
    chunks = split_metadata_string(value)
    chunks_len = len(chunks)

    write_template = "tv_writeprojectstring \"{}\" \"{}\" \"{}\""
    george_script_parts = []
    # Add information about chunks length to metadata key itself
    george_script_parts.append(
        write_template.format(METADATA_SECTION, metadata_key, chunks_len)
    )
    # Add chunk values to indexed metadata keys
    for idx, chunk_value in enumerate(chunks):
        sub_key = "{}{}".format(metadata_key, idx)
        george_script_parts.append(
            write_template.format(METADATA_SECTION, sub_key, chunk_value)
        )

    george_script = "\n".join(george_script_parts)

    return execute_george_through_file(george_script)


def get_current_workfile_context():
    """Return context in which was workfile saved."""
    return get_workfile_metadata(SECTION_NAME_CONTEXT, {})


def save_current_workfile_context(context):
    """Save context which was used to create a workfile."""
    return write_workfile_metadata(SECTION_NAME_CONTEXT, context)


def list_instances():
    """List all created instances from current workfile."""
    return get_workfile_metadata(SECTION_NAME_INSTANCES)


def write_instances(data):
    return write_workfile_metadata(SECTION_NAME_INSTANCES, data)


def get_containers():
    output = get_workfile_metadata(SECTION_NAME_CONTAINERS)
    if output:
        for item in output:
            if "objectName" not in item and "members" in item:
                members = item["members"]
                if isinstance(members, list):
                    members = "|".join([str(member) for member in members])
                item["objectName"] = members
    return output


def set_context_settings(project_name, asset_doc):
    """Set workfile settings by asset document data.

    Change fps, resolution and frame start/end.
    """

    width_key = "resolutionWidth"
    height_key = "resolutionHeight"

    width = asset_doc["data"].get(width_key)
    height = asset_doc["data"].get(height_key)
    if width is None or height is None:
        print("Resolution was not found!")
    else:
        execute_george(
            "tv_resizepage {} {} 0".format(width, height)
        )

    framerate = asset_doc["data"].get("fps")

    if framerate is not None:
        execute_george(
            "tv_framerate {} \"timestretch\"".format(framerate)
        )
    else:
        print("Framerate was not found!")

    frame_start = asset_doc["data"].get("frameStart")
    frame_end = asset_doc["data"].get("frameEnd")

    if frame_start is None or frame_end is None:
        print("Frame range was not found!")
        return

    handle_start = asset_doc["data"].get("handleStart")
    handle_end = asset_doc["data"].get("handleEnd")

    # Always start from 0 Mark In and set only Mark Out
    mark_in = 0
    mark_out = mark_in + (frame_end - frame_start) + handle_start + handle_end

    execute_george("tv_markin {} set".format(mark_in))
    execute_george("tv_markout {} set".format(mark_out))
