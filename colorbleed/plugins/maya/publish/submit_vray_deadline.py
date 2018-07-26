import getpass
import json
import os
from copy import deepcopy

import pyblish.api

from avalon import api
from avalon.vendor import requests

from maya import cmds


class VraySubmitDeadline(pyblish.api.InstancePlugin):
    """"""
    label = "Submit to Deadline ( vrscene )"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["colorbleed.vrayscene"]

    def process(self, instance):

        AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE",
                                          "http://localhost:8082")
        assert AVALON_DEADLINE, "Requires AVALON_DEADLINE"

        context = instance.context

        deadline_url = context.data["deadlineUrl"]
        deadline_user = context.data.get("deadlineUser", getpass.getuser())

        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        task_name = "{} - {}".format(filename, instance.name)

        batch_name = "VRay Scene Export - {}".format(filename)

        output_filepath = context.data["outputFilePath"].replace("\\", "/")

        # This is also the input file for the render job
        first_file = self.format_output_filename_zero(instance, filename)

        # Primary job
        self.log.info("Submitting export job ..")

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": batch_name,

                # Job name, as seen in Monitor
                "Name": task_name,

                # Arbitrary username, for visualisation in Monitor
                "UserName": deadline_user,

                "Plugin": "MayaCmd",
                "Frames": "1",

                "Comment": context.data.get("comment", ""),
            },
            "PluginInfo": {

                # Mandatory for Deadline
                "Version": cmds.about(version=True),

                # Input
                "SceneFile": filepath,

                # Output directory and filename
                "OutputFilePath": output_filepath,

                "CommandLineOptions": self.build_command(instance),

                "UseOnlyCommandLineOptions": True,

                "SkipExistingFrames": True,
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        environment = dict(AVALON_TOOLS="global;python36;maya2018")

        jobinfo_environment = self.build_jobinfo_environment(environment)

        payload["JobInfo"].update(jobinfo_environment)

        self.log.info("Job Data:\n{}".format(json.dumps(payload)))

        response = requests.post(url=deadline_url, json=payload)
        if not response.ok:
            raise RuntimeError(response.text)

        # Secondary job
        # Store job to create dependency chain
        dependency = response.json()

        self.log.info("Submitting render job ..")

        start_frame = int(instance.data["startFrame"])
        end_frame = int(instance.data["endFrame"])

        payload_b = {
            "JobInfo": {

                "JobDependency0": dependency["_id"],
                "BatchName": batch_name,
                "Name": "Render {}".format(task_name),
                "UserName": deadline_user,

                "Frames": "{}-{}".format(start_frame, end_frame),

                "Plugin": "Vray",
                "OverrideTaskExtraInfoNames": False,
                "Whitelist": "cb7"
            },
            "PluginInfo": {

                "InputFilename": first_file,
                "Threads": 0,
                "OutputFilename": "",
                "SeparateFilesPerFrame": True,
                "VRayEngine": "V-Ray",

                "Width": instance.data["resolution"][0],
                "Height": instance.data["resolution"][1],

            },
            "AuxFiles": [],
        }

        tools = environment["AVALON_TOOLS"] + ";vrayrenderslave"
        environment_b = deepcopy(environment)
        environment_b["AVALON_TOOLS"] = tools

        jobinfo_environment_b = self.build_jobinfo_environment(environment_b)
        payload_b["JobInfo"].update(jobinfo_environment_b)

        self.log.info(json.dumps(payload_b))

        response_b = requests.post(url=deadline_url, json=payload_b)
        if not response_b.ok:
            raise RuntimeError(response_b.text)

        print(response_b.text)

    def build_command(self, instance):
        """Create command for Render.exe to export vray scene

        Returns:
            str

        """

        cmd = ('-r vray -proj {project} -cam {cam} -noRender -s {startFrame} '
               '-e {endFrame} -rl {layer} -exportFramesSeparate')

        return cmd.format(project=instance.context.data["workspaceDir"],
                          cam=instance.data.get("cam", "persp"),
                          startFrame=instance.data["startFrame"],
                          endFrame=instance.data["endFrame"],
                          layer=instance.name)

    def build_jobinfo_environment(self, env):
        """Format environment keys and values to match Deadline rquirements

        Returns:
            dict

        """
        return {"EnvironmentKeyValue%d" % index: "%s=%s" % (k, env[k])
                for index, k in enumerate(env)}

    def format_output_filename_zero(self, instance, filename):
        """Format the expected output file of the Export job

        Example:
            <Scene>/<Layer>/<Scene>_<Layer>
            shot010

        Args:
            instance:
            filename(str):

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
        output_filename = instance.context.data["outputFilePath"]

        # Reformat without tokens
        output_path = smart_replace(output_filename,
                                    {"<Scene>": file_name,
                                     "<Layer>": instance.name})

        start_frame = int(instance.data["startFrame"])
        filename_zero = "{}_{:04d}.vrscene".format(output_path, start_frame)

        result = filename_zero.replace("\\", "/")

        return result
