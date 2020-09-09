# -*- coding: utf-8 -*-
"""Main entry point for Pype command."""
from pype import cli
from pype.lib import terminal as t
import sys
import traceback
from version import __version__

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
try:
    cli.main(obj={}, prog_name="pype")
except Exception:
    exc_info = sys.exc_info()
    print("!!! Pype crashed:")
    traceback.print_exception(*exc_info)
    sys.exit(1)
