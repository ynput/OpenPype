import getpass
import json
import os
from copy import deepcopy

import pyblish.api

from avalon import api
from avalon.vendor import requests

from maya import cmds


class VraySubmitDeadline(pyblish.api.InstancePlugin):
    """Export the scene to `.vrscene` files per frame per render layer

    vrscene files will be written out based on the following template:
        <project>/vrayscene/<Scene>/<Scene>_<Layer>/<Layer>

    A dependency job will be added for each layer to render the framer
    through VRay Standalone

    """
    label = "Submit to Deadline ( vrscene )"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["vrayscene_foo"]
    if not os.environ.get("DEADLINE_REST_URL"):
        optional = False
        active = False
    else:
        optional = True

    def process(self, instance):

        DEADLINE_REST_URL = api.Session.get("DEADLINE_REST_URL",
                                            "http://localhost:8082")
        assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        context = instance.context

        deadline_url = "{}/api/jobs".format(DEADLINE_REST_URL)
        deadline_user = context.data.get("deadlineUser", getpass.getuser())

        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        task_name = "{} - {}".format(filename, instance.name)

        batch_name = "{} - (vrscene)".format(filename)

        # Get the output template for vrscenes
        vrscene_output = instance.data["vrsceneOutput"]

        # This is also the input file for the render job
        first_file = self.format_output_filename(instance,
                                                 filename,
                                                 vrscene_output)

        start_frame = int(instance.data["frameStart"])
        end_frame = int(instance.data["frameEnd"])

        # Primary job
        self.log.info("Submitting export job ..")

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": batch_name,

                # Job name, as seen in Monitor
                "Name": "Export {} [{}-{}]".format(task_name,
                                                   start_frame,
                                                   end_frame),

                # Arbitrary username, for visualisation in Monitor
                "UserName": deadline_user,

                "Plugin": "MayaBatch",
                "Frames": "{}-{}".format(start_frame, end_frame),
                "FramesPerTask": instance.data.get("framesPerTask", 1),

                "Comment": context.data.get("comment", ""),

                "OutputFilename0": os.path.dirname(first_file),
            },
            "PluginInfo": {

                # Renderer
                "Renderer": "vray",

                # Mandatory for Deadline
                "Version": cmds.about(version=True),

                # Input
                "SceneFile": filepath,

                "SkipExistingFrames": True,

                "UsingRenderLayers": True,

                "UseLegacyRenderLayers": True
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        environment = dict(AVALON_TOOLS="global;python36;maya2018")
        environment.update(api.Session.copy())

        jobinfo_environment = self.build_jobinfo_environment(environment)

        payload["JobInfo"].update(jobinfo_environment)

        self.log.info("Job Data:\n{}".format(json.dumps(payload)))

        response = self._requests_post(url=deadline_url, json=payload)
        if not response.ok:
            raise RuntimeError(response.text)

        # Secondary job
        # Store job to create dependency chain
        dependency = response.json()

        if instance.data["suspendRenderJob"]:
            self.log.info("Skipping render job and publish job")
            return

        self.log.info("Submitting render job ..")

        start_frame = int(instance.data["frameStart"])
        end_frame = int(instance.data["frameEnd"])
        ext = instance.data.get("ext") or "exr"

        # Create output directory for renders
        render_ouput = self.format_output_filename(instance,
                                                   filename,
                                                   instance.data["outputDir"],
                                                   dir=True)

        self.log.info("Render output: %s" % render_ouput)

        # Update output dir
        instance.data["outputDir"] = render_ouput

        # Format output file name
        sequence_filename = ".".join([instance.name, ext])
        output_filename = os.path.join(render_ouput, sequence_filename)

        # Ensure folder exists:
        if not os.path.exists(render_ouput):
            os.makedirs(render_ouput)

        payload_b = {
            "JobInfo": {

                "JobDependency0": dependency["_id"],
                "BatchName": batch_name,
                "Name": "Render {} [{}-{}]".format(task_name,
                                                   start_frame,
                                                   end_frame),
                "UserName": deadline_user,

                "Frames": "{}-{}".format(start_frame, end_frame),

                "Plugin": "Vray",
                "OverrideTaskExtraInfoNames": False,

                "OutputFilename0": render_ouput,
            },
            "PluginInfo": {

                "InputFilename": first_file,
                "OutputFilename": output_filename,
                "SeparateFilesPerFrame": True,
                "VRayEngine": "V-Ray",

                "Width": instance.data["resolution"][0],
                "Height": instance.data["resolution"][1],

            },
            "AuxFiles": [],
        }

        # Add vray renderslave to environment
        tools = environment["AVALON_TOOLS"] + ";vrayrenderslave"
        environment_b = deepcopy(environment)
        environment_b["AVALON_TOOLS"] = tools

        jobinfo_environment_b = self.build_jobinfo_environment(environment_b)
        payload_b["JobInfo"].update(jobinfo_environment_b)

        self.log.info(json.dumps(payload_b))

        # Post job to deadline
        response_b = self._requests_post(url=deadline_url, json=payload_b)
        if not response_b.ok:
            raise RuntimeError(response_b.text)

        # Add job for publish job
        if not instance.data.get("suspendPublishJob", False):
            instance.data["deadlineSubmissionJob"] = response_b.json()

    def build_command(self, instance):
        """Create command for Render.exe to export vray scene

        Args:
            instance

        Returns:
            str

        """

        cmd = ('-r vray -proj {project} -cam {cam} -noRender -s {startFrame} '
               '-e {endFrame} -rl {layer} -exportFramesSeparate')

        # Get the camera
        cammera = instance.data["cameras"][0]

        return cmd.format(project=instance.context.data["workspaceDir"],
                          cam=cammera,
                          startFrame=instance.data["frameStart"],
                          endFrame=instance.data["frameEnd"],
                          layer=instance.name)

    def build_jobinfo_environment(self, env):
        """Format environment keys and values to match Deadline rquirements

        Args:
            env(dict): environment dictionary

        Returns:
            dict

        """
        return {"EnvironmentKeyValue%d" % index: "%s=%s" % (k, env[k])
                for index, k in enumerate(env)}

    def format_output_filename(self, instance, filename, template, dir=False):
        """Format the expected output file of the Export job.

        Example:
            <Scene>/<Scene>_<Layer>/<Layer>
            "shot010_v006/shot010_v006_CHARS/CHARS"

        Args:
            instance:
            filename(str):
            dir(bool):

        Returns:
            str

        """

        def smart_replace(string, key_values):
            new_string = string
            for key, value in key_values.items():
                new_string = new_string.replace(key, value)
            return new_string

        # Ensure filename has no extension
        file_name, _ = os.path.splitext(filename)

        # Reformat without tokens
        output_path = smart_replace(template,
                                    {"<Scene>": file_name,
                                     "<Layer>": instance.name})

        if dir:
            return output_path.replace("\\", "/")

        start_frame = int(instance.data["frameStart"])
        filename_zero = "{}_{:04d}.vrscene".format(output_path, start_frame)

        result = filename_zero.replace("\\", "/")

        return result

    def _requests_post(self, *args, **kwargs):
        """ Wrapper for requests, disabling SSL certificate validation if
            DONT_VERIFY_SSL environment variable is found. This is useful when
            Deadline or Muster server are running with self-signed certificates
            and their certificate is not added to trusted certificates on
            client machines.

            WARNING: disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.
        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        return requests.post(*args, **kwargs)
