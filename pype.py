# -*- coding: utf-8 -*-
"""Main entry point for Pype command.

Bootstrapping process of Pype is as follows:

If no Pype repositories are found in default install location (user data dir)
then Igniter (Pype setup tool) will launch its GUI.

If pype repositories zip file is found in default install location
(user data dir), it will get list of those zips there and use latest one
or the one specified with `--use-version` command line argument. If the
one specified doesn't exist then latest available version will be used. All
repositories in that zip will be added to `sys.path` and `PYTHONPATH`.

If Pype is live (ie not freezed) then current version of Pype module will be
used. All directories under `repos` will be added to `sys.path` and
`PYTHONPATH`.

"""
import sys
import os
import re
import traceback
import platform


# find Pype installation.
from igniter.bootstrap_repos import BootstrapRepos

bootstrap = BootstrapRepos()
pype_versions = bootstrap.find_pype()
# if nothing found, run installer - only when running freezed
if getattr(sys, 'frozen', False):
    if not pype_versions:
        import igniter
        igniter.run()


def boot():
    """Bootstrap Pype."""
    # test for `--use-version=3.0.0` argument.
    use_version = None

    for arg in sys.argv:
        m = re.search(r"--use-version=(?P<version>\d+\.\d+\.\d+)", arg)
        if m and m.group('version'):
            use_version = m.group('version')
            break

    if getattr(sys, 'frozen', False):
        if use_version in pype_versions.keys():
            # use specified
            bootstrap.add_paths_from_archive(pype_versions[use_version])
            os.environ["PYPE_ROOT"] = pype_versions[use_version]
        else:
            if use_version is not None:
                print(("!!! Specified version was not found, using "
                       "latest available"))
            # use latest
            bootstrap.add_paths_from_archive(list(pype_versions.values())[-1])
            os.environ["PYPE_ROOT"] = list(pype_versions.values())[-1]
            use_version = list(pype_versions.keys())[-1]
    else:
        # run throught repos and add them to sys.path and PYTHONPATH
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
    t.echo(f"*** Pype [{__version__}] --------------------------------------")
    t.echo(">>> Using Pype from [ {} ]".format(os.path.dirname(cli.__file__)))
    t.echo(">>> Loading environments ...")
    load_environments()
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
    if os.getenv('PYPE_DEV'):
        infos.append(("Pype variant", "staging"))
    else:
        infos.append(("Pype variant", "production"))
    infos.append(("Running pype from", os.environ.get('PYPE_SETUP_PATH')))
    infos.append(("Using config at", os.environ.get('PYPE_CONFIG')))
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


def load_environments() -> None:
    import acre
    os.environ['PLATFORM'] = platform.system().lower()
    # FIXME (antirotor): Acre cannot read stuff from zip files.
    os.environ["TOOL_ENV"] = os.path.join(
        os.environ["PYPE_ROOT"],
        "pype-config",
        "environments"
    )
    tools_env = acre.get_tools(
        ["global", "avalon", "ftrack", "deadline", "clockify"])
    pype_paths_env = dict()
    for key, value in dict(os.environ).items():
        if key.startswith('PYPE_'):
            pype_paths_env[key] = value

    env = tools_env
    env.update(pype_paths_env)
    env = acre.compute(env, cleanup=True)
    env = acre.merge(env, os.environ)
    os.environ = env


boot()
