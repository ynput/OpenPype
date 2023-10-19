
import os
import re
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

    main_workfile = get_last_workfile_path(original_context["project_name"],
                                           original_context["asset_name"],
                                           original_context["task_name"])

    main_asset = get_asset_by_name(original_context["project_name"],
                                   original_context["asset_name"])

    jobs_to_publish = []

    # Each layer should be a Comp named after the child  Asset
    layers = stub.get_precomps_from_comps(current_comp.id)
    for layer in layers:
        if layer.get("type") == "Precomp":

            comp_name = layer["name"]

            asset_name = "_".join(comp_name.split("_")[0:-1])
            asset = get_asset_by_name(original_context["project_name"],
                                      asset_name)

            job = save_precomp_as_workfile(comp_name, asset, "Compositing")
            jobs_to_publish.append(job)

            # Return to original context
            change_current_context(main_asset, original_context["task_name"])
            host.open_workfile(main_workfile)

    for job in jobs_to_publish:
        log.info(f"Submitting {job}")
        submit_ae_job(job)

    log.info("bye")


def save_precomp_as_workfile(comp_name, asset, task_name,
                             render_template_name="OpenEXR"):
    """Changes the context to asset's task, add the precomp to
    the render queue using the render_template_name.

    Args:
        comp_name (str): the name of the precomp to save.
        asset (Context): an asset to set the context to.
        task_name (str): the task name to set the context to.
        render_template_name (str, optional): The name of the render queue
                                              template. Defaults to "OpenEXR".

    Returns:
        dict: A dictionary holding the selected context plus
              the path to the workfile.
    """
    stub = get_stub()
    host = registered_host()

    # Switch context to Shot
    change_current_context(asset, task_name)
    current_context = get_current_context()
    log.info("Context switched to: {}".format(current_context))

    # Save as Shot version up Workfile
    workfile_path = get_last_workfile_path(current_context["project_name"],
                                           current_context["asset_name"],
                                           current_context["task_name"])
    workfile_path = version_up(workfile_path)
    host.save_workfile(workfile_path)
    log.info("Saving incremented workfile: {}".format(workfile_path))

    # Add Comp to render queue
    # Comp name is the same as the Layer name
    comp = get_comp_by_name(comp_name)

    stub.select_items([comp.id])
    stub.add_comp_to_queue(comp.id, render_template_name)

    host.save_workfile(workfile_path)
    print("Saving workfile: {}".format(workfile_path))

    render_info = stub.get_render_info(comp.id)

    filename = os.path.basename(render_info[0].file_name)
    name, ext = os.path.splitext(filename)
    ext = ext.replace(".", "")
    # root, ext = os.path.splitext(render_info[0].file_name)

    output_dir = _get_output_dir(workfile_path)
    output_path = os.path.join(output_dir, filename)

    job = {
        "context": current_context,
        "workfile_path": workfile_path,
        "output_path": output_path
    }

    return job


def submit_ae_job(job, family_name="render", variant_name="Main"):
    from openpype.modules.deadline.lib import submit

    host = registered_host()
    project_name = job["context"]["project_name"]
    asset_name = job["context"]["asset_name"]
    task_name = job["context"]["task_name"]
    subset_name = f"{family_name.lower()} {task_name.capitalize()}\
                    {variant_name.capitalize()}"

    # expected_representations = job["representations"]

    # publish_data = {}

    batch_name = f"{project_name} {asset_name} {task_name}"

    plugin_data = {
        # "AWSAssetFile0":""
        "Arguments": "",
        "Comp": subset_name,
        "MultiProcess": True,
        "Output": job["output_path"],
        "OutputFilePath": "",
        "ProjectPath": "",
        "SceneFile": job["workfile_path"],
        "StartupDirectory": "",
        "Version": "23.6"
    }

    extra_env = {
        "AVALON_APP_NAME": host.name,
        "AVALON_ASSET": asset_name,
        "AVALON_PROJECT": project_name,
        "AVALON_TASK": task_name,
        "OPENPYPE_LOG_NO_COLORS": "False",
        "OPENPYPE_MONGO": os.getenv("OPENPYPE_MONGO"),
        "OPENPYPE_RENDER_JOB": "1",
    }

    response = submit.payload_submit(
        "AfterEffects",
        plugin_data,
        batch_name,
        task_name,
        # group="",
        # comment="",
        frame_range=0,
        extra_env=extra_env,
        # response_data=None,
    )

