
import os
import pprint
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

from openpype.modules.deadline.lib import submit


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

            job = save_precomp_as_workfile(comp_name, asset, "Compositing",
                                           render_template_name="CSE")
            jobs_to_publish.append(job)

            # Return to original context
            change_current_context(main_asset, original_context["task_name"])
            host.open_workfile(main_workfile)

    for job in jobs_to_publish:
        log.info(f"Submitting {job}")
        deadline_job = submit_ae_job(job)
        submit_publish_job(job, deadline_job)

    log.info("bye")


def save_precomp_as_workfile(comp_name, asset, task_name,
                             render_template_name="OpenEXR",
                             file_name="[compName].[####].[fileextension]"):
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
    workfile_path, workfile_ext = os.path.splitext(workfile_path)

    # Add a subversion
    workfile_path = f"{workfile_path}_batchPublish{workfile_ext}"
    host.save_workfile(workfile_path)
    log.info("Saving incremented workfile: {}".format(workfile_path))

    # Add Comp to render queue
    # Comp name is the same as the Layer name
    comp = get_comp_by_name(comp_name)

    stub.select_items([comp.id])
    stub.add_comp_to_queue(comp.id,
                           render_template_name,
                           file_name=file_name)

    host.save_workfile(workfile_path)
    print("Saving workfile: {}".format(workfile_path))

    render_info = stub.get_render_info(comp.id)

    filename = os.path.basename(render_info[0].file_name)
    name, ext = os.path.splitext(filename)
    ext = ext.replace(".", "")

    output_dir = _get_output_dir(workfile_path)
    output_path = os.path.join(output_dir, filename)
    output_path = output_path.replace("%5B", "[")
    output_path = output_path.replace("%5D", "]")

    comp_info = stub.get_comp_properties(comp.id)
    frame_start = comp_info.frameStart
    frame_end = round(comp_info.frameStart +
                      comp_info.framesDuration) - 1

    family_name = "render"
    variant_name = "Main"

    subset_name = family_name.lower()
    subset_name += task_name.capitalize()
    subset_name += variant_name.capitalize()

    job = {
        "context": current_context,
        "workfile_path": workfile_path,
        "output_path": output_path,
        "comp_name": comp_name,
        "frame_range": [frame_start, frame_end],
        "batch_name": os.path.basename(workfile_path),
        "subset_name": subset_name,
        "family_name": family_name,
        "variant_name": variant_name
    }

    return job


def submit_ae_job(job):

    project_name = job["context"]["project_name"]
    asset_name = job["context"]["asset_name"]
    task_name = job["context"]["task_name"]
    subset_name = job["subset_name"]
    batch_name = job["batch_name"]

    plugin_data = {
        # "AWSAssetFile0":""
        "Arguments": "",
        "Comp": job["comp_name"],
        "MultiProcess": True,
        "Output": job["output_path"],
        "OutputFilePath": "",
        "ProjectPath": "",
        "SceneFile": job["workfile_path"],
        "StartupDirectory": "",
        "Version": "23.6"
    }

    extra_env = {
        "AVALON_APP_NAME": os.getenv("AVALON_APP_NAME"),
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
        subset_name,
        comment="from after effects",
        frame_range=job["frame_range"],
        extra_env=extra_env,
    )

    return response


