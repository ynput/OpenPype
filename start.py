# -*- coding: utf-8 -*-
"""Main entry point for OpenPype command.

Bootstrapping process of OpenPype is as follows:

`OPENPYPE_PATH` is checked for existence - either one from environment or
from user settings. Precedence takes the one set by environment.

On this path we try to find OpenPype in directories version string in their
names. For example: `openpype-v3.0.1-foo` is valid name, or
even `foo_3.0.2` - as long as version can be determined from its name
_AND_ file `openpype/openpype/version.py` can be found inside, it is
considered OpenPype installation.

If no OpenPype repositories are found in `OPENPYPE_PATH` (user data dir)
then **Igniter** (OpenPype setup tool) will launch its GUI.

It can be used to specify `OPENPYPE_PATH` or if it is _not_ specified, current
*"live"* repositories will be used to create zip file and copy it to
appdata dir in user home and extract it there. Version will be determined by
version specified in OpenPype module.

If OpenPype repository directories are found in default install location
(user data dir) or in `OPENPYPE_PATH`, it will get list of those dirs
there and use latest one or the one specified with optional `--use-version`
command line argument. If the one specified doesn't exist then latest
available version will be used. All repositories in that dir will be added
to `sys.path` and `PYTHONPATH`.

If OpenPype is live (not frozen) then current version of OpenPype module
will be used. All directories under `repos` will be added to `sys.path` and
`PYTHONPATH`.

OpenPype depends on connection to `MongoDB`_. You can specify MongoDB
connection string via `OPENPYPE_MONGO` set in environment or it can be set
in user settings or via **Igniter** GUI.

So, bootstrapping OpenPype looks like this::

.. code-block:: bash

┌───────────────────────────────────────────────────────┐
│ Determine MongoDB connection:                         │
│ Use `OPENPYPE_MONGO`, system keyring `openPypeMongo`  │
└──────────────────────────┬────────────────────────────┘
                  ┌───- Found? -─┐
                 YES             NO
                  │              │
                  │       ┌──────┴──────────────┐
                  │       │ Fire up Igniter GUI ├<-────────┐
                  │       │ and ask User        │          │
                  │       └─────────────────────┘          │
                  │                                        │
                  │                                        │
┌─────────────────┴─────────────────────────────────────┐  │
│ Get location of OpenPype:                             │  │
│   1) Test for `OPENPYPE_PATH` environment variable    │  │
│   2) Test `openPypePath` in registry setting          │  │
│   3) Test user data directory                         │  │
│ ····················································· │  │
│ If running from frozen code:                          │  │
│   - Use latest one found in user data dir             │  │
│ If running from live code:                            │  │
│   - Use live code and install it to user data dir     │  │
│ * can be overridden with `--use-version` argument     │  │
└──────────────────────────┬────────────────────────────┘  │
              ┌─- Is OpenPype found? -─┐                   │
             YES                       NO                  │
              │                        │                   │
              │      ┌─────────────────┴─────────────┐     │
              │      │ Look in `OPENPYPE_PATH`, find │     │
              │      │ latest version and install it │     │
              │      │ to user data dir.             │     │
              │      └──────────────┬────────────────┘     │
              │         ┌─- Is OpenPype found? -─┐         │
              │        YES                       NO -──────┘
              │         │
              ├<-───────┘
              │
┌─────────────┴────────────┐
│      Run OpenPype        │
└─────═══════════════──────┘


Todo:
    Move or remove bootstrapping environments out of the code.

Attributes:
    silent_commands (set): list of commands for which we won't print OpenPype
        logo and info header.

.. _MongoDB:
   https://www.mongodb.com/

"""
import os
import re
import sys
import platform
import traceback
import subprocess
import site
import distutils.spawn
from pathlib import Path

# OPENPYPE_ROOT is variable pointing to build (or code) directory
# WARNING `OPENPYPE_ROOT` must be defined before igniter import
# - igniter changes cwd which cause that filepath of this script won't lead
#   to right directory
if not getattr(sys, 'frozen', False):
    # Code root defined by `start.py` directory
    OPENPYPE_ROOT = os.path.dirname(os.path.abspath(__file__))
