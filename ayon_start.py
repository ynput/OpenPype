# -*- coding: utf-8 -*-
"""Main entry point for AYON command.

Bootstrapping process of AYON.
"""
import os
import sys
import platform
import traceback
import subprocess
import distutils.spawn


# Enabled logging debug mode when "--debug" is passed
if "--verbose" in sys.argv:
    expected_values = (
        "Expected: notset, debug, info, warning, error, critical"
        " or integer [0-50]."
    )
    idx = sys.argv.index("--verbose")
    sys.argv.pop(idx)
    if idx < len(sys.argv):
        value = sys.argv.pop(idx)
    else:
        raise RuntimeError((
            f"Expect value after \"--verbose\" argument. {expected_values}"
        ))

    log_level = None
    low_value = value.lower()
    if low_value.isdigit():
        log_level = int(low_value)
    elif low_value == "notset":
        log_level = 0
    elif low_value == "debug":
        log_level = 10
    elif low_value == "info":
        log_level = 20
    elif low_value == "warning":
        log_level = 30
    elif low_value == "error":
        log_level = 40
    elif low_value == "critical":
        log_level = 50

    if log_level is None:
        raise RuntimeError((
            "Unexpected value after \"--verbose\" "
            f"argument \"{value}\". {expected_values}"
        ))

    os.environ["OPENPYPE_LOG_LEVEL"] = str(log_level)

# Enable debug mode, may affect log level if log level is not defined
if "--debug" in sys.argv:
    sys.argv.remove("--debug")
    os.environ["OPENPYPE_DEBUG"] = "1"

if "--automatic-tests" in sys.argv:
    sys.argv.remove("--automatic-tests")
    os.environ["IS_TEST"] = "1"

if "--use-staging" in sys.argv:
    sys.argv.remove("--use-staging")
    os.environ["OPENPYPE_USE_STAGING"] = "1"

_silent_commands = {
    "run",
    "igniter",
    "standalonepublisher",
    "extractenvironments",
    "version"
}
if "--headless" in sys.argv:
    os.environ["OPENPYPE_HEADLESS_MODE"] = "1"
    sys.argv.remove("--headless")
elif os.getenv("OPENPYPE_HEADLESS_MODE") != "1":
    os.environ.pop("OPENPYPE_HEADLESS_MODE", None)


IS_BUILT_APPLICATION = getattr(sys, "frozen", False)
HEADLESS_MODE_ENABLED = os.environ.get("OPENPYPE_HEADLESS_MODE") == "1"
SILENT_MODE_ENABLED = any(arg in _silent_commands for arg in sys.argv)

# AYON_ROOT is variable pointing to build (or code) directory
# WARNING `AYON_ROOT` must be defined before igniter import
# - igniter changes cwd which cause that filepath of this script won't lead
#   to right directory
_pythonpath = os.getenv("PYTHONPATH", "")
_python_paths = _pythonpath.split(os.pathsep)
if not IS_BUILT_APPLICATION:
    # Code root defined by `start.py` directory
    AYON_ROOT = os.path.dirname(os.path.abspath(__file__))
else:
    AYON_ROOT = os.path.dirname(sys.executable)

    # add dependencies folder to sys.pat for frozen code
    frozen_libs = os.path.normpath(
        os.path.join(AYON_ROOT, "dependencies")
    )
    # add stuff from `<frozen>/dependencies` to PYTHONPATH.
    sys.path.append(frozen_libs)
    _python_paths.append(frozen_libs)

# Vendored python modules that must not be in PYTHONPATH environment but
#   are required for OpenPype processes
sys.path.insert(0, os.path.join(AYON_ROOT, "vendor", "python"))

# Add common package to sys path
# - common contains common code for bootstraping and OpenPype processes
sys.path.insert(0, os.path.join(AYON_ROOT, "common"))

# This is content of 'core' addon which is ATM part of build
common_python_vendor = os.path.join(
    AYON_ROOT,
    "openpype",
    "vendor",
    "python",
    "common"
)
for path in (AYON_ROOT, common_python_vendor):
    while path in _python_paths:
        _python_paths.remove(path)

    while path in sys.path:
        sys.path.remove(path)

    _python_paths.insert(0, path)
    sys.path.insert(0, path)

os.environ["PYTHONPATH"] = os.pathsep.join(_python_paths)

# enabled AYON state
os.environ["USE_AYON_SERVER"] = "1"
# Set this to point either to `python` from venv in case of live code
#    or to `ayon` or `ayon_console` in case of frozen code
os.environ["OPENPYPE_EXECUTABLE"] = sys.executable
os.environ["AYON_ROOT"] = AYON_ROOT
os.environ["OPENPYPE_ROOT"] = AYON_ROOT
os.environ["OPENPYPE_REPOS_ROOT"] = AYON_ROOT
os.environ["AVALON_LABEL"] = "AYON"

import blessed  # noqa: E402
import certifi  # noqa: E402


