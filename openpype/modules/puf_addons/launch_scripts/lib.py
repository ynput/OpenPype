import os
import logging

from openpype.lib import StringTemplate
from openpype.lib.applications import (
    ApplicationManager
)
from openpype.pipeline import (
    registered_host,
    legacy_io,
    Anatomy,
)
from openpype.pipeline.workfile import (
    get_workfile_template_key_from_context,
    get_last_workfile_with_version,
)
from openpype.pipeline.template_data import get_template_data_with_names


log = logging.getLogger(__name__)


def get_last_workfile_for_task(
    project_name=None,
    asset_name=None,
    task_name=None,
    host_name=None,
    scene_dir=None,
    extensions=None
):
    """Return last existing workfile version for a task.

    Args:
        project_name (Optional[str]): Project name. Defaults to active project.
        asset_name (Optional[str]): Project name. Defaults to AVALON_ASSET.
        task_name (Optional[str]): Project name. Defaults to AVALON_TASK.
        host_name (Optional[str]): Project name. Defaults to AVALON_APP.
        scene_dir (Optional[str]): Include this scene subfolder for the
            workdir. Defaults to AVALON_SCENEDIR.
        extensions (list): Filename extensions to look for. This defaults
            to retrieving the extensions from the currently registered host.

    Returns:
        tuple: (str: filepath, int: Version number)

    """
    # Default fallbacks
    if project_name is None:
        project_name = legacy_io.active_project()
    if asset_name is None:
        asset_name = legacy_io.Session["AVALON_ASSET"]
    if task_name is None:
        task_name = legacy_io.Session["AVALON_TASK"]
    if host_name is None:
        host_name = os.environ["AVALON_APP"]
    if scene_dir is None:
        scene_dir = os.environ.get("AVALON_SCENEDIR")

    log.debug(
        "Searching last workfile for "
        f"{project_name} > {asset_name} > {task_name} (host: {host_name})"
    )

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

    if extensions is None:
        host = registered_host()
        extensions = host.get_workfile_extensions()

    folder_template = anatomy.templates[template_key]["folder"]
    work_root = StringTemplate.format_strict_template(
        folder_template, data
    )
    if scene_dir:
        work_root = os.path.join(work_root, scene_dir)

    log.debug(f"Looking in work root: {work_root}")

    filename, version = get_last_workfile_with_version(
        work_root, file_template, data, extensions
    )

    if filename:
        filename = os.path.join(work_root, filename)
    return filename, version


def find_app_variant(app_name, application_manager=None):
    """Searches for relevant application.

    If app_name equals e.g. `maya` or `houdini` it will try to retrieve
    the latest version available on the local machine.

    If app equals e.g. `maya/2023` or `houdini/19.0.435` (exact key for app
    variant) then it will try and launch that application.

    Arguments:
        application_manager (ApplicationManager)
        app_name (str): Name of host or full application name, e.g.
            "maya" or "maya/2023"

    Returns:
        str: Application group / variant name

    Raises:
        ValueError: if no valid application variant found
    """

    if application_manager is None:
        application_manager = ApplicationManager()

    if "/" in app_name:
        host, variant_key = app_name.split("/", 1)
    else:
        host = app_name
        variant_key = None

    app_group = application_manager.app_groups.get(host)
    if not app_group or not app_group.enabled:
        raise ValueError("No application {} configured".format(host))

    if not variant_key:
        # finds most up-to-date variant if any installed
        # TODO: This should actually be filtered by the project settings too
        #  so it only allows to retrieve Application version enabled in
        #  the project!
        variant = (
            application_manager.find_latest_available_variant_for_group(host)
        )
        if not variant:
            raise ValueError("No executable for {} found".format(host))
        variant_key = variant.name
    else:
        # ensure the requested version is available on this machine
        if variant_key not in app_group.variants:
            raise ValueError(
                "Variant {} not found amongst variants: {}".format(
                    variant_key, ", ".join(app_group.variants.keys())
                )
            )

        # Detect if executables exist
        for executable in app_group.variants[variant_key].executables:
            if executable.exists():
                break
        else:
            raise ValueError("No executable for {} found".format(app_name))

    return f"{host}/{variant_key}"
