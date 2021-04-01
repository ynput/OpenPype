# -*- coding: utf-8 -*-
"""Main entry point for OpenPype command.

Bootstrapping process of OpenPype is as follows:

`OPENPYPE_PATH` is checked for existence - either one from environment or
from user settings. Precedence takes the one set by environment.

On this path we try to find OpenPype in directories version string in their names.
For example: `openpype-v3.0.1-foo` is valid name, or even `foo_3.0.2` - as long
as version can be determined from its name _AND_ file `openpype/openpype/version.py`
can be found inside, it is considered OpenPype installation.

If no OpenPype repositories are found in `OPENPYPE_PATH` (user data dir)
then **Igniter** (OpenPype setup tool) will launch its GUI.

It can be used to specify `OPENPYPE_PATH` or if it is _not_ specified, current
*"live"* repositories will be used to create zip file and copy it to
appdata dir in user home and extract it there. Version will be determined by
version specified in OpenPype module.

If OpenPype repository directories are found in default install location
(user data dir) or in `OPENPYPE_PATH`, it will get list of those dirs there and
use latest one or the one specified with optional `--use-version` command
line argument. If the one specified doesn't exist then latest available
version will be used. All repositories in that dir will be added
to `sys.path` and `PYTHONPATH`.

If OpenPype is live (not frozen) then current version of OpenPype module will be
used. All directories under `repos` will be added to `sys.path` and
`PYTHONPATH`.

OpenPype depends on connection to `MongoDB`_. You can specify MongoDB connection
string via `OPENPYPE_MONGO` set in environment or it can be set in user
settings or via **Igniter** GUI.

So, bootstrapping OpenPype looks like this::

.. code-block:: bash

+-------------------------------------------------------+
| Determine MongoDB connection:                         |
| Use `OPENPYPE_MONGO`, system keyring `openPypeMongo`  |
+--------------------------|----------------------------+
                   .--- Found? --.
                 YES             NO
                  |              |
                  |       +------v--------------+
                  |       | Fire up Igniter GUI |<---------+
                  |       | and ask User        |          |
                  |       +---------------------+          |
                  |                                        |
                  |                                        |
+-----------------v------------------------------------+   |
| Get location of OpenPype:                            |   |
|   1) Test for `OPENPYPE_PATH` environment variable   |   |
|   2) Test `openPypePath` in registry setting         |   |
|   3) Test user data directory                        |   |
| ...................................................  |   |
| If running from frozen code:                         |   |
|   - Use latest one found in user data dir            |   |
| If running from live code:                           |   |
|   - Use live code and install it to user data dir    |   |
| * can be overridden with `--use-version` argument    |   |
+-------------------------|----------------------------+   |
             .-- Is OpenPype found? --.                    |
             YES                     NO                    |
              |                      |                     |
              |      +---------------v-----------------+   |
              |      | Look in `OPENPYPE_PATH`, find   |   |
              |      | latest version and install it   |   |
              |      | to user data dir.               |   |
              |      +--------------|------------------+   |
              |         .-- Is OpenPype found? --.         |
              |         YES                     NO --------+
              |          |
              |<---------+
              |
+-------------v------------+
|      Run OpenPype        |
+--------------------------+


Todo:
    Move or remove bootstrapping environments out of the code.

Attributes:
    silent_commands (list): list of commands for which we won't print OpenPype
        logo and info header.

.. _MongoDB:
   https://www.mongodb.com/

"""
import os
import re
import sys
import traceback
import subprocess
import site
from pathlib import Path

# add dependencies folder to sys.pat for frozen code
if getattr(sys, 'frozen', False):
    frozen_libs = os.path.normpath(
        os.path.join(os.path.dirname(sys.executable), "dependencies"))
    sys.path.append(frozen_libs)
    # add stuff from `<frozen>/dependencies` to PYTHONPATH.
    pythonpath = os.getenv("PYTHONPATH", "")
    paths = pythonpath.split(os.pathsep)
    paths.append(frozen_libs)
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)

import igniter  # noqa: E402
from igniter import BootstrapRepos  # noqa: E402
from igniter.tools import get_openpype_path_from_db  # noqa
from igniter.bootstrap_repos import OpenPypeVersion  # noqa: E402

bootstrap = BootstrapRepos()
silent_commands = ["run", "igniter", "standalonepublisher",
                   "extractenvironments"]