if sys.__stdout__:
    term = blessed.Terminal()

    def _print(message: str):
        if SILENT_MODE_ENABLED:
            pass
        elif message.startswith("!!! "):
            print(f'{term.orangered2("!!! ")}{message[4:]}')
        elif message.startswith(">>> "):
            print(f'{term.aquamarine3(">>> ")}{message[4:]}')
        elif message.startswith("--- "):
            print(f'{term.darkolivegreen3("--- ")}{message[4:]}')
        elif message.startswith("*** "):
            print(f'{term.gold("*** ")}{message[4:]}')
        elif message.startswith("  - "):
            print(f'{term.wheat("  - ")}{message[4:]}')
        elif message.startswith("  . "):
            print(f'{term.tan("  . ")}{message[4:]}')
        elif message.startswith("     - "):
            print(f'{term.seagreen3("     - ")}{message[7:]}')
        elif message.startswith("     ! "):
            print(f'{term.goldenrod("     ! ")}{message[7:]}')
        elif message.startswith("     * "):
            print(f'{term.aquamarine1("     * ")}{message[7:]}')
        elif message.startswith("    "):
            print(f'{term.darkseagreen3("    ")}{message[4:]}')
        else:
            print(message)
else:
    def _print(message: str):
        if not SILENT_MODE_ENABLED:
            print(message)


# if SSL_CERT_FILE is not set prior to OpenPype launch, we set it to point
# to certifi bundle to make sure we have reasonably new CA certificates.
if not os.getenv("SSL_CERT_FILE"):
    os.environ["SSL_CERT_FILE"] = certifi.where()
elif os.getenv("SSL_CERT_FILE") != certifi.where():
    _print("--- your system is set to use custom CA certificate bundle.")

import igniter
from openpype_common.connection.server import (
    need_server_or_login,
    load_environments,
    set_environments,
)
from openpype_common.connection.credentials import (
    ask_to_login_ui,
    add_server,
    store_token
)
from openpype_common.distribution.addon_distribution import (
    get_addons_dir,
    get_dependencies_dir,
    make_sure_addons_are_updated,
    make_sure_venv_is_updated,
    get_default_addon_downloader,
)


def set_global_environments() -> None:
    """Set global OpenPype's environments."""
    import acre

    from openpype.settings import get_general_environments

    general_env = get_general_environments()

    # first resolve general environment because merge doesn't expect
    # values to be list.
    # TODO: switch to OpenPype environment functions
    merged_env = acre.merge(
        acre.compute(acre.parse(general_env), cleanup=False),
        dict(os.environ)
    )
    env = acre.compute(
        merged_env,
        cleanup=False
    )
    os.environ.clear()
    os.environ.update(env)

    # Hardcoded default values
    os.environ["PYBLISH_GUI"] = "pyblish_pype"
    # Change scale factor only if is not set
    if "QT_AUTO_SCREEN_SCALE_FACTOR" not in os.environ:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


def set_addons_environments():
    """Set global environments for OpenPype modules.

    This requires to have OpenPype in `sys.path`.
    """

    import acre
    from openpype.modules import ModulesManager

    modules_manager = ModulesManager()

    module_envs = modules_manager.collect_global_environments()

    # Merge environments with current environments and update values
    if module_envs:
        parsed_envs = acre.parse(module_envs)
        env = acre.merge(parsed_envs, dict(os.environ))
        os.environ.clear()
        os.environ.update(env)


def _validate_thirdparty_binaries():
    """Check existence of thirdpart executables."""

    low_platform = platform.system().lower()
    binary_vendors_dir = os.path.join(AYON_ROOT, "vendor", "bin")

    error_msg = (
        "Missing binary dependency {}. Please fetch thirdparty dependencies."
    )
    # Validate existence of FFmpeg
    ffmpeg_dir = os.path.join(binary_vendors_dir, "ffmpeg", low_platform)
    if low_platform == "windows":
        ffmpeg_dir = os.path.join(ffmpeg_dir, "bin")
    ffmpeg_executable = os.path.join(ffmpeg_dir, "ffmpeg")
    ffmpeg_result = distutils.spawn.find_executable(ffmpeg_executable)
    if ffmpeg_result is None:
        raise RuntimeError(error_msg.format("FFmpeg"))

    # Validate existence of OpenImageIO (not on MacOs)
    oiio_tool_path = None
    if low_platform == "linux":
        oiio_tool_path = os.path.join(
            binary_vendors_dir,
            "oiio",
            low_platform,
            "bin",
            "oiiotool"
        )
    elif low_platform == "windows":
        oiio_tool_path = os.path.join(
            binary_vendors_dir,
            "oiio",
            low_platform,
            "oiiotool"
        )
    oiio_result = None
    if oiio_tool_path is not None:
        oiio_result = distutils.spawn.find_executable(oiio_tool_path)

    if oiio_result is None:
        raise RuntimeError(error_msg.format("OpenImageIO"))


