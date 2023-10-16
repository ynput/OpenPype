# Filename extension is .py3 so Fusion forces the run with Python 3 interpreter
import os
import runpy

from openpype.pipeline import install_host
from openpype.hosts.fusion.api import FusionHost
from openpype.hosts.fusion.api.lib import get_fusion_module

fusion = get_fusion_module()


def main():

    # Ensure fusion install host triggered prior to the script
    install_host(FusionHost())

    # Run the script
    # Environment variable is set by run script implementation
    script_path = os.environ["OPENPYPE_FUSION_LAUNCH_SCRIPT_PATH"]
    runpy.run_path(script_path, run_name="__main__", init_globals={
        "fusion": fusion
    })

    # Close fusion afterwards
    fusion.Quit()


main()
