# -*- coding: utf-8 -*-
"""Main entry point for AYON command.

Bootstrapping process of AYON.
"""
import os
import sys
import site
import traceback
import contextlib

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
        raise ValueError((
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

_pythonpath = os.getenv("PYTHONPATH", "")
_python_paths = _pythonpath.split(os.pathsep)
if not IS_BUILT_APPLICATION:
    # Code root defined by `start.py` directory
    AYON_ROOT = os.path.dirname(os.path.abspath(__file__))
    _dependencies_path = site.getsitepackages()[-1]
else:
    AYON_ROOT = os.path.dirname(sys.executable)

    # add dependencies folder to sys.pat for frozen code
    _dependencies_path = os.path.normpath(
        os.path.join(AYON_ROOT, "dependencies")
    )
# add stuff from `<frozen>/dependencies` to PYTHONPATH.
sys.path.append(_dependencies_path)
_python_paths.append(_dependencies_path)

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
# Add tools dir to sys path for pyblish UI discovery
tools_dir = os.path.join(AYON_ROOT, "openpype", "tools")
for path in (AYON_ROOT, common_python_vendor, tools_dir):
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
# Set name of pyblish UI import
os.environ["PYBLISH_GUI"] = "pyblish_pype"
# Set builtin OCIO root
os.environ["BUILTIN_OCIO_ROOT"] = os.path.join(
    AYON_ROOT,
    "vendor",
    "bin",
    "ocioconfig",
    "OpenColorIOConfigs"
)

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

from ayon_api.constants import SERVER_URL_ENV_KEY, SERVER_API_ENV_KEY
from ayon_common.connection.credentials import (
    ask_to_login_ui,
    add_server,
    need_server_or_login,
    load_environments,
    set_environments,
    create_global_connection,
    confirm_server_login,
)
from ayon_common.distribution.addon_distribution import AyonDistribution


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

    # Merge environments with current environments and update values
    if module_envs := modules_manager.collect_global_environments():
        parsed_envs = acre.parse(module_envs)
        env = acre.merge(parsed_envs, dict(os.environ))
        os.environ.clear()
        os.environ.update(env)


def _connect_to_ayon_server():
    load_environments()
    if not need_server_or_login():
        create_global_connection()
        return

    if HEADLESS_MODE_ENABLED:
        _print("!!! Cannot open v4 Login dialog in headless mode.")
        _print((
            "!!! Please use `{}` to specify server address"
            " and '{}' to specify user's token."
        ).format(SERVER_URL_ENV_KEY, SERVER_API_ENV_KEY))
        sys.exit(1)

    current_url = os.environ.get(SERVER_URL_ENV_KEY)
    url, token, username = ask_to_login_ui(current_url, always_on_top=True)
    if url is not None and token is not None:
        confirm_server_login(url, token, username)
        return

    if url is not None:
        add_server(url, username)

    _print("!!! Login was not successful.")
    sys.exit(0)


def _check_and_update_from_ayon_server():
    """Gets addon info from v4, compares with local folder and updates it.

    Raises:
        RuntimeError
    """

    distribution = AyonDistribution()
    distribution.distribute()
    distribution.validate_distribution()

    python_paths = [
        path
        for path in os.getenv("PYTHONPATH", "").split(os.pathsep)
        if path
    ]

    for path in distribution.get_sys_paths():
        sys.path.insert(0, path)
        if path not in python_paths:
            python_paths.append(path)
    os.environ["PYTHONPATH"] = os.pathsep.join(python_paths)


def boot():
    """Bootstrap OpenPype."""

    from openpype.version import __version__

    # TODO load version
    os.environ["OPENPYPE_VERSION"] = __version__
    os.environ["AYON_VERSION"] = __version__

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
        with contextlib.suppress(AttributeError, KeyError):
            del sys.modules[module_name]

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
        with contextlib.suppress(ValueError, OSError):
            t_width = os.get_terminal_size().columns - 2

        _header = f"*** AYON [{__version__}] "
        info.insert(0, _header + "-" * (t_width - len(_header)))

        for i in info:
            t.echo(i)

    try:
        cli.main(obj={}, prog_name="ayon")
    except Exception:  # noqa
        exc_info = sys.exc_info()
        _print("!!! AYON crashed:")
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