def set_openpype_global_environments() -> None:
    """Set global OpenPype's environments."""
    import acre

    from openpype.settings import get_environments

    all_env = get_environments()

    # TODO Global environments will be stored in "general" settings so loading
    #   will be modified and can be done in igniter.
    env = acre.merge(
        acre.parse(all_env["global"]),
        dict(os.environ)
    )
    os.environ.clear()
    os.environ.update(env)

    # Hardcoded default values
    os.environ["PYBLISH_GUI"] = "pyblish_pype"
    os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"  # name of Pype database
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
    print(f">>> done [{p.returncode}]")
    return p.returncode


def set_avalon_environments():
    """Set avalon specific environments.

    These are non modifiable environments for avalon workflow that must be set
    before avalon module is imported because avalon works with globals set with
    environment variables.
    """
    from openpype import PACKAGE_DIR

    # Path to OpenPype's schema
    schema_path = os.path.join(
        os.path.dirname(PACKAGE_DIR),
        "schema"
    )
    # Avalon mongo URL
    avalon_mongo_url = (
        os.environ.get("AVALON_MONGO")
        or os.environ["OPENPYPE_MONGO"]
    )
    os.environ.update({
        # Mongo url (use same as OpenPype has)
        "AVALON_MONGO": avalon_mongo_url,

        "AVALON_SCHEMA": schema_path,
        # Mongo DB name where avalon docs are stored
        "AVALON_DB": "avalon",
        # Name of config
        "AVALON_CONFIG": "openpype",
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


def _process_arguments() -> tuple:
    """Process command line arguments.

    Returns:
        tuple: Return tuple with specific version to use (if any) and flag
            to prioritize staging (if set)
    """
    # check for `--use-version=3.0.0` argument and `--use-staging`
    use_version = None
    use_staging = False
    for arg in sys.argv:
        if arg == "--use-version":
            print("!!! Please use option --use-version like:")
            print("    --use-version=3.0.0")
            sys.exit(1)

        m = re.search(r"--use-version=(?P<version>\d+\.\d+\.\d*.+?)", arg)
        if m and m.group('version'):
            use_version = m.group('version')
            sys.argv.remove(arg)
            break
    if "--use-staging" in sys.argv:
        use_staging = True
        sys.argv.remove("--use-staging")

    # handle igniter
    # this is helper to run igniter before anything else
    if "igniter" in sys.argv:
        import igniter
        return_code = igniter.open_dialog()

        # this is when we want to run OpenPype without installing anything.
        # or we are ready to run.
        if return_code not in [2, 3]:
            sys.exit(return_code)

    return use_version, use_staging


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
            openpype_mongo = bootstrap.registry.get_secure_item(
                "openPypeMongo")
        except ValueError:
            print("*** No DB connection string specified.")
            print("--- launching setup UI ...")
            import igniter
            igniter.open_dialog()

            try:
                openpype_mongo = bootstrap.registry.get_secure_item(
                    "openPypeMongo")
            except ValueError:
                raise RuntimeError("missing mongodb url")

    return openpype_mongo


def _initialize_environment(openpype_version: OpenPypeVersion) -> None:
    version_path = openpype_version.path
    os.environ["OPENPYPE_VERSION"] = openpype_version.version
    # set OPENPYPE_ROOT to point to currently used OpenPype version.
    os.environ["OPENPYPE_ROOT"] = os.path.normpath(version_path.as_posix())
    # inject version to Python environment (sys.path, ...)
    print(">>> Injecting OpenPype version to running environment  ...")
    bootstrap.add_paths_from_directory(version_path)

    # Additional sys paths related to OPENPYPE_ROOT directory
    # TODO move additional paths to `boot` part when OPENPYPE_ROOT will point
    # to same hierarchy from code and from frozen OpenPype
    additional_paths = [
        # add OpenPype tools
        os.path.join(os.environ["OPENPYPE_ROOT"], "openpype", "tools"),
        # add common OpenPype vendor
        # (common for multiple Python interpreter versions)
        os.path.join(
            os.environ["OPENPYPE_ROOT"],
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
    ``PYTHONPATH``, ``OPENPYPE_VERSION``, ``OPENPYPE_ROOT``

    Args:
        use_version (str, optional): Try to use specified version.
        use_staging (bool, optional): Prefer *staging* flavor over production.

    Returns:
        Path: Path to version to be used.

    Raises:
        RuntimeError: If no OpenPype version are found or no staging version
            (if requested).

    """
    openpype_version = None
    openpype_versions = bootstrap.find_openpype(include_zips=True,
                                                staging=use_staging)
    if not os.getenv("OPENPYPE_TRYOUT"):
        try:
            # use latest one found (last in the list is latest)
            openpype_version = openpype_versions[-1]
        except IndexError:
            # no OpenPype version found, run Igniter and ask for them.
            print('*** No OpenPype versions found.')
            print("--- launching setup UI ...")
            import igniter
            return_code = igniter.open_dialog()
            if return_code == 2:
                os.environ["OPENPYPE_TRYOUT"] = "1"
            if return_code == 3:
                # run OpenPype after installation

                print('>>> Finding OpenPype again ...')
                openpype_versions = bootstrap.find_openpype(
                    staging=use_staging)
                try:
                    openpype_version = openpype_versions[-1]
                except IndexError:
                    print(("!!! Something is wrong and we didn't "
                          "found it again."))
                    sys.exit(1)
            elif return_code != 2:
                print(f"  . finished ({return_code})")
                sys.exit(return_code)

    if not openpype_versions:
        # no openpype versions found anyway, lets use then the one
        # shipped with frozen OpenPype
        if not os.getenv("OPENPYPE_TRYOUT"):
            print("*** Still no luck finding OpenPype.")
            print(("*** We'll try to use the one coming "
                   "with OpenPype installation."))
        version_path = _bootstrap_from_code(use_version)
        openpype_version = OpenPypeVersion(
            version=BootstrapRepos.get_version(version_path),
            path=version_path)
        _initialize_environment(openpype_version)
        return version_path

    # get path of version specified in `--use-version`
    version_path = BootstrapRepos.get_version_path_from_list(
        use_version, openpype_versions)

    if not version_path:
        if use_version is not None:
            if not openpype_version:
                ...
            else:
                print(("!!! Specified version was not found, using "
                       "latest available"))
        # specified version was not found so use latest detected.
        version_path = openpype_version.path
        print(f">>> Using version [ {openpype_version} ]")
        print(f"    From {version_path}")

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
        version_path = bootstrap.install_version(
            openpype_version, force=True)

    if openpype_version.path.is_file():
        print(">>> Extracting zip file ...")
        version_path = bootstrap.extract_openpype(openpype_version)
        openpype_version.path = version_path

    _initialize_environment(openpype_version)
    return version_path


def _bootstrap_from_code(use_version):
    """Bootstrap live code (or the one coming with frozen OpenPype.

    Args:
        use_version: (str): specific version to use.

    Returns:
        Path: path to sourced version.

    """
    # run through repos and add them to `sys.path` and `PYTHONPATH`
    # set root
    if getattr(sys, 'frozen', False):
        openpype_root = os.path.normpath(
            os.path.dirname(sys.executable))
        local_version = bootstrap.get_version(Path(openpype_root))
        print(f"  - running version: {local_version}")
        assert local_version
    else:
        openpype_root = os.path.normpath(
            os.path.dirname(
                os.path.dirname(
                    os.path.realpath(igniter.__file__))))
        # get current version of OpenPype
        local_version = bootstrap.get_local_live_version()

    os.environ["OPENPYPE_VERSION"] = local_version
    if use_version and use_version != local_version:
        openpype_versions = bootstrap.find_openpype(include_zips=True)
        version_path = BootstrapRepos.get_version_path_from_list(
            use_version, openpype_versions)
        if version_path:
            # use specified
            bootstrap.add_paths_from_directory(version_path)
            os.environ["OPENPYPE_VERSION"] = use_version
    else:
        version_path = openpype_root
    os.environ["OPENPYPE_ROOT"] = openpype_root
    repos = os.listdir(os.path.join(openpype_root, "repos"))
    repos = [os.path.join(openpype_root, "repos", repo) for repo in repos]
    # add self to python paths
    repos.insert(0, openpype_root)
    for repo in repos:
        sys.path.insert(0, repo)

    # add venv 'site-packages' to PYTHONPATH
    python_path = os.getenv("PYTHONPATH", "")
    split_paths = python_path.split(os.pathsep)
    # Add repos as first in list
    split_paths = repos + split_paths
    # last one should be venv site-packages
    # this is slightly convoluted as we can get here from frozen code too
    # in case when we are running without any version installed.
    if not getattr(sys, 'frozen', False):
        split_paths.append(site.getsitepackages()[-1])
        # TODO move additional paths to `boot` part when OPENPYPE_ROOT will point
        # to same hierarchy from code and from frozen OpenPype
        additional_paths = [
            # add OpenPype tools
            os.path.join(os.environ["OPENPYPE_ROOT"], "openpype", "tools"),
            # add common OpenPype vendor
            # (common for multiple Python interpreter versions)
            os.path.join(
                os.environ["OPENPYPE_ROOT"],
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

    return Path(version_path)


def boot():
    """Bootstrap OpenPype."""

    # ------------------------------------------------------------------------
    # Play animation
    # ------------------------------------------------------------------------

    # from igniter.terminal_splash import play_animation

    # don't play for silenced commands
    # if all(item not in sys.argv for item in silent_commands):
    #     play_animation()

    # ------------------------------------------------------------------------
    # Process arguments
    # ------------------------------------------------------------------------

    use_version, use_staging = _process_arguments()

    # ------------------------------------------------------------------------
    # Determine mongodb connection
    # ------------------------------------------------------------------------

    try:
        openpype_mongo = _determine_mongodb()
    except RuntimeError as e:
        # without mongodb url we are done for.
        print(f"!!! {e}")
        sys.exit(1)

    os.environ["OPENPYPE_MONGO"] = openpype_mongo

    # ------------------------------------------------------------------------
    # Set environments - load OpenPype path from database (if set)
    # ------------------------------------------------------------------------
    # set OPENPYPE_ROOT to running location until proper version can be
    # determined.
    if getattr(sys, 'frozen', False):
        os.environ["OPENPYPE_ROOT"] = os.path.dirname(sys.executable)
    else:
        os.environ["OPENPYPE_ROOT"] = os.path.dirname(__file__)

    # Get openpype path from database and set it to environment so openpype can
    # find its versions there and bootstrap them.
    openpype_path = get_openpype_path_from_db(openpype_mongo)
    if not openpype_path:
        print("*** Cannot get OpenPype path from database.")

    if not os.getenv("OPENPYPE_PATH") and openpype_path:
        os.environ["OPENPYPE_PATH"] = openpype_path

    # ------------------------------------------------------------------------
    # Find OpenPype versions
    # ------------------------------------------------------------------------
    # WARNING: Environment OPENPYPE_ROOT may change if frozen OpenPype
    # is executed
    if getattr(sys, 'frozen', False):
        # find versions of OpenPype to be used with frozen code
        try:
            version_path = _find_frozen_openpype(use_version, use_staging)
        except RuntimeError as e:
            # no version to run
            print(f"!!! {e}")
            sys.exit(1)
    else:
        version_path = _bootstrap_from_code(use_version)

    # set this to point either to `python` from venv in case of live code
    # or to `openpype` or `openpype_console` in case of frozen code
    os.environ["OPENPYPE_EXECUTABLE"] = sys.executable

    if getattr(sys, 'frozen', False):
        os.environ["OPENPYPE_REPOS_ROOT"] = os.environ["OPENPYPE_ROOT"]
    else:
        os.environ["OPENPYPE_REPOS_ROOT"] = os.path.join(
            os.environ["OPENPYPE_ROOT"], "repos")

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

    print(">>> loading environments ...")
    # Avalon environments must be set before avalon module is imported
    print("  - for Avalon ...")
    set_avalon_environments()
    print("  - global OpenPype ...")
    set_openpype_global_environments()
    print("  - for modules ...")
    set_modules_environments()

    from openpype import cli
    from openpype.lib import terminal as t
    from openpype.version import __version__

    assert version_path, "Version path not defined."
    info = get_info()
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
        # don't show for running scripts
        if all(item not in sys.argv for item in silent_commands):
            t.echo(i)

    try:
        cli.main(obj={}, prog_name="openpype")
    except Exception:  # noqa
        exc_info = sys.exc_info()
        print("!!! OpenPype crashed:")
        traceback.print_exception(*exc_info)
        sys.exit(1)


def get_info() -> list:
    """Print additional information to console."""
    from openpype.lib.mongo import get_default_components
    from openpype.lib.log import PypeLogger

    components = get_default_components()

    inf = []
    if not getattr(sys, 'frozen', False):
        inf.append(("OpenPype variant", "staging"))
    else:
        inf.append(("OpenPype variant", "production"))
    inf.append(("Running OpenPype from", os.environ.get('OPENPYPE_ROOT')))
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

    log_components = PypeLogger.log_mongo_url_components
    if log_components["host"]:
        inf.append(("Logging to MongoDB", log_components["host"]))
        inf.append(("  - port", log_components["port"] or "<N/A>"))
        inf.append(("  - database", PypeLogger.log_database_name))
        inf.append(("  - collection", PypeLogger.log_collection_name))
        inf.append(("  - user", log_components["username"] or "<N/A>"))
        if log_components["auth_db"]:
            inf.append(("  - auth source", log_components["auth_db"]))

    maximum = max(len(i[0]) for i in inf)
    formatted = []
    for info in inf:
        padding = (maximum - len(info[0])) + 1
        formatted.append(
            "... {}:{}[ {} ]".format(info[0], " " * padding, info[1]))
    return formatted


if __name__ == "__main__":
    boot()
