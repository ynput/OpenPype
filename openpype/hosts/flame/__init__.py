from .api.utils import (
    setup
)

from .api.pipeline import (
    install,
    uninstall,
    ls,
    containerise,
    update_container,
    remove_instance,
    list_instances,
    imprint,
    maintained_selection
)

from .api.lib import (
    FlameAppFramework,
    maintain_current_timeline,
    get_project_manager,
    get_current_project,
    get_current_sequence,
    create_bin,
    create_segment_data_marker,
    get_segment_data_marker,
    set_segment_data_marker,
    set_publish_attribute,
    get_publish_attribute,
    get_sequence_segments,
    maintained_segment_selection,
    reset_segment_selection,
    get_segment_attributes
)

from .api.menu import (
    FlameMenuProjectConnect,
    FlameMenuTimeline
)

from .api.workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

import os

HOST_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
API_DIR = os.path.join(HOST_DIR, "api")
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

app_framework = None
apps = []
selection = None


__all__ = [
    "HOST_DIR",
    "API_DIR",
    "PLUGINS_DIR",
    "PUBLISH_PATH",
    "LOAD_PATH",
    "CREATE_PATH",
    "INVENTORY_PATH",
    "INVENTORY_PATH",

    "app_framework",
    "apps",
    "selection",

    # pipeline
    "install",
    "uninstall",
    "ls",
    "containerise",
    "update_container",
    "reload_pipeline",
    "maintained_selection",
    "remove_instance",
    "list_instances",
    "imprint",
    "maintained_selection",

    # utils
    "setup",

    # lib
    "FlameAppFramework",
    "maintain_current_timeline",
    "get_project_manager",
    "get_current_project",
    "get_current_sequence",
    "create_bin",
    "create_segment_data_marker",
    "get_segment_data_marker",
    "set_segment_data_marker",
    "set_publish_attribute",
    "get_publish_attribute",
    "get_sequence_segments",
    "maintained_segment_selection",
    "reset_segment_selection",
    "get_segment_attributes"

    # menu
    "FlameMenuProjectConnect",
    "FlameMenuTimeline",

    # plugin

    # workio
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root"
]