def submit_publish_job(job, dependency):
    # Publish Job
    from openpype.modules.puf_addons.gobbler import easy_publish
    from openpype.modules.delivery.scripts.utils import replace_frame_number_with_token

    project_name = job["context"]["project_name"]
    asset_name = job["context"]["asset_name"]
    task_name = job["context"]["task_name"]
    subset_name = job["subset_name"]
    subset_name = job["subset_name"]
    batch_name = job["batch_name"]
    family_name = job["family_name"]

    extension = os.path.splitext(job["output_path"])[-1][1:]
    representation_path = job["output_path"]
    representation_path = representation_path.replace("[", "")
    representation_path = representation_path.replace("]", "")

    # Replace multiples # with `<frameIn>-<frameOut>#` as fileseq expects
    # when passing representations that does not exists.
    f_in, f_out = job["frame_range"]
    token = f"{f_in}-{f_out}#"

    representation_path = representation_path.replace("####", token)

    expected_representations = {extension: representation_path}
    publish_data = {}

    easy_publish.publish_version(
        project_name,
        asset_name,
        task_name,
        family_name,
        subset_name,
        expected_representations,
        publish_data,
        batch_name,
        response_data=dependency,
        representations_exists=False
    )

    # from openpype.pipeline import (
    #     registered_host,
    #     Anatomy,
    # )
    # from openpype.pipeline.workfile import (
    #     get_workfile_template_key_from_context,
    #     get_last_workfile
    # )
    # from openpype.pipeline.template_data import get_template_data_with_names

    # from openpype.pipeline.farm.pyblish_functions import (
    #     create_metadata_path
    # )

    # project_name = job["context"]["project_name"]
    # asset_name = job["context"]["asset_name"]
    # task_name = job["context"]["task_name"]
    # host = registered_host()
    # # host_name = host.name

    # # template_key = get_workfile_template_key_from_context(
    # #     asset_name,
    # #     task_name,
    # #     host_name,
    # #     project_name=project_name
    # # )
    # anatomy = Anatomy(project_name)

    # log.info("anatomy")
    # log.info(pprint.pformat(anatomy.templates))

    # extra_env = {
    #     "AVALON_APP_NAME": os.getenv("AVALON_APP_NAME"),
    #     "AVALON_ASSET": asset_name,
    #     "AVALON_PROJECT": project_name,
    #     "AVALON_TASK": task_name,
    #     "OPENPYPE_LOG_NO_COLORS": "False",
    #     "OPENPYPE_MONGO": os.getenv("OPENPYPE_MONGO"),
    #     "OPENPYPE_PUBLISH_JOB":1,
    #     "OPENPYPE_REMOTE_PUBLISH":0,
    #     "KITSU_LOGIN": os.getenv("KITSU_LOGIN"),
    #     "KITSU_PWD": os.getenv("KITSU_PWD"),
    #     "OPENPYPE_USERNAME": os.getenv("KITSU_LOGIN"),
    # }


    # # Transfer the environment from the original job to this dependent
    # # job so they use the same environment
    # metadata_path, rootless_metadata_path = \
    #     create_metadata_path(instance, anatomy)


    # args = []
    # args.append("--headless")
    # args.append("publish")
    # args.append(f"{work_folder}/renders/{host.name}/cse_CSE101_01_014_Compositing_v003/renderCompositingMain_metadata.json")
    # args.append("--targets")
    # args.append("deadline")
    # args.append("--targets")
    # args.append("farm")

    # plugin_data = {
    #     "Arguments": " ".join(args),
    #     "SingleFrameOnly": True,
    #     "Version": "3.0"
    # }

    # workfile_basename = os.path.basename(job["workfile_path"])
    # batch_name = f"{workfile_basename}"
    # job_name = "Publish - renderCompositingMain"

    # response = submit.payload_submit(
    #     "OpenPype",
    #     plugin_data,
    #     batch_name,
    #     job_name,
    #     comment="from after effects",
    #     frame_range=0,
    #     extra_env=extra_env,
    #     response_data=dependency
    # )

    # """
    # # Job Info
    # BatchName=cse_CSE101_01_014_Compositing_v003.aep
    # Denylist=
    # EnvironmentKeyValue0=AVALON_PROJECT=cse
    # EnvironmentKeyValue1=AVALON_ASSET=CSE101_01_014
    # EnvironmentKeyValue10=KITSU_LOGIN=lucas.avfx@gmail.com
    # EnvironmentKeyValue11=KITSU_PWD=lucasavfx321
    # EnvironmentKeyValue12=OPENPYPE_VERSION=3.16.704
    # EnvironmentKeyValue13=OPENPYPE_MONGO=mongodb://root:example@10.68.150.36:27017
    # EnvironmentKeyValue2=AVALON_TASK=Compositing
    # EnvironmentKeyValue3=OPENPYPE_USERNAME=Titan
    # EnvironmentKeyValue4=OPENPYPE_LOG_NO_COLORS=1
    # EnvironmentKeyValue5=IS_TEST=0
    # EnvironmentKeyValue6=OPENPYPE_PUBLISH_JOB=1
    # EnvironmentKeyValue7=OPENPYPE_RENDER_JOB=0
    # EnvironmentKeyValue8=OPENPYPE_REMOTE_PUBLISH=0
    # EnvironmentKeyValue9=AVALON_APP_NAME=aftereffects/2023
    # EventOptIns=
    # Frames=0
    # JobDependency0=653c105c0147e761839c642b
    # MachineName=d36f64297157
    # Name=Publish - renderCompositingMain
    # OutputDirectory0=Y:/WORKS/_openpype/cse/Shots/CSE101/CSE101_SEC01/CSE101_01_014/publish/render/renderCompositingMain/v003
    # OverrideTaskExtraInfoNames=False
    # Plugin=OpenPype
    # Region=
    # ScheduledStartDateTime=27/10/2023 16:32
    # UserName=titan

    # # Plugin Info
    # Arguments=--headless publish "{root[work]}/cse/Shots/CSE101/CSE101_SEC01/CSE101_01_014/work/Compositing/renders/aftereffects/cse_CSE101_01_014_Compositing_v003/renderCompositingMain_metadata.json" --targets deadline --targets farm
    # SingleFrameOnly=True
    # Version=3.0
    # """

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
