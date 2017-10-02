import os
import json
import shutil
import getpass

from maya import cmds

from avalon import api
from avalon.vendor import requests

import pyblish.api

import colorbleed.maya.lib as lib


RENDER_ATTRIBUTES = {"vray":
                         {"node": "vraySettings",
                          "prefix": "fileNamePrefix",
                          "padding": "fileNamePadding",
                          "ext": "imageFormatStr"},
                     "arnold":
                         {"node": "defaultRenderGlobals",
                          "prefix": "imageFilePrefix",
                          "padding": "extensionPadding"}
                     }


def get_renderer_variables():
    """Retrieve the extension which has been set in the VRay settings

    Will return None if the current renderer is not VRay

    Returns:
        dict
    """

    renderer = lib.get_renderer(lib.get_current_renderlayer())
    render_attrs = RENDER_ATTRIBUTES[renderer]

    filename_padding = cmds.getAttr("{}.{}".format(render_attrs["node"],
                                                   render_attrs["padding"]))

    filename_0 = cmds.renderSettings(fullPath=True, firstImageName=True)[0]

    if renderer == "vray":
        # Maya's renderSettings function does not resolved V-Ray extension
        # Getting the extension for VRay settings node
        extension = cmds.getAttr("{}.{}".format(render_attrs["node"],
                                                render_attrs["ext"]))
        filename_prefix = "<Scene>/<Layer>/<Layer>"
    else:
        # Get the extension, getAttr defaultRenderGlobals.imageFormat
        # returns an index number.
        filename_base = os.path.basename(filename_0)
        extension = os.path.splitext(filename_base)[-1].strip(".")
        filename_prefix = cmds.getAttr("{}.{}".format(render_attrs["node"],
                                                      render_attrs["prefix"]))

    return {"ext": extension,
            "filename_prefix": filename_prefix,
            "padding": filename_padding,
            "filename_0": filename_0}


class MindbenderSubmitDeadline(pyblish.api.InstancePlugin):
    """Submit available render layers to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE

    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["colorbleed.renderlayer"]

    def process(self, instance):

        AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE",
                                          "http://localhost:8082")

        assert AVALON_DEADLINE is not None, "Requires AVALON_DEADLINE"

        context = instance.context
        workspace = context.data["workspaceDir"]
        fpath = context.data["currentFile"]
        fname = os.path.basename(fpath)
        comment = context.data.get("comment", "")
        scene = os.path.splitext(fname)[0]
        dirname = os.path.join(workspace, "renders")

        try:
            os.makedirs(dirname)
        except OSError:
            pass

        # Get the variables depending on the renderer
        render_variables = get_renderer_variables()
        # following hardcoded "<Scene>/<Layer>/<Layer>"
        output_filename_0 = self.preview_fname(scene,
                                               instance.name,
                                               dirname,
                                               render_variables["padding"],
                                               render_variables["ext"])

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(AVALON_DEADLINE)

        # Documentation for keys available at:
        # https://docs.thinkboxsoftware.com
        #    /products/deadline/8.0/1_User%20Manual/manual
        #    /manual-submission.html#job-info-file-options
        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": fname,

                # Job name, as seen in Monitor
                "Name": "%s - %s" % (fname, instance.name),

                # Arbitrary username, for visualisation in Monitor
                "UserName": getpass.getuser(),

                "Plugin": "MayaBatch",
                "Frames": "{start}-{end}x{step}".format(
                    start=int(instance.data["startFrame"]),
                    end=int(instance.data["endFrame"]),
                    step=int(instance.data["byFrameStep"]),
                ),

                "Comment": comment,

                # Optional, enable double-click to preview rendered
                # frames from Deadline Monitor
                "OutputFilename0": output_filename_0,
            },
            "PluginInfo": {
                # Input
                "SceneFile": fpath,

                # Output directory and filename
                "OutputFilePath": dirname,
                "OutputFilePrefix": render_variables["filename_prefix"],

                # Mandatory for Deadline
                "Version": cmds.about(version=True),

                # Only render layers are considered renderable in this pipeline
                "UsingRenderLayers": True,

                # Render only this layer
                "RenderLayer": instance.data["setMembers"],

                # Determine which renderer to use from the file itself
                "Renderer": "file",

                # Resolve relative references
                "ProjectPath": workspace,
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Include critical variables with submission
        environment = dict({
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have accesss to these paths, such as if slaves are
            # running Linux and the submitter is on Windows.
            "PYTHONPATH": os.getenv("PYTHONPATH", ""),

        }, **api.Session)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        # Include optional render globals
        payload["JobInfo"].update(instance.data.get("renderGlobals", {}))

        self.preflight_check(instance)

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        response = requests.post(url, json=payload)

        if response.ok:
            # Write metadata for publish
            fname = os.path.join(dirname, "{}.json".format(instance.name))
            data = {
                "submission": payload,
                "session": api.Session,
                "instance": instance.data,
                "jobs": [
                    response.json()
                ],
            }

            with open(fname, "w") as f:
                json.dump(data, f, indent=4, sort_keys=True)

        else:
            try:
                shutil.rmtree(dirname)
            except OSError:
                # This is nice-to-have, but not critical to the operation
                pass

            raise Exception(response.text)

    def preview_fname(self, scene, layer, folder, padding, ext):
        """Return outputted filename with #### for padding

        Passing the absolute path to Deadline enables Deadline Monitor
        to provide the user with a Job Output menu option.

        Deadline requires the path to be formatted with # in place of numbers.

        From
            /path/to/render.0000.png
        To
            /path/to/render.####.png

        Args:
            layer: name of the current layer to be rendered
            folder (str): folder to which will be written
            padding (int): padding length
            ext(str): file extension

        Returns:
            str

        """

        padded_basename = "{}.{}.{}".format(layer, "#" * padding, ext)
        preview_fname = os.path.join(folder, scene, layer, padded_basename)

        return preview_fname

    def preflight_check(self, instance):
        """Ensure the startFrame, endFrame and byFrameStep are integers"""

        for key in ("startFrame", "endFrame", "byFrameStep"):
            value = instance.data[key]

            if int(value) == value:
                continue

            self.log.warning(
                "%f=%d was rounded off to nearest integer"
                % (value, int(value))
            )