else:
    OPENPYPE_ROOT = os.path.dirname(sys.executable)

    # add dependencies folder to sys.pat for frozen code
    frozen_libs = os.path.normpath(
        os.path.join(OPENPYPE_ROOT, "dependencies")
    )
    sys.path.append(frozen_libs)
    sys.path.insert(0, OPENPYPE_ROOT)
    # add stuff from `<frozen>/dependencies` to PYTHONPATH.
    pythonpath = os.getenv("PYTHONPATH", "")
    paths = pythonpath.split(os.pathsep)
    paths.append(frozen_libs)
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)

# Vendored python modules that must not be in PYTHONPATH environment but
#   are required for OpenPype processes
vendor_python_path = os.path.join(OPENPYPE_ROOT, "vendor", "python")
sys.path.insert(0, vendor_python_path)

import blessed  # noqa: E402
import certifi  # noqa: E402


if sys.__stdout__:
    term = blessed.Terminal()

    def _print(message: str):
        if message.startswith("!!! "):
            print("{}{}".format(term.orangered2("!!! "), message[4:]))
            return
        if message.startswith(">>> "):
            print("{}{}".format(term.aquamarine3(">>> "), message[4:]))
            return
        if message.startswith("--- "):
            print("{}{}".format(term.darkolivegreen3("--- "), message[4:]))
            return
        if message.startswith("*** "):
            print("{}{}".format(term.gold("*** "), message[4:]))
            return
        if message.startswith("  - "):
            print("{}{}".format(term.wheat("  - "), message[4:]))
            return
        if message.startswith("  . "):
            print("{}{}".format(term.tan("  . "), message[4:]))
            return
        if message.startswith("     - "):
            print("{}{}".format(term.seagreen3("     - "), message[7:]))
            return
        if message.startswith("     ! "):
            print("{}{}".format(term.goldenrod("     ! "), message[7:]))
            return
        if message.startswith("     * "):
            print("{}{}".format(term.aquamarine1("     * "), message[7:]))
            return
        if message.startswith("    "):
            print("{}{}".format(term.darkseagreen3("    "), message[4:]))
            return

        print(message)
else:
    def _print(message: str):
        print(message)


# if SSL_CERT_FILE is not set prior to OpenPype launch, we set it to point
# to certifi bundle to make sure we have reasonably new CA certificates.
if os.getenv("SSL_CERT_FILE") and \
        os.getenv("SSL_CERT_FILE") != certifi.where():
    _print("--- your system is set to use custom CA certificate bundle.")
else:
    ssl_cert_file = certifi.where()
    os.environ["SSL_CERT_FILE"] = ssl_cert_file

if "--headless" in sys.argv:
    os.environ["OPENPYPE_HEADLESS_MODE"] = "1"
    sys.argv.remove("--headless")
else:
    if os.getenv("OPENPYPE_HEADLESS_MODE") != "1":
        os.environ.pop("OPENPYPE_HEADLESS_MODE", None)

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
            "Expect value after \"--verbose\" argument. {}"
        ).format(expected_values))

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
            "Unexpected value after \"--verbose\" argument \"{}\". {}"
        ).format(value, expected_values))

    os.environ["OPENPYPE_LOG_LEVEL"] = str(log_level)

# Enable debug mode, may affect log level if log level is not defined
if "--debug" in sys.argv:
    sys.argv.remove("--debug")
    os.environ["OPENPYPE_DEBUG"] = "1"


import igniter  # noqa: E402
from igniter import BootstrapRepos  # noqa: E402
from igniter.tools import (
    get_openpype_global_settings,
    get_openpype_path_from_settings,
    validate_mongo_connection,
    OpenPypeVersionNotFound
)  # noqa
from igniter.bootstrap_repos import OpenPypeVersion  # noqa: E402

bootstrap = BootstrapRepos()
silent_commands = {"run", "igniter", "standalonepublisher",
                   "extractenvironments"}


def list_versions(openpype_versions: list, local_version=None) -> None:
    """Print list of detected versions."""
    _print("  - Detected versions:")
    for v in sorted(openpype_versions):
        _print(f"     - {v}: {v.path}")
    if not openpype_versions:
        _print("     ! none in repository detected")
    if local_version:
        _print(f"     * local version {local_version}")


