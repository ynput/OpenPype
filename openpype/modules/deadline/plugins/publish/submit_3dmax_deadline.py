import os
import json
import getpass

import requests
import pyblish.api

from pymxs import runtme as rt
from openpype.pipeline import legacy_io
from openpype.hosts.max.api.lib import get_current_renderer
from openpype.hosts.max.api.lib_rendersettings import RenderSettings


class MaxSubmitRenderDeadline(pyblish.api.InstancePlugin):
    """
    3DMax File Submit Render Deadline

    """

    label = "Submit 3DsMax Render to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["max"]
    families = ["maxrender"]
    targets = ["local"]
    use_published = True
    priority = 50
    chunk_size = 1
    group = None
    deadline_pool = None
    deadline_pool_secondary = None
    framePerTask = 1

    def process(self, instance):
        context = instance.context
        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        deadline_user = context.data.get("deadlineUser", getpass.getuser())
        jobname = "{0} - {1}".format(filename, instance.name)

        # StartFrame to EndFrame
        frames = "{start}-{end}".format(
            start=int(instance.data["frameStart"]),
            end=int(instance.data["frameEnd"])
        )
        if self.use_published:
            for item in context:
                if "workfile" in item.data["families"]:
                    msg = "Workfile (scene) must be published along"
                    assert item.data["publish"] is True, msg

                    template_data = item.data.get("anatomyData")
                    rep = item.data.get("representations")[0].get("name")
                    template_data["representation"] = rep
                    template_data["ext"] = rep
                    template_data["comment"] = None
                    anatomy_data = context.data["anatomy"]
                    anatomy_filled = anatomy_data.format(template_data)
                    template_filled = anatomy_filled["publish"]["path"]
                    filepath = os.path.normpath(template_filled)
                    filepath = filepath.replace("\\", "/")
                    self.log.info(
                        "Using published scene for render {}".format(filepath)
                    )
            if not os.path.exists(filepath):
                self.log.error("published scene does not exist!")

            new_scene = self._clean_name(filepath)
            # use the anatomy data for setting up the path of the files
            orig_scene = self._clean_name(instance.context.data["currentFile"])
            expected_files = instance.data.get("expectedFiles")

            new_exp = []
            for file in expected_files:
                new_file = str(file).replace(orig_scene, new_scene)
                new_exp.append(new_file)

                instance.data["expectedFiles"] = new_exp

            metadata_folder = instance.data.get("publishRenderMetadataFolder")
            if metadata_folder:
                metadata_folder = metadata_folder.replace(orig_scene,
                                                          new_scene)
                instance.data["publishRenderMetadataFolder"] = metadata_folder

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": filename,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": deadline_user,

                "Plugin": instance.data["plugin"],
                "Group": self.group,
                "Pool": self.deadline_pool,
                "secondaryPool": self.deadline_pool_secondary,
                "Frames": frames,
                "ChunkSize": self.chunk_size,
                "Priority": instance.data.get("priority", self.priority),
                "Comment": comment,
                "FramesPerTask": self.framePerTask
            },
            "PluginInfo": {
                # Input
                "SceneFile": filepath,
                "Version": "2023",
                "SaveFile": True,
                # Mandatory for Deadline
                # Houdini version without patch number

                "IgnoreInputs": True
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }
        # Include critical environment variables with submission + api.Session
        keys = [
            # Submit along the current Avalon tool setup that we launched
            # this application with so the Render Slave can build its own
            # similar environment using it, e.g. "maya2018;vray4.x;yeti3.1.9"
            "AVALON_TOOLS",
            "OPENPYPE_VERSION"
        ]
        # Add mongo url if it's enabled
        if context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        # Include OutputFilename entries
        # The first entry also enables double-click to preview rendered
        # frames from Deadline Monitor
        output_data = {}
        # need to be fixed
        for i, filepath in enumerate(instance.data["expectedFiles"]):
            dirname = os.path.dirname(filepath)
            fname = os.path.basename(filepath)
            output_data["OutputDirectory%d" % i] = dirname.replace("\\", "/")
            output_data["OutputFilename%d" % i] = fname

        if not os.path.exists(dirname):
            self.log.info("Ensuring output directory exists: %s" %
                          dirname)
            os.makedirs(dirname)
        plugin_data = {}
        if self.use_published:
            old_output_dir = os.path.dirname(expected_files[0])
            output_beauty = RenderSettings().get_renderoutput(instance.name,
                                                              old_output_dir)
            output_beauty = output_beauty.replace(orig_scene, new_scene)
            output_beauty = output_beauty.replace("\\", "/")
            plugin_data["RenderOutput"] = output_beauty

            renderer_class = get_current_renderer()
            renderer = str(renderer_class).split(":")[0]
            if (
                renderer == "ART_Renderer" or
                renderer == "Redshift_Renderer" or
                renderer == "V_Ray_6_Hotfix_3" or
                renderer == "V_Ray_GPU_6_Hotfix_3" or
                renderer == "Default_Scanline_Renderer" or
                renderer == "Quicksilver_Hardware_Renderer"
            ):
                render_elem_list = RenderSettings().get_render_element()
                for i, render_element in enumerate(render_elem_list):
                    render_element = render_element.replace(orig_scene, new_scene)
                    plugin_data["RenderElementOutputFilename%d" % i] = render_element

            self.log.debug("plugin data:{}".format(plugin_data))
            self.log.info("Scene name was switched {} -> {}".format(
                orig_scene, new_scene
            ))

        payload["JobInfo"].update(output_data)
        payload["PluginInfo"].update(plugin_data)

        self.submit(instance, payload)

    def submit(self, instance, payload):

        context = instance.context
        deadline_url = context.data.get("defaultDeadline")
        deadline_url = instance.data.get(
            "deadlineUrl", deadline_url)

        assert deadline_url, "Requires Deadline Webservice URL"

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("Using Render Plugin : {}".format(plugin))

        self.log.info("Submitting..")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(deadline_url)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)
        # Store output dir for unified publisher (expectedFilesequence)
        expected_files = instance.data["expectedFiles"]
        output_dir = os.path.dirname(expected_files[0])
        instance.data["toBeRenderedOn"] = "deadline"
        instance.data["outputDir"] = output_dir
        instance.data["deadlineSubmissionJob"] = response.json()

    def rename_render_element(self):
        pass

    def _clean_name(self, path):
        return os.path.splitext(os.path.basename(path))[0]