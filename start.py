# -*- coding: utf-8 -*-
"""Main entry point for AYON command.

Bootstrapping process of AYON.
"""
import os
import sys
import site
import traceback
import contextlib


from version import __version__

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
    os.environ["AYON_LOG_LEVEL"] = str(log_level)

os.environ["AYON_VERSION"] = __version__

# Enable debug mode, may affect log level if log level is not defined
if "--debug" in sys.argv:
    sys.argv.remove("--debug")
    os.environ["AYON_DEBUG"] = "1"
    os.environ["OPENPYPE_DEBUG"] = "1"

SKIP_HEADERS = False
if "--skip-headers" in sys.argv:
    sys.argv.remove("--skip-headers")
    SKIP_HEADERS = True

if "--use-staging" in sys.argv:
    sys.argv.remove("--use-staging")
    os.environ["AYON_USE_STAGING"] = "1"
    os.environ["OPENPYPE_USE_STAGING"] = "1"

if "--headless" in sys.argv:
    os.environ["AYON_HEADLESS_MODE"] = "1"
    os.environ["OPENPYPE_HEADLESS_MODE"] = "1"
    sys.argv.remove("--headless")

elif (
    os.getenv("AYON_HEADLESS_MODE") != "1"
    or os.getenv("OPENPYPE_HEADLESS_MODE") != "1"
):
    os.environ.pop("AYON_HEADLESS_MODE", None)
    os.environ.pop("OPENPYPE_HEADLESS_MODE", None)

elif (
    os.getenv("AYON_HEADLESS_MODE")
    != os.getenv("OPENPYPE_HEADLESS_MODE")
):
    os.environ["OPENPYPE_HEADLESS_MODE"] = (
        os.environ["AYON_HEADLESS_MODE"]
    )

IS_BUILT_APPLICATION = getattr(sys, "frozen", False)
HEADLESS_MODE_ENABLED = os.getenv("AYON_HEADLESS_MODE") == "1"

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

os.environ["PYTHONPATH"] = os.pathsep.join(_python_paths)

# enabled AYON state
os.environ["USE_AYON_SERVER"] = "1"
# Set this to point either to `python` from venv in case of live code
#    or to `ayon` or `ayon_console` in case of frozen code
os.environ["AYON_EXECUTABLE"] = sys.executable
os.environ["OPENPYPE_EXECUTABLE"] = sys.executable
os.environ["AYON_ROOT"] = AYON_ROOT
os.environ["OPENPYPE_ROOT"] = AYON_ROOT
os.environ["OPENPYPE_REPOS_ROOT"] = AYON_ROOT
os.environ["AYON_MENU_LABEL"] = "AYON"
os.environ["AVALON_LABEL"] = "AYON"

import blessed  # noqa: E402
import certifi  # noqa: E402


if sys.__stdout__:
    term = blessed.Terminal()

    def _print(message: str):
        if message.startswith("!!! "):
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
    """Bootstrap AYON."""

    use_staging = os.environ.get("AYON_USE_STAGING") == "1"

    _connect_to_ayon_server()
    _check_and_update_from_ayon_server()

    from openpype import cli

    _print(">>> loading environments ...")
    _print("  - global AYON ...")
    set_global_environments()
    _print("  - for addons ...")
    set_addons_environments()

    # print info when not running scripts defined in 'silent commands'
    if not SKIP_HEADERS:
        info = get_info(use_staging)
        info.insert(0, f">>> Using AYON from [ {AYON_ROOT} ]")

        t_width = 20
        with contextlib.suppress(ValueError, OSError):
            t_width = os.get_terminal_size().columns - 2

        _header = f"*** AYON [{__version__}] "
        info.insert(0, _header + "-" * (t_width - len(_header)))

        for i in info:
            _print(i)

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
    inf.append(("AYON bundle", os.getenv("AYON_BUNDLE")))

    # NOTE add addons information

    maximum = max(len(i[0]) for i in inf)
    formatted = []
    for info in inf:
        padding = (maximum - len(info[0])) + 1
        formatted.append(f'... {info[0]}:{" " * padding}[ {info[1]} ]')
    return formatted


if __name__ == "__main__":
    boot()