def _startup_validations():
    """Validations before OpenPype starts."""
    try:
        _validate_thirdparty_binaries()
    except Exception as exc:
        if HEADLESS_MODE_ENABLED:
            raise

        import tkinter
        from tkinter.messagebox import showerror

        root = tkinter.Tk()
        root.attributes("-alpha", 0.0)
        root.wm_state("iconic")
        if platform.system().lower() != "windows":
            root.withdraw()

        showerror(
            "Startup validations didn't pass",
            str(exc)
        )
        root.withdraw()
        sys.exit(1)


def _process_igniter_argument():
    """Process command line arguments.

    Returns:
        tuple: Return tuple with specific version to use (if any) and flag
            to prioritize staging (if set)
    """

    # handle igniter
    # this is helper to run igniter before anything else
    if "igniter" not in sys.argv:
        return

    if HEADLESS_MODE_ENABLED:
        _print("!!! Cannot open Igniter dialog in headless mode.")
        sys.exit(1)

    return_code = igniter.open_dialog()

    # this is when we want to run OpenPype without installing anything.
    # or we are ready to run.
    if return_code not in [2, 3]:
        sys.exit(return_code)

    idx = sys.argv.index("igniter")
    sys.argv.pop(idx)
    sys.argv.insert(idx, "tray")


def _connect_to_ayon_server():
    load_environments()
    if not need_server_or_login():
        return

    if HEADLESS_MODE_ENABLED:
        _print("!!! Cannot open v4 Login dialog in headless mode.")
        _print((
            "!!! Please use `AYON_SERVER_URL` to specify server address"
            " and 'AYON_TOKEN' to specify user's token."
        ))
        sys.exit(1)

    current_url = os.environ.get("AYON_SERVER_URL")
    url, token = ask_to_login_ui(current_url)
    if url is not None:
        add_server(url)
        if token is not None:
            store_token(url, token)
            set_environments(url, token)
            return

    _print("!!! Login was not successful.")
    sys.exit(0)


def _check_and_update_from_ayon_server():
    """Gets addon info from v4, compares with local folder and updates it.

    Raises:
        RuntimeError
    """

    local_addons_dir = get_addons_dir()
    local_dependencies_dir = get_dependencies_dir()

    default_downloader = get_default_addon_downloader()
    _print(f">>> Checking addons in {local_addons_dir} ...")
    make_sure_addons_are_updated(default_downloader, local_addons_dir)

    if local_addons_dir not in sys.path:
        _print(f"Adding {local_addons_dir} to sys path.")
        sys.path.insert(0, local_addons_dir)

    _print(f">>> Checking venvs in {local_dependencies_dir} ...")
    make_sure_venv_is_updated(default_downloader, local_dependencies_dir)


def boot():
    """Bootstrap OpenPype."""

    from openpype.version import __version__

    # TODO load version
    os.environ["OPENPYPE_VERSION"] = __version__
    os.environ["AYON_VERSION"] = __version__

    # ------------------------------------------------------------------------
    # Do necessary startup validations
    # ------------------------------------------------------------------------
    _startup_validations()

    # ------------------------------------------------------------------------
    # Process arguments
    # ------------------------------------------------------------------------
    if "igniter" in sys.argv:
        _process_igniter_argument()
    use_staging = os.environ.get("OPENPYPE_USE_STAGING") == "1"

    _connect_to_ayon_server()
    _check_and_update_from_ayon_server()

    # delete OpenPype module and it's submodules from cache so it is used from
    # specific version
    modules_to_del = [
        sys.modules.pop(module_name)
        for module_name in tuple(sys.modules)
        if module_name == "openpype" or module_name.startswith("openpype.")
    ]

    for module_name in modules_to_del:
        try:
            del sys.modules[module_name]
        except AttributeError:
            pass
        except KeyError:
            pass

    from openpype import cli
    from openpype.lib import terminal as t

    _print(">>> loading environments ...")
    _print("  - global AYON ...")
    set_global_environments()
    _print("  - for addons ...")
    set_addons_environments()

    # print info when not running scripts defined in 'silent commands'
    if not SILENT_MODE_ENABLED:
        info = get_info(use_staging)
        info.insert(0, f">>> Using AYON from [ {AYON_ROOT} ]")

        t_width = 20
        try:
            t_width = os.get_terminal_size().columns - 2
        except (ValueError, OSError):
            # running without terminal
            pass

        _header = f"*** AYON [{__version__}] "
        info.insert(0, _header + "-" * (t_width - len(_header)))

        for i in info:
            t.echo(i)

    try:
        cli.main(obj={}, prog_name="openpype")
    except Exception:  # noqa
        exc_info = sys.exc_info()
        _print("!!! OpenPype crashed:")
        traceback.print_exception(*exc_info)
        sys.exit(1)


def get_info(use_staging=None) -> list:
    """Print additional information to console."""

    inf = []
    if use_staging:
        inf.append(("AYON variant", "staging"))
    else:
        inf.append(("AYON variant", "production"))

    # NOTE add addons information

    maximum = max(len(i[0]) for i in inf)
    formatted = []
    for info in inf:
        padding = (maximum - len(info[0])) + 1
        formatted.append(f'... {info[0]}:{" " * padding}[ {info[1]} ]')
    return formatted


if __name__ == "__main__":
    boot()