def set_openpype_global_environments() -> None:
    """Set global OpenPype's environments."""
    import acre

    from openpype.settings import get_general_environments

    general_env = get_general_environments()

    merged_env = acre.merge(
        acre.parse(general_env),
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


def run(arguments: list, env: dict = None) -> int:
    """Use correct executable to run stuff.

    This passing arguments to correct OpenPype executable. If OpenPype is run
    from live sources, executable will be `python` in virtual environment.
    If running from frozen code, executable will be `openpype_console` or
    `openpype_gui`. Its equivalent in live code is `python start.py`.

    Args:
        arguments (list): Argument list to pass OpenPype.
        env (dict, optional): Dictionary containing environment.

    Returns:
        int: Process return code.

    """
    if getattr(sys, 'frozen', False):
        interpreter = [sys.executable]
    else:
        interpreter = [sys.executable, __file__]

    interpreter.extend(arguments)

    p = subprocess.Popen(interpreter, env=env)
    p.wait()
    _print(f">>> done [{p.returncode}]")
    return p.returncode


def run_disk_mapping_commands(settings):
    """ Run disk mapping command

        Used to map shared disk for OP to pull codebase.
    """

    low_platform = platform.system().lower()
    disk_mapping = settings.get("disk_mapping")
    if not disk_mapping:
        return

    mappings = disk_mapping.get(low_platform) or []
    for source, destination in mappings:
        destination = destination.rstrip('/')
        source = source.rstrip('/')

        if low_platform == "windows":
            args = ["subst", destination, source]
        elif low_platform == "darwin":
            scr = "do shell script \"ln -s {} {}\" with administrator privileges".format(source, destination)  # noqa: E501
            args = ["osascript", "-e", scr]
        else:
            args = ["sudo", "ln", "-s", source, destination]

        _print("disk mapping args:: {}".format(args))
        try:
            if not os.path.exists(destination):
                output = subprocess.Popen(args)
                if output.returncode and output.returncode != 0:
                    exc_msg = "Executing was not successful: \"{}\"".format(
                        args)

                    raise RuntimeError(exc_msg)
        except TypeError as exc:
            _print("Error {} in mapping drive {}, {}".format(str(exc),
                                                             source,
                                                             destination))
            raise


def set_avalon_environments():
    """Set avalon specific environments.

    These are non modifiable environments for avalon workflow that must be set
    before avalon module is imported because avalon works with globals set with
    environment variables.
    """

    avalon_db = os.environ.get("AVALON_DB") or "avalon"  # for tests
    os.environ.update({
        # Mongo DB name where avalon docs are stored
        "AVALON_DB": avalon_db,
        # Name of config
        "AVALON_LABEL": "OpenPype"
    })


def set_modules_environments():
    """Set global environments for OpenPype modules.

    This requires to have OpenPype in `sys.path`.
    """

    from openpype.modules import ModulesManager
    import acre

    modules_manager = ModulesManager()

    module_envs = modules_manager.collect_global_environments()
    publish_plugin_dirs = modules_manager.collect_plugin_paths()["publish"]

    # Set pyblish plugins paths if any module want to register them
    if publish_plugin_dirs:
        publish_paths_str = os.environ.get("PYBLISHPLUGINPATH") or ""
        publish_paths = publish_paths_str.split(os.pathsep)
        _publish_paths = {
            os.path.normpath(path) for path in publish_paths if path
        }
        for path in publish_plugin_dirs:
            _publish_paths.add(os.path.normpath(path))
        module_envs["PYBLISHPLUGINPATH"] = os.pathsep.join(_publish_paths)

    # Merge environments with current environments and update values
    if module_envs:
        parsed_envs = acre.parse(module_envs)
        env = acre.merge(parsed_envs, dict(os.environ))
        os.environ.clear()
        os.environ.update(env)


def _startup_validations():
    """Validations before OpenPype starts."""
    try:
        _validate_thirdparty_binaries()
    except Exception as exc:
        if os.environ.get("OPENPYPE_HEADLESS_MODE"):
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


def _validate_thirdparty_binaries():
    """Check existence of thirdpart executables."""
    low_platform = platform.system().lower()
    binary_vendors_dir = os.path.join(
        os.environ["OPENPYPE_ROOT"],
        "vendor",
        "bin"
    )

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


def _process_arguments() -> tuple:
    """Process command line arguments.

    Returns:
        tuple: Return tuple with specific version to use (if any) and flag
            to prioritize staging (if set)
    """
    # check for `--use-version=3.0.0` argument and `--use-staging`
    use_version = None
    use_staging = False
    commands = []

    # OpenPype version specification through arguments
    use_version_arg = "--use-version"

    for arg in sys.argv:
        if arg.startswith(use_version_arg):
            # Remove arg from sys argv
            sys.argv.remove(arg)
            # Extract string after use version arg
            use_version_value = arg[len(use_version_arg):]

            if (
                not use_version_value
                or not use_version_value.startswith("=")
            ):
                _print("!!! Please use option --use-version like:")
                _print("    --use-version=3.0.0")
                sys.exit(1)

            version_str = use_version_value[1:]
            use_version = None
            if version_str.lower() == "latest":
                use_version = "latest"
            else:
                m = re.search(
                    r"(?P<version>\d+\.\d+\.\d+(?:\S*)?)", version_str
                )
                if m and m.group('version'):
                    use_version = m.group('version')
                    _print(">>> Requested version [ {} ]".format(use_version))
                    if "+staging" in use_version:
                        use_staging = True
                    break

            if use_version is None:
                _print("!!! Requested version isn't in correct format.")
                _print(("    Use --list-versions to find out"
                       " proper version string."))
                sys.exit(1)

        if arg == "--validate-version":
            _print("!!! Please use option --validate-version like:")
            _print("    --validate-version=3.0.0")
            sys.exit(1)

        if arg.startswith("--validate-version="):
            m = re.search(
                r"--validate-version=(?P<version>\d+\.\d+\.\d+(?:\S*)?)", arg)
            if m and m.group('version'):
                use_version = m.group('version')
                sys.argv.remove(arg)
                commands.append("validate")
            else:
                _print("!!! Requested version isn't in correct format.")
                _print(("    Use --list-versions to find out"
                        " proper version string."))
                sys.exit(1)

    if "--use-staging" in sys.argv:
        use_staging = True
        sys.argv.remove("--use-staging")

    if "--list-versions" in sys.argv:
        commands.append("print_versions")
        sys.argv.remove("--list-versions")

    # handle igniter
    # this is helper to run igniter before anything else
    if "igniter" in sys.argv:
        if os.getenv("OPENPYPE_HEADLESS_MODE") == "1":
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

    return use_version, use_staging, commands


def _determine_mongodb() -> str:
    """Determine mongodb connection string.

    First use ``OPENPYPE_MONGO`` environment variable, then system keyring.
    Then try to run **Igniter UI** to let user specify it.

    Returns:
        str: mongodb connection URL

    Raises:
        RuntimeError: if mongodb connection url cannot by determined.

    """

    openpype_mongo = os.getenv("OPENPYPE_MONGO", None)
    if not openpype_mongo:
        # try system keyring
        try:
            openpype_mongo = bootstrap.secure_registry.get_item(
                "openPypeMongo"
            )
        except ValueError:
            pass

    if openpype_mongo:
        result, msg = validate_mongo_connection(openpype_mongo)
        if not result:
            _print(msg)
            openpype_mongo = None

    if not openpype_mongo:
        _print("*** No DB connection string specified.")
        if os.getenv("OPENPYPE_HEADLESS_MODE") == "1":
            _print("!!! Cannot open Igniter dialog in headless mode.")
            _print(
                "!!! Please use `OPENPYPE_MONGO` to specify server address.")
            sys.exit(1)
        _print("--- launching setup UI ...")

        result = igniter.open_dialog()
        if result == 0:
            raise RuntimeError("MongoDB URL was not defined")

        openpype_mongo = os.getenv("OPENPYPE_MONGO")
        if not openpype_mongo:
            try:
                openpype_mongo = bootstrap.secure_registry.get_item(
                    "openPypeMongo")
            except ValueError:
                raise RuntimeError("Missing MongoDB url")

    return openpype_mongo


def _initialize_environment(openpype_version: OpenPypeVersion) -> None:
    version_path = openpype_version.path
    os.environ["OPENPYPE_VERSION"] = str(openpype_version)
    # set OPENPYPE_REPOS_ROOT to point to currently used OpenPype version.
    os.environ["OPENPYPE_REPOS_ROOT"] = os.path.normpath(
        version_path.as_posix()
    )
    # inject version to Python environment (sys.path, ...)
    _print(">>> Injecting OpenPype version to running environment  ...")
    bootstrap.add_paths_from_directory(version_path)

    # Additional sys paths related to OPENPYPE_REPOS_ROOT directory
    # TODO move additional paths to `boot` part when OPENPYPE_REPOS_ROOT will
    # point to same hierarchy from code and from frozen OpenPype
    additional_paths = [
        os.environ["OPENPYPE_REPOS_ROOT"],
        # add OpenPype tools
        os.path.join(os.environ["OPENPYPE_REPOS_ROOT"], "openpype", "tools"),
        # add common OpenPype vendor
        # (common for multiple Python interpreter versions)
        os.path.join(
            os.environ["OPENPYPE_REPOS_ROOT"],
            "openpype",
            "vendor",
            "python",
            "common"
        )
    ]

    split_paths = os.getenv("PYTHONPATH", "").split(os.pathsep)
    for path in additional_paths:
        split_paths.insert(0, path)
        sys.path.insert(0, path)

    os.environ["PYTHONPATH"] = os.pathsep.join(split_paths)


def _find_frozen_openpype(use_version: str = None,
                          use_staging: bool = False) -> Path:
    """Find OpenPype to run from frozen code.

    This will process and modify environment variables:
    ``PYTHONPATH``, ``OPENPYPE_VERSION``, ``OPENPYPE_REPOS_ROOT``

    Args:
        use_version (str, optional): Try to use specified version.
        use_staging (bool, optional): Prefer *staging* flavor over production.

    Returns:
        Path: Path to version to be used.

    Raises:
        RuntimeError: If no OpenPype version are found or no staging version
            (if requested).

    """
    # Collect OpenPype versions
    installed_version = OpenPypeVersion.get_installed_version()
    # Expected version that should be used by studio settings
    #   - this option is used only if version is not explictly set and if
    #       studio has set explicit version in settings
    studio_version = OpenPypeVersion.get_expected_studio_version(use_staging)

    if use_version is not None:
        # Specific version is defined
        if use_version.lower() == "latest":
            # Version says to use latest version
            _print("Finding latest version defined by use version")
            openpype_version = bootstrap.find_latest_openpype_version(
                use_staging
            )
        else:
            _print("Finding specified version \"{}\"".format(use_version))
            openpype_version = bootstrap.find_openpype_version(
                use_version, use_staging
            )

        if openpype_version is None:
            raise OpenPypeVersionNotFound(
                "Requested version \"{}\" was not found.".format(
                    use_version
                )
            )

    elif studio_version is not None:
        # Studio has defined a version to use
        _print("Finding studio version \"{}\"".format(studio_version))
        openpype_version = bootstrap.find_openpype_version(
            studio_version, use_staging
        )
        if openpype_version is None:
            raise OpenPypeVersionNotFound((
                "Requested OpenPype version \"{}\" defined by settings"
                " was not found."
            ).format(studio_version))

    else:
        # Default behavior to use latest version
        _print("Finding latest version")
        openpype_version = bootstrap.find_latest_openpype_version(
            use_staging
        )
        if openpype_version is None:
            if use_staging:
                reason = "Didn't find any staging versions."
            else:
                reason = "Didn't find any versions."
            raise OpenPypeVersionNotFound(reason)

    # get local frozen version and add it to detected version so if it is
    # newer it will be used instead.
    if installed_version == openpype_version:
        version_path = _bootstrap_from_code(use_version, use_staging)
        openpype_version = OpenPypeVersion(
            version=BootstrapRepos.get_version(version_path),
            path=version_path)
        _initialize_environment(openpype_version)
        return version_path

    # test if latest detected is installed (in user data dir)
    is_inside = False
    try:
        is_inside = openpype_version.path.resolve().relative_to(
            bootstrap.data_dir)
    except ValueError:
        # if relative path cannot be calculated, openpype version is not
        # inside user data dir
        pass

    if not is_inside:
        # install latest version to user data dir
        if os.getenv("OPENPYPE_HEADLESS_MODE") == "1":
            version_path = bootstrap.install_version(
                openpype_version, force=True
            )
        else:
            version_path = igniter.open_update_window(openpype_version)

        openpype_version.path = version_path
        _initialize_environment(openpype_version)
        return openpype_version.path

    if openpype_version.path.is_file():
        _print(">>> Extracting zip file ...")
        try:
            version_path = bootstrap.extract_openpype(openpype_version)
        except OSError as e:
            _print("!!! failed: {}".format(str(e)))
            sys.exit(1)
        else:
            # cleanup zip after extraction
            os.unlink(openpype_version.path)

        openpype_version.path = version_path

    _initialize_environment(openpype_version)
    return openpype_version.path


def _bootstrap_from_code(use_version, use_staging):
    """Bootstrap live code (or the one coming with frozen OpenPype.

    Args:
        use_version: (str): specific version to use.

    Returns:
        Path: path to sourced version.

    """
    # run through repos and add them to `sys.path` and `PYTHONPATH`
    # set root
    _openpype_root = OPENPYPE_ROOT
    # Unset use version if latest should be used
    #   - when executed from code then code is expected as latest
    #   - when executed from build then build is already marked as latest
    #       in '_find_frozen_openpype'
    if use_version and use_version.lower() == "latest":
        use_version = None

    if getattr(sys, 'frozen', False):
        local_version = bootstrap.get_version(Path(_openpype_root))
        switch_str = f" - will switch to {use_version}" if use_version else ""
        _print(f"  - booting version: {local_version}{switch_str}")
        assert local_version
    else:
        # get current version of OpenPype
        local_version = OpenPypeVersion.get_installed_version_str()

    # All cases when should be used different version than build
    if (use_version and use_version != local_version) or use_staging:
        if use_version:
            # Explicit version should be used
            version_to_use = bootstrap.find_openpype_version(
                use_version, use_staging
            )
            if version_to_use is None:
                raise OpenPypeVersionNotFound(
                    "Requested version \"{}\" was not found.".format(
                        use_version
                    )
                )
        else:
            # Staging version should be used
            version_to_use = bootstrap.find_latest_openpype_version(
                use_staging
            )
            if version_to_use is None:
                if use_staging:
                    reason = "Didn't find any staging versions."
                else:
                    # This reason is backup for possible bug in code
                    reason = "Didn't find any versions."
                raise OpenPypeVersionNotFound(reason)

        # Start extraction of version if needed
        if version_to_use.path.is_file():
            version_to_use.path = bootstrap.extract_openpype(version_to_use)
        bootstrap.add_paths_from_directory(version_to_use.path)
        os.environ["OPENPYPE_VERSION"] = use_version
        version_path = version_to_use.path
        os.environ["OPENPYPE_REPOS_ROOT"] = (
            version_path / "openpype"
        ).as_posix()
        _openpype_root = version_to_use.path.as_posix()

    else:
        os.environ["OPENPYPE_VERSION"] = local_version
        version_path = Path(_openpype_root)
        os.environ["OPENPYPE_REPOS_ROOT"] = _openpype_root

    # add self to sys.path of current process
    # NOTE: this seems to be duplicate of 'add_paths_from_directory'
    sys.path.insert(0, _openpype_root)
    # add venv 'site-packages' to PYTHONPATH
    python_path = os.getenv("PYTHONPATH", "")
    split_paths = python_path.split(os.pathsep)
    # add self to python paths
    split_paths.insert(0, _openpype_root)

    # last one should be venv site-packages
    # this is slightly convoluted as we can get here from frozen code too
    # in case when we are running without any version installed.
    if not getattr(sys, 'frozen', False):
        split_paths.append(site.getsitepackages()[-1])
        # TODO move additional paths to `boot` part when OPENPYPE_ROOT will
        # point to same hierarchy from code and from frozen OpenPype
        additional_paths = [
            # add OpenPype tools
            os.path.join(_openpype_root, "openpype", "tools"),
            # add common OpenPype vendor
            # (common for multiple Python interpreter versions)
            os.path.join(
                _openpype_root,
                "openpype",
                "vendor",
                "python",
                "common"
            )
        ]
        for path in additional_paths:
            split_paths.insert(0, path)
            sys.path.insert(0, path)

    os.environ["PYTHONPATH"] = os.pathsep.join(split_paths)

    return version_path


def _boot_validate_versions(use_version, local_version):
    _print(f">>> Validating version [ {use_version} ]")
    openpype_versions = bootstrap.find_openpype(include_zips=True,
                                                staging=True)
    openpype_versions += bootstrap.find_openpype(include_zips=True,
                                                 staging=False)
    v: OpenPypeVersion
    found = [v for v in openpype_versions if str(v) == use_version]
    if not found:
        _print(f"!!! Version [ {use_version} ] not found.")
        list_versions(openpype_versions, local_version)
        sys.exit(1)

    # print result
    result = bootstrap.validate_openpype_version(
        bootstrap.get_version_path_from_list(
            use_version, openpype_versions))

    _print("{}{}".format(
        ">>> " if result[0] else "!!! ",
        bootstrap.validate_openpype_version(
            bootstrap.get_version_path_from_list(
                use_version, openpype_versions)
        )[1])
    )


def _boot_print_versions(use_staging, local_version, openpype_root):
    if not use_staging:
        _print("--- This will list only non-staging versions detected.")
        _print("    To see staging versions, use --use-staging argument.")
    else:
        _print("--- This will list only staging versions detected.")
        _print("    To see other version, omit --use-staging argument.")
    _openpype_root = OPENPYPE_ROOT
    openpype_versions = bootstrap.find_openpype(include_zips=True,
                                                staging=use_staging)
    if getattr(sys, 'frozen', False):
        local_version = bootstrap.get_version(Path(_openpype_root))
    else:
        local_version = OpenPypeVersion.get_installed_version_str()

    list_versions(openpype_versions, local_version)


def boot():
    """Bootstrap OpenPype."""

    # ------------------------------------------------------------------------
    # Set environment to OpenPype root path
    # ------------------------------------------------------------------------
    os.environ["OPENPYPE_ROOT"] = OPENPYPE_ROOT

    # ------------------------------------------------------------------------
    # Do necessary startup validations
    # ------------------------------------------------------------------------
    _startup_validations()

    # ------------------------------------------------------------------------
    # Process arguments
    # ------------------------------------------------------------------------

    use_version, use_staging, commands = _process_arguments()

    if os.getenv("OPENPYPE_VERSION"):
        if use_version:
            _print(("*** environment variable OPENPYPE_VERSION"
                    "is overridden by command line argument."))
        else:
            _print(">>> version set by environment variable")
            use_staging = "staging" in os.getenv("OPENPYPE_VERSION")
            use_version = os.getenv("OPENPYPE_VERSION")

    # ------------------------------------------------------------------------
    # Determine mongodb connection
    # ------------------------------------------------------------------------

    try:
        openpype_mongo = _determine_mongodb()
    except RuntimeError as e:
        # without mongodb url we are done for.
        _print(f"!!! {e}")
        sys.exit(1)

    os.environ["OPENPYPE_MONGO"] = openpype_mongo
    # name of Pype database
    os.environ["OPENPYPE_DATABASE_NAME"] = \
        os.environ.get("OPENPYPE_DATABASE_NAME") or "openpype"

    global_settings = get_openpype_global_settings(openpype_mongo)

    _print(">>> run disk mapping command ...")
    run_disk_mapping_commands(global_settings)

    # Logging to server enabled/disabled
    log_to_server = global_settings.get("log_to_server", True)
    if log_to_server:
        os.environ["OPENPYPE_LOG_TO_SERVER"] = "1"
        log_to_server_msg = "ON"
    else:
        os.environ.pop("OPENPYPE_LOG_TO_SERVER", None)
        log_to_server_msg = "OFF"
    _print(f">>> Logging to server is turned {log_to_server_msg}")

    # Get openpype path from database and set it to environment so openpype can
    # find its versions there and bootstrap them.
    openpype_path = get_openpype_path_from_settings(global_settings)

    if getattr(sys, 'frozen', False):
        local_version = bootstrap.get_version(Path(OPENPYPE_ROOT))
    else:
        local_version = OpenPypeVersion.get_installed_version_str()

    if "validate" in commands:
        _boot_validate_versions(use_version, local_version)
        sys.exit(1)

    if not openpype_path:
        _print("*** Cannot get OpenPype path from database.")

    if not os.getenv("OPENPYPE_PATH") and openpype_path:
        os.environ["OPENPYPE_PATH"] = openpype_path

    if "print_versions" in commands:
        _boot_print_versions(use_staging, local_version, OPENPYPE_ROOT)
        sys.exit(1)

    # ------------------------------------------------------------------------
    # Find OpenPype versions
    # ------------------------------------------------------------------------
    # WARNING: Environment OPENPYPE_REPOS_ROOT may change if frozen OpenPype
    # is executed
    if getattr(sys, 'frozen', False):
        # find versions of OpenPype to be used with frozen code
        try:
            version_path = _find_frozen_openpype(use_version, use_staging)
        except OpenPypeVersionNotFound as exc:
            message = str(exc)
            _print(message)
            if os.environ.get("OPENPYPE_HEADLESS_MODE") == "1":
                openpype_versions = bootstrap.find_openpype(
                    include_zips=True, staging=use_staging
                )
                list_versions(openpype_versions, local_version)
            else:
                igniter.show_message_dialog("Version not found", message)
            sys.exit(1)

        except RuntimeError as e:
            # no version to run
            _print(f"!!! {e}")
            sys.exit(1)
        # validate version
        _print(f">>> Validating version [ {str(version_path)} ]")
        result = bootstrap.validate_openpype_version(version_path)
        if not result[0]:
            _print(f"!!! Invalid version: {result[1]}")
            sys.exit(1)
        _print(f"--- version is valid")
    else:
        try:
            version_path = _bootstrap_from_code(use_version, use_staging)

        except OpenPypeVersionNotFound as exc:
            message = str(exc)
            _print(message)
            if os.environ.get("OPENPYPE_HEADLESS_MODE") == "1":
                openpype_versions = bootstrap.find_openpype(
                    include_zips=True, staging=use_staging
                )
                list_versions(openpype_versions, local_version)
            else:
                igniter.show_message_dialog("Version not found", message)
            sys.exit(1)

    # set this to point either to `python` from venv in case of live code
    # or to `openpype` or `openpype_console` in case of frozen code
    os.environ["OPENPYPE_EXECUTABLE"] = sys.executable

    # delete OpenPype module and it's submodules from cache so it is used from
    # specific version
    modules_to_del = [
        sys.modules.pop(module_name)
        for module_name in tuple(sys.modules)
        if module_name == "openpype" or module_name.startswith("openpype.")
    ]

    try:
        for module_name in modules_to_del:
            del sys.modules[module_name]
    except AttributeError:
        pass
    except KeyError:
        pass

    _print(">>> loading environments ...")
    # Avalon environments must be set before avalon module is imported
    _print("  - for Avalon ...")
    set_avalon_environments()
    _print("  - global OpenPype ...")
    set_openpype_global_environments()
    _print("  - for modules ...")
    set_modules_environments()

    assert version_path, "Version path not defined."

    # print info when not running scripts defined in 'silent commands'
    if all(arg not in silent_commands for arg in sys.argv):
        from openpype.lib import terminal as t
        from openpype.version import __version__

        info = get_info(use_staging)
        info.insert(0, f">>> Using OpenPype from [ {version_path} ]")

        t_width = 20
        try:
            t_width = os.get_terminal_size().columns - 2
        except (ValueError, OSError):
            # running without terminal
            pass

        _header = f"*** OpenPype [{__version__}] "
        info.insert(0, _header + "-" * (t_width - len(_header)))

        for i in info:
            t.echo(i)

    from openpype import cli
    try:
        cli.main(obj={}, prog_name="openpype")
    except Exception:  # noqa
        exc_info = sys.exc_info()
        _print("!!! OpenPype crashed:")
        traceback.print_exception(*exc_info)
        sys.exit(1)


def get_info(use_staging=None) -> list:
    """Print additional information to console."""
    from openpype.lib.mongo import get_default_components
    from openpype.lib.log import PypeLogger

    components = get_default_components()

    inf = []
    if use_staging:
        inf.append(("OpenPype variant", "staging"))
    else:
        inf.append(("OpenPype variant", "production"))
    inf.append(
        ("Running OpenPype from", os.environ.get('OPENPYPE_REPOS_ROOT'))
    )
    inf.append(("Using mongodb", components["host"]))

    if os.environ.get("FTRACK_SERVER"):
        inf.append(("Using FTrack at",
                    os.environ.get("FTRACK_SERVER")))

    if os.environ.get('DEADLINE_REST_URL'):
        inf.append(("Using Deadline webservice at",
                    os.environ.get("DEADLINE_REST_URL")))

    if os.environ.get('MUSTER_REST_URL'):
        inf.append(("Using Muster at",
                    os.environ.get("MUSTER_REST_URL")))

    # Reinitialize
    PypeLogger.initialize()

    mongo_components = get_default_components()
    if mongo_components["host"]:
        inf.append(("Logging to MongoDB", mongo_components["host"]))
        inf.append(("  - port", mongo_components["port"] or "<N/A>"))
        inf.append(("  - database", PypeLogger.log_database_name))
        inf.append(("  - collection", PypeLogger.log_collection_name))
        inf.append(("  - user", mongo_components["username"] or "<N/A>"))
        if mongo_components["auth_db"]:
            inf.append(("  - auth source", mongo_components["auth_db"]))

    maximum = max(len(i[0]) for i in inf)
    formatted = []
    for info in inf:
        padding = (maximum - len(info[0])) + 1
        formatted.append(
            "... {}:{}[ {} ]".format(info[0], " " * padding, info[1]))
    return formatted


if __name__ == "__main__":
    boot()
