app_framework = None
apps = []

from .api.utils import (
    setup
)

from .api.pipeline import (
    install,
    uninstall,
    ls,
    containerise,
    update_container,
    publish,
    launch_workfiles_app,
    maintained_selection,
    remove_instance,
    list_instances,
    imprint
)

from .api.lib import (
    FlameAppFramework,
    maintain_current_timeline,
    get_project_manager,
    get_current_project,
    get_current_timeline,
    create_bin,
)

from .api.menu import (
    FlameMenuProjectconnect,
    main_menu_build
)

from .api.workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)


__all__ = [
    "app_framework",
    "apps",

    # pipeline
    "install",
    "uninstall",
    "ls",
    "containerise",
    "update_container",
    "reload_pipeline",
    "publish",
    "launch_workfiles_app",
    "maintained_selection",
    "remove_instance",
    "list_instances",
    "imprint",

    # utils
    "setup",

    # lib
    "FlameAppFramework",
    "maintain_current_timeline",
    "get_project_manager",
    "get_current_project",
    "get_current_timeline",
    "create_bin",

    # menu
    "FlameMenuProjectconnect",
    "main_menu_build",

    # plugin

    # workio
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root"
]
