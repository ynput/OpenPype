from openpype.settings import lib as op_settings_lib

_typing = False
if _typing:
    from typing import Any

    from . import backends
del _typing


class VersionControlDisabledError(Exception):
    def __init__(self):
        # type: () -> None
        super().__init__("Version control is disabled!")


class NoActiveVersionControlError(Exception):
    def __init__(self, message="No version control set!"):
        # type: (str) -> None
        super().__init__(message)


class NoVersionControlWithNameFoundError(NoActiveVersionControlError):
    def __init__(self, vcs_name):
        # type: (str) -> None
        super().__init__("No version control named: '{}'' found!".format(vcs_name))


class NoVersionControlBackendFoundError(NoActiveVersionControlError):
    def __init__(self, vcs_name):
        # type: (str) -> None
        super().__init__("Version control: '{}'' has no backend attribute!".format(vcs_name))


class NoVersionControlClassFoundError(NoActiveVersionControlError):
    def __init__(self, vcs_name, vcs_class_name):
        # type: (str, str) -> None
        super().__init__("Version control: '{}'' has no class named {}!".format(vcs_name, vcs_class_name))


def get_version_control_settings():
    # type: () -> dict[str, Any]

    system_settings = op_settings_lib.get_system_settings()
    module_settings = system_settings["modules"]
    if "version_control" not in module_settings:
        return {}

    return module_settings["version_control"]


def is_version_control_enabled():
    # type: () -> bool
    from .. import version_control

    if not version_control._compatible_dcc:
        return False

    version_control_settings = get_version_control_settings()
    if not version_control_settings:
        return False

    return version_control_settings["enabled"]


def get_active_version_control_system():
    # type: () -> str | None

    if not is_version_control_enabled():
        return

    version_control_settings = get_version_control_settings()
    return version_control_settings["active_version_control_system"]


_active_version_control_backend = None  # type: backends.abstract.VersionControl | None


def get_active_version_control_backend():
    # type: () -> backends.abstract.VersionControl | None
    """
    Get the active version control backend.

    Raises VersionControlDisabledError if version control is disabled
    or NoActiveVersionControlError if no backend is set.

    Returned object is a static sub-class of `backends.abstract.VersionControl`.
    """
    global _active_version_control_backend

    if _active_version_control_backend is not None:
        return _active_version_control_backend

    try:
        from . import backends
    except ImportError as error:
        if "No module named P4API" not in str(error):
            raise
        return

    active_vcs = get_active_version_control_system()
    if active_vcs is None:
        raise VersionControlDisabledError()

    try:
        backend_module = getattr(backends, active_vcs)
    except AttributeError as error:
        if active_vcs in str(error):
            raise NoVersionControlWithNameFoundError(active_vcs)
        raise

    try:
        backend_sub_module = getattr(backend_module, "backend")
    except AttributeError as error:
        if "backend" in str(error):
            raise NoVersionControlBackendFoundError(active_vcs)

        raise

    try:
        backend_class = getattr(
            backend_sub_module, f"VersionControl{active_vcs.title()}"
        )  # type: type[backends.abstract.VersionControl]
        _active_version_control_backend = backend_class()
        return _active_version_control_backend
    except AttributeError as error:
        if f"VersionControl{active_vcs.title()}" in str(error):
            raise NoVersionControlClassFoundError(active_vcs, f"VersionControl{active_vcs.title()}")

        raise