# def get_expected_files(frameStart, frameEnd, workfile_path,
#                        file_name, asset_name, subset_name, padding_width=6):
#     """
#         Copied from: openpype/hosts/aftereffects/plugins/publish/collect_render.py
#         Returns list of rendered files that should be created by
#         Deadline. These are not published directly, they are source
#         for later 'submit_publish_job'.

#     Args:
#         render_instance (RenderInstance): to pull anatomy and parts used
#             in url

#     Returns:
#         (list) of absolute urls to rendered file
#     """
#     start = frameStart
#     end = frameEnd

#     base_dir = _get_output_dir(workfile_path)
#     base_name = os.path.basename(workfile_path)

#     regex = r"[._]v\d+"
#     matches = re.findall(regex, str(base_name), re.IGNORECASE)
#     label = matches[-1]
#     version = re.search(r"\d+", label).group()
#     version = int(version)

#     expected_files = []

#     _, ext = os.path.splitext(os.path.basename(file_name))
#     ext = ext.replace('.', '')
#     version_str = "v{:03d}".format(version)
#     if "#" not in file_name:  # single frame (mov)W
#         path = os.path.join(base_dir, "{}_{}_{}.{}".format(
#             asset_name,
#             subset_name,
#             version_str,
#             ext
#         ))
#         expected_files.append(path)
#     else:
#         for frame in range(start, end + 1):
#             path = os.path.join(base_dir, "{}_{}_{}.{}.{}".format(
#                 asset_name,
#                 subset_name,
#                 version_str,
#                 str(frame).zfill(padding_width),
#                 ext
#             ))
#             expected_files.append(path)
#     return expected_files


def _get_output_dir(workfile_path):
    """
        Copied from: openpype/hosts/aftereffects/plugins/publish/collect_render.py
        Returns dir path of rendered files, used in submit_publish_job
        for metadata.json location.
        Should be in separate folder inside of work area.

    Args:
        render_instance (RenderInstance):

    Returns:
        (str): absolute path to rendered files
    """
    # render to folder of workfile
    base_dir = os.path.dirname(workfile_path)
    file_name, _ = os.path.splitext(
        os.path.basename(workfile_path))
    base_dir = os.path.join(base_dir, 'renders', 'aftereffects', file_name)

    # for submit_publish_job
    return base_dir


# def submit(job):
#     import os
#     import getpass
#     import json

#     from openpype.lib import Logger
#     from openpype.pipeline import legacy_io, Anatomy
#     from openpype.pipeline.publish.lib import get_template_name_profiles, \
#                                               get_publish_template_name

#     from openpype.modules.deadline import constants as dl_constants
#     from openpype.modules.deadline.lib import submit
#     from openpype.modules.delivery.scripts import utils

#     from openpype.hosts.aftereffects.plugins.publish.collect_render import CollectAERender, RenderInstance

#     profiles = get_template_name_profiles(job["context"]["project_name"])

#     log.info(f"{profiles}")
#     template_name = get_publish_template_name(
#         job["context"]["project_name"],
#         "aftereffects/2023",
#         "render",
#         job["context"]["task_name"],
#         "Shot",
#         {},
#         False,
#         log
#     )
#     log.info(f"{template_name}")

#     instance = RenderInstance(
#         families=[
#             "review",
#             "render",
#         ]
#     )


#     collect = CollectAERender()
#     collect.process([instance])

#     log.info(collect.get_expected_files())

#     REVIEW_FAMILIES = {
#         "render"
#     }

#     PUBLISH_TO_SG_FAMILIES = {
#         "render"
#     }

#     def publish_version(
#         project_name,
#         asset_name,
#         task_name,
#         family_name,
#         subset_name,
#         expected_representations,
#         publish_data,
#     ):
#         # TODO: write some logic that finds the main path from the list of
#         # representations
#         source_path = list(expected_representations.values())[0]

