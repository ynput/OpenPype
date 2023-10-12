
import os
import sys
import subprocess
import collections
import logging
import asyncio
import functools
import traceback


from wsrpc_aiohttp import (
    WebSocketRoute,
    WebSocketAsync
)

from qtpy import QtCore

from openpype.lib import Logger
from openpype.tests.lib import is_in_tests
from openpype.pipeline import install_host, legacy_io
from openpype.modules import ModulesManager
from openpype.tools.utils import host_tools, get_openpype_qt_app
from openpype.tools.adobe_webserver.app import WebServerTool

from openpype.pipeline import get_current_context
from openpype.pipeline.context_tools import change_current_context
from openpype.client import get_asset_by_name

from .ws_stub import get_stub
from .lib import set_settings

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def publish():
    stub = get_stub()
    # stub.print_msg("Hello.")

    kwargs = {}
    tool_name = "publisher"

    # store current Context
    original_context = get_current_context()

    # Analyze the layers
    current_comp = stub.get_selected_items(True)
    if len(current_comp) != 1:
        stub.print_msg("Only 1 comp can be published.")
        return
    else:
        current_comp = current_comp[0]
        log.info(f"Current Comp Id: {current_comp.id}")

    # # Each layer should be a Comp named after the child  Asset
    layers = stub.get_precomps_from_comps(current_comp.id)
    for layer in layers:
        if layer.get("type") == "Precomp":
            asset_name = "_".join(layer["name"].split("_")[0:-1])
            asset = get_asset_by_name(original_context["project_name"],
                                      asset_name)
            workAreaStart = layer.get("startTime")
            workAreaDuration = layer.get("outPoint") - layer.get("inPoint")

            log.info((current_comp.id,
                     workAreaStart,
                     workAreaDuration))

            stub.set_comp_work_area(current_comp.id,
                                    workAreaStart,
                                    workAreaDuration)

            change_current_context(asset, "Compositing")

            host_tools.show_tool_by_name(tool_name, **kwargs)
    log.info("bye")
