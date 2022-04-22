from .constants import (
    AVALON_CONTAINER_ID,
    HOST_WORKFILE_EXTENSIONS,
)

from .create import (
    BaseCreator,
    Creator,
    AutoCreator,
    CreatedInstance,
    CreatorError,

    LegacyCreator,
    legacy_create,

    discover_creator_plugins,
    discover_legacy_creator_plugins,
    register_creator_plugin,
    deregister_creator_plugin,
    register_creator_plugin_path,
    deregister_creator_plugin_path,
)

from .load import (
    HeroVersionType,
    IncompatibleLoaderError,
    LoaderPlugin,
    SubsetLoaderPlugin,

    discover_loader_plugins,
    register_loader_plugin,
    deregister_loader_plugin_path,
    register_loader_plugin_path,
    deregister_loader_plugin,

    load_container,
    remove_container,
    update_container,
    switch_container,

    loaders_from_representation,
    get_representation_path,
    get_representation_context,
    get_repres_contexts,
)

from .publish import (
    PublishValidationError,
    PublishXmlValidationError,
    KnownPublishError,
    OpenPypePyblishPluginMixin,
    OptionalPyblishPluginMixin,
)

from .actions import (
    LauncherAction,

    InventoryAction,

    discover_launcher_actions,
    register_launcher_action,
    register_launcher_action_path,

    discover_inventory_actions,
    register_inventory_action,
    register_inventory_action_path,
    deregister_inventory_action,
    deregister_inventory_action_path,
)

from .context_tools import (
    install_openpype_plugins,
    install_host,
    uninstall_host,
    is_installed,

    register_root,
    registered_root,

    register_host,
    registered_host,
    deregister_host,
)
install = install_host
uninstall = uninstall_host


__all__ = (
    "AVALON_CONTAINER_ID",
    "HOST_WORKFILE_EXTENSIONS",

    "attribute_definitions",

    # --- Create ---
    "BaseCreator",
    "Creator",
    "AutoCreator",
    "CreatedInstance",
    "CreatorError",

    "CreatorError",

    # - legacy creation
    "LegacyCreator",
    "legacy_create",

    "discover_creator_plugins",
    "discover_legacy_creator_plugins",
    "register_creator_plugin",
    "deregister_creator_plugin",
    "register_creator_plugin_path",
    "deregister_creator_plugin_path",

    # --- Load ---
    "HeroVersionType",
    "IncompatibleLoaderError",
    "LoaderPlugin",
    "SubsetLoaderPlugin",

    "discover_loader_plugins",
    "register_loader_plugin",
    "deregister_loader_plugin_path",
    "register_loader_plugin_path",
    "deregister_loader_plugin",

    "load_container",
    "remove_container",
    "update_container",
    "switch_container",

    "loaders_from_representation",
    "get_representation_path",
    "get_representation_context",
    "get_repres_contexts",

    # --- Publish ---
    "PublishValidationError",
    "PublishXmlValidationError",
    "KnownPublishError",
    "OpenPypePyblishPluginMixin",
    "OptionalPyblishPluginMixin",

    # --- Actions ---
    "LauncherAction",
    "InventoryAction",

    "discover_launcher_actions",
    "register_launcher_action",
    "register_launcher_action_path",

    "discover_inventory_actions",
    "register_inventory_action",
    "register_inventory_action_path",
    "deregister_inventory_action",
    "deregister_inventory_action_path",

    # --- Process context ---
    "install_openpype_plugins",
    "install_host",
    "uninstall_host",
    "is_installed",

    "register_root",
    "registered_root",

    "register_host",
    "registered_host",
    "deregister_host",

    # Backwards compatible function names
    "install",
    "uninstall",
)
