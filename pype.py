# -*- coding: utf-8 -*-
"""Main entry point for Pype command."""
import sys
import os
import traceback

from appdirs import user_data_dir

from pype import cli
from pype.lib import terminal as t
from version import __version__


vendor = "pypeclub"
app = "pype"
pype_dir = user_data_dir(app, vendor)
repo_zip = os.path.join(pype_dir, f"pype-repositories-v{__version__}.zip")
if getattr(sys, 'frozen', False):
    datadir = os.path.dirname(sys.executable)
else:
    datadir = os.path.dirname(__file__)

art = r"""
    ____________
   /\      __   \
   \ \     \/_\  \
    \ \     _____/ ______
     \ \    \___/ /\     \
      \ \____\    \ \_____\
       \/____/     \/_____/  PYPE Club .

"""

print(art)
t.echo(f"*** Pype [{__version__}] --------------------")
t.echo(">>> Validating installation ...")

t.echo(sys.executable)
try:
    cli.main(obj={}, prog_name="pype")
except Exception:
    exc_info = sys.exc_info()
    print("!!! Pype crashed:")
    traceback.print_exception(*exc_info)
    sys.exit(1)
