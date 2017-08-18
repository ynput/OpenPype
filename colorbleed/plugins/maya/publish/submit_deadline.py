import os
import re
import json
import shutil
import getpass

from maya import cmds

from avalon import api
from avalon.vendor import requests

import pyblish.api


def get_padding_length(filename):
    """

    >>> get_padding_length("sequence.v004.0001.exr", default=None)
    4
    >>> get_padding_length("sequence.-001.exr", default=None)
    4
    >>> get_padding_length("sequence.v005.exr", default=None)
    None

    Retrieve the padding length by retrieving the frame number from a file.

    Args:
        filename (str): the explicit filename, e.g.: sequence.0001.exr

    Returns:
        int
    """

    padding_match = re.search(r"\.(-?\d+)", filename)
    if padding_match:
        length = len(padding_match.group())
    else:
        raise AttributeError("Could not find padding length in "
                             "'{}'".format(filename))

    return length


def get_renderer_variables():
    """Retrieve the extension which has been set in the VRay settings

    Will return None if the current renderer is not VRay

    Returns:
        dict
    """

    ext = ""
    filename_prefix = ""
    # padding = 4

    renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
    if renderer == "vray":

        # padding = cmds.getAttr("vraySettings.fileNamePadding")

        # check for vray settings node
        settings_node = cmds.ls("vraySettings", type="VRaySettingsNode")
        if not settings_node:
            raise AttributeError("Could not find a VRay Settings Node, "
                                 "to ensure the node exists open the "
                                 "Render Settings window")

        # get the extension
        image_format = cmds.getAttr("vraySettings.imageFormatStr")
        if image_format:
            ext = "{}".format(image_format.split(" ")[0])

        prefix = cmds.getAttr("vraySettings.fileNamePrefix")
        if prefix:
            filename_prefix = prefix

    # insert other renderer logic here

    # fall back to default
    if renderer.lower().startswith("maya"):
        # get the extension, getAttr defaultRenderGlobals.imageFormat
        # returns index number
        first_filename = cmds.renderSettings(fullPath=True,
                                             firstImageName=True)[0]
        ext = os.path.splitext(os.path.basename(first_filename))[-1].strip(".")

        # get padding and filename prefix
        # padding = cmds.getAttr("defaultRenderGlobals.extensionPadding")
        prefix = cmds.getAttr("defaultRenderGlobals.fileNamePrefix")
        if prefix:
            filename_prefix = prefix

    return {"ext": ext, "filename_prefix": filename_prefix}


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

        deadline = api.Session.get("AVALON_DEADLINE", "http://localhost:8082")
        assert deadline is not None, "Requires AVALON_DEADLINE"

        context = instance.context
        workspace = context.data["workspaceDir"]
        fpath = context.data["currentFile"]
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)
        comment = context.data.get("comment", "")
        dirname = os.path.join(workspace, "renders", name)

        try:
            os.makedirs(dirname)
        except OSError:
            pass

        # get the variables depending on the renderer
        render_variables = get_renderer_variables()
        output_file_prefix = render_variables["filename_prefix"]
        output_filename_0 = self.preview_fname(instance,
                                               dirname,
                                               render_variables["ext"])

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(deadline)

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
                "OutputFilePrefix": output_file_prefix,

                # Mandatory for Deadline
                "Version": cmds.about(version=True),

                # Only render layers are considered renderable in this pipeline
                "UsingRenderLayers": True,

                # Render only this layer
                "RenderLayer": instance.name,

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

    def preview_fname(self, instance, dirname, extension):
        """Return outputted filename with #### for padding

        Passing the absolute path to Deadline enables Deadline Monitor
        to provide the user with a Job Output menu option.

        Deadline requires the path to be formatted with # in place of numbers.

        From
            /path/to/render.0000.png
        To
            /path/to/render.####.png

        """

        # We'll need to take tokens into account
        fname = cmds.renderSettings(firstImageName=True,
                                    fullPath=True,
                                    layer=instance.name)[0]

        try:
            # Assume `c:/some/path/filename.0001.exr`
            # TODO(marcus): Bulletproof this, the user may have
            # chosen a different format for the outputted filename.
            basename = os.path.basename(fname)
            name, padding, ext = basename.rsplit(".", 2)

            padding_format = "#" * len(padding)
            fname = ".".join([name, padding_format, extension])
            self.log.info("Assuming renders end up @ %s" % fname)
            file_name = os.path.join(dirname, instance.name, fname)
        except ValueError:
            file_name = ""
            self.log.info("Couldn't figure out where renders go")

        return file_name

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