#         instance_data = {
#             "project": project_name,
#             "family": family_name,
#             "subset": subset_name,
#             "families": publish_data.get("families", []),
#             "asset": asset_name,
#             "task": task_name,
#             "comment": publish_data.get("comment", ""),
#             "source": source_path,
#             "overrideExistingFrame": False,
#             "useSequenceForReview": True,
#             "colorspace": publish_data.get("colorspace"),
#             "version": publish_data.get("version"),
#             "outputDir": os.path.dirname(source_path),
#         }

#         representations = utils.get_representations(
#             instance_data,
#             expected_representations,
#             add_review=family_name in REVIEW_FAMILIES,
#             publish_to_sg=family_name in PUBLISH_TO_SG_FAMILIES,
#         )
#         if not representations:
#             logger.error(
#                 "No representations could be found on expected dictionary: %s",
#                 expected_representations
#             )
#             return {}

#         if family_name in REVIEW_FAMILIES:
#             # inject colorspace data if we are generating a review
#             for rep in representations:
#                 source_colorspace = publish_data.get("colorspace") or "scene_linear"
#                 logger.debug(
#                     "Setting colorspace '%s' to representation", source_colorspace
#                 )
#                 # utils.set_representation_colorspace(
#                 #     rep, project_name, colorspace=source_colorspace
#                 # )

#         instance_data["frameStartHandle"] = representations[0]["frameStart"]
#         instance_data["frameEndHandle"] = representations[0]["frameEnd"]

#         # add representation
#         instance_data["representations"] = representations
#         instances = [instance_data]

#         # Create farm job to run OP publish
#         metadata_path = utils.create_metadata_path(instance_data)
#         logger.info("Metadata path: %s", metadata_path)

#         publish_args = [
#             "--headless",
#             "publish",
#             '"{}"'.format(metadata_path),
#             "--targets",
#             "deadline",
#             "--targets",
#             "farm",
#         ]

#         # Create dictionary of data specific to OP plugin for payload submit
#         plugin_data = {
#             "Arguments": " ".join(publish_args),
#             "Version": os.getenv("OPENPYPE_VERSION"),
#             "SingleFrameOnly": "True",
#         }

#         username = getpass.getuser()

#         # Submit job to Deadline
#         extra_env = {
#             "AVALON_PROJECT": project_name,
#             "AVALON_ASSET": asset_name,
#             "AVALON_TASK": task_name,
#             "OPENPYPE_USERNAME": username,
#             "AVALON_WORKDIR": os.path.dirname(source_path),
#             "OPENPYPE_PUBLISH_JOB": "1",
#             "OPENPYPE_RENDER_JOB": "0",
#             "OPENPYPE_REMOTE_JOB": "0",
#             "OPENPYPE_LOG_NO_COLORS": "1",
#             "OPENPYPE_SG_USER": username,
#         }

#         deadline_task_name = "Publish {} - {} - {} - {} - {}".format(
#             family_name,
#             subset_name,
#             task_name,
#             asset_name,
#             project_name
#         )

#         response = submit.payload_submit(
#             plugin="OpenPype",
#             plugin_data=plugin_data,
#             batch_name=publish_data.get("jobBatchName") or deadline_task_name,
#             task_name=deadline_task_name,
#             group=dl_constants.OP_GROUP,
#             extra_env=extra_env,
#         )

#         # publish job file
#         publish_job = {
#             "asset": instance_data["asset"],
#             "frameStart": instance_data["frameStartHandle"],
#             "frameEnd": instance_data["frameEndHandle"],
#             "source": instance_data["source"],
#             "user": getpass.getuser(),
#             "version": None,  # this is workfile version
#             "comment": instance_data["comment"],
#             "job": {},
#             "session": legacy_io.Session.copy(),
#             "instances": instances,
#             "deadline_publish_job_id": response.get("_id")
#         }

#         logger.info("Writing json file: {}".format(metadata_path))
#         with open(metadata_path, "w") as f:
#             json.dump(publish_job, f, indent=4, sort_keys=True)

#         return response

#     expected_representations = {
#         "exr": "/path/to/exr.exr"
#     }

#     publish_data = {}

#     # publish_version(
#     #     job["context"]["project_name"],
#     #     job["context"]["asset_name"],
#     #     job["context"]["task_name"],
#     #     "render",
#     #     "renderCompositingMain",
#     #     expected_representations,
#     #     publish_data
#     # )
