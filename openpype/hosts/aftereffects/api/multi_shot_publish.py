
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

from openpype.lib import Logger, version_up
from openpype.tests.lib import is_in_tests
from openpype.pipeline import install_host, legacy_io, registered_host
from openpype.modules import ModulesManager
from openpype.tools.utils import host_tools, get_openpype_qt_app
from openpype.tools.adobe_webserver.app import WebServerTool

from openpype.pipeline import get_current_context
from openpype.pipeline.context_tools import change_current_context
from openpype.client import get_asset_by_name

from .ws_stub import get_stub
from .lib import set_settings

from .workfile_template_builder import get_last_workfile_path, get_comp_by_name
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def publish():
    stub = get_stub()
    host = registered_host()
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
            # workAreaStart = layer.get("startTime")
            # workAreaDuration = layer.get("outPoint") - layer.get("inPoint")

            # log.info((current_comp.id,
            #          workAreaStart,
            #          workAreaDuration))

            # stub.set_comp_work_area(current_comp.id,
            #                         workAreaStart,
            #                         workAreaDuration)

            change_current_context(asset, "Compositing")
            current_context = get_current_context()
            log.info("Context switched to: {}".format(current_context))

            child_asset_workfile_path = get_last_workfile_path(current_context["project_name"],
                                                               current_context["asset_name"],
                                                               current_context["task_name"])
            child_asset_workfile_path = version_up(child_asset_workfile_path)
            host.save_workfile(child_asset_workfile_path)
            log.info("Saving incremented workfile: {}".format(child_asset_workfile_path))

            # Comp name is the same as the Layer name
            comp_name = layer["name"]
            comp = get_comp_by_name(comp_name)

            stub.select_items([comp.id])
            stub.add_comp_to_queue(comp.id, "OpenEXR")

            host.save_workfile(child_asset_workfile_path)
            print("Saving workfile: {}".format(child_asset_workfile_path))

            # Return to original context
            asset = get_asset_by_name(original_context["project_name"],
                                    original_context["asset_name"])
            change_current_context(asset, original_context["task_name"])
            main_workfile = get_last_workfile_path(original_context["project_name"],
                                                original_context["asset_name"],
                                                original_context["task_name"])
            host.open_workfile(main_workfile)

    # Return to original context
    asset = get_asset_by_name(original_context["project_name"],
                              original_context["asset_name"])
    change_current_context(asset, original_context["task_name"])
    main_workfile = get_last_workfile_path(original_context["project_name"],
                                           original_context["asset_name"],
                                           original_context["task_name"])
    host.open_workfile(main_workfile)
    log.info("Context switched to: {}".format(original_context))
    log.info("Workfile: {}".format(main_workfile))

    log.info("bye")
