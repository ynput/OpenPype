# -*- coding: utf-8 -*-
"""Main entry point for Pype command.

Bootstrapping process of Pype is as follows:

`PYPE_PATH` is checked for existence - either one from environment or
from user settings. Precedence takes the one set by environment.

On this path we try to find zip files with `pype-repositories-v3.x.x.zip`
format.

If no Pype repositories are found in `PYPE_PATH (user data dir)
then **Igniter** (Pype setup tool) will launch its GUI.

It can be used to specify `PYPE_PATH` or if it is _not_ specified, current
*"live"* repositories will be used to create such zip file and copy it to
appdata dir in user home. Version will be determined by version specified
in Pype module.

If Pype repositories zip file is found in default install location
(user data dir) or in `PYPE_PATH`, it will get list of those zips there and
use latest one or the one specified with optional `--use-version` command
line argument. If the one specified doesn't exist then latest available
version will be used. All repositories in that zip will be added
to `sys.path` and `PYTHONPATH`.

If Pype is live (not frozen) then current version of Pype module will be
used. All directories under `repos` will be added to `sys.path` and
`PYTHONPATH`.

Pype depends on connection to `MongoDB`_. You can specify MongoDB connection
string via `AVALON_MONGO` set in environment or it can be set in user
settings or via **Igniter** GUI.

.. _MongoDB:
   https://www.mongodb.com/

"""
import sys
import os
import re
import traceback
from igniter.tools import load_environments

try:
    import acre
except ImportError:
    sys.path.append("repos/acre")
    import acre
from igniter import BootstrapRepos


def set_environments() -> None:
    env = load_environments()
    env = acre.merge(env, dict(os.environ))
    os.environ.clear()
    os.environ.update(env)


def boot():
    """Bootstrap Pype."""
    art = r"""
            ____________
           /\      ___  \
           \ \     \/_\  \
            \ \     _____/ ______   ___ ___ ___
             \ \    \___/ /\     \  \  \\  \\  \
              \ \____\    \ \_____\  \__\\__\\__\
               \/____/     \/_____/  . PYPE Club .

        """

    print(art)
    print(">>> loading environments ...")
    set_environments()
    # find pype versions
    bootstrap = BootstrapRepos()
    pype_versions = bootstrap.find_pype()

    # check for `--use-version=3.0.0` argument.
    use_version = None

    for arg in sys.argv:
        m = re.search(r"--use-version=(?P<version>\d+\.\d+\.\d+)", arg)
        if m and m.group('version'):
            use_version = m.group('version')
            break

    if not os.getenv("AVALON_MONGO"):
        try:
            avalon_mongo = bootstrap.registry.get_secure_item("avalonMongo")
        except ValueError:
            print("*** No DB connection string specified.")
            import igniter
            igniter.run()
            set_environments()
        else:
            os.environ["AVALON_MONGO"] = avalon_mongo

    if getattr(sys, 'frozen', False):
        if not pype_versions:
            import igniter
            igniter.run()

        if use_version in pype_versions.keys():
            # use specified
            bootstrap.add_paths_from_archive(pype_versions[use_version])
            use_version = pype_versions[use_version]
        else:
            if use_version is not None:
                print(("!!! Specified version was not found, using "
                       "latest available"))
            # use latest
            bootstrap.add_paths_from_archive(list(pype_versions.values())[-1])
            use_version = list(pype_versions.keys())[-1]

        os.environ["PYPE_ROOT"] = pype_versions[use_version].as_posix()
    else:
        # run through repos and add them to sys.path and PYTHONPATH
        pype_root = os.path.dirname(os.path.realpath(__file__))
        os.environ["PYPE_ROOT"] = pype_root
        repos = os.listdir(os.path.join(pype_root, "repos"))
        repos = [os.path.join(pype_root, "repos", repo) for repo in repos]
        for repo in repos:
            sys.path.append(repo)

        pythonpath = os.getenv("PYTHONPATH", "")
        paths = pythonpath.split(os.pathsep)
        paths += repos
        os.environ["PYTHONPATH"] = os.pathsep.join(paths)

    # delete Pype module from cache so it is used from specific version
    try:
        del sys.modules["pype"]
        del sys.modules["pype.version"]
    except AttributeError:
        pass

    from pype import cli
    from pype.lib import terminal as t
    from pype.version import __version__

    t.echo(f"*** Pype [{__version__}] --------------------------------------")
    t.echo(">>> Using Pype from [ {} ]".format(os.path.dirname(cli.__file__)))
    print_info()

    try:
        cli.main(obj={}, prog_name="pype")
    except Exception:
        exc_info = sys.exc_info()
        print("!!! Pype crashed:")
        traceback.print_exception(*exc_info)
        sys.exit(1)


def print_info() -> None:
    """Print additional information to console."""
    from pype.lib import terminal as t
    from pype.lib.mongo import get_default_components
    from pype.lib.log import LOG_DATABASE_NAME, LOG_COLLECTION_NAME

    components = get_default_components()

    infos = []
    if not getattr(sys, 'frozen', False):
        infos.append(("Pype variant", "staging"))
    else:
        infos.append(("Pype variant", "production"))
    infos.append(("Running pype from", os.environ.get('PYPE_ROOT')))
    infos.append(("Using mongodb", components["host"]))

    if os.environ.get("FTRACK_SERVER"):
        infos.append(("Using FTrack at",
                      os.environ.get("FTRACK_SERVER")))

    if os.environ.get('DEADLINE_REST_URL'):
        infos.append(("Using Deadline webservice at",
                      os.environ.get("DEADLINE_REST_URL")))

    if os.environ.get('MUSTER_REST_URL'):
        infos.append(("Using Muster at",
                      os.environ.get("MUSTER_REST_URL")))

    if components["host"]:
        infos.append(("Logging to MongoDB", components["host"]))
        infos.append(("  - port", components["port"] or "<N/A>"))
        infos.append(("  - database", LOG_DATABASE_NAME))
        infos.append(("  - collection", LOG_COLLECTION_NAME))
        infos.append(("  - user", components["username"] or "<N/A>"))
        if components["auth_db"]:
            infos.append(("  - auth source", components["auth_db"]))

    maximum = max([len(i[0]) for i in infos])
    for info in infos:
        padding = (maximum - len(info[0])) + 1
        t.echo("... {}:{}[ {} ]".format(info[0], " " * padding, info[1]))
    print('\n')


boot()
