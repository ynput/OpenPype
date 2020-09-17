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
        else:
            if use_version is not None:
                print(("!!! Specified version was not found, using "
                       "latest available"))
            # use latest
            bootstrap.add_paths_from_archive(list(pype_versions.values())[-1])
            use_version = list(pype_versions.keys())[-1]
    else:
        # run throught repos and add them to sys.path and PYTHONPATH
        pype_root = os.path.dirname(sys.executable)
        repos = os.listdir(os.path.join(pype_root, "repos"))
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
    try:
        cli.main(obj={}, prog_name="pype")
    except Exception:
        exc_info = sys.exc_info()
        print("!!! Pype crashed:")
        traceback.print_exception(*exc_info)
        sys.exit(1)


boot()
