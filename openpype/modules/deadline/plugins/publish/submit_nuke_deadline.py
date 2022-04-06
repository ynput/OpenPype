import os
import re
import json
import getpass

import requests

from avalon import api
import pyblish.api
import nuke


class NukeSubmitDeadline(pyblish.api.InstancePlugin):
    """Submit write to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via settings key "DEADLINE_REST_URL".

    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["nuke", "nukestudio"]
    families = ["render.farm", "prerender.farm"]
    optional = True

    # presets
    priority = 50
    chunk_size = 1
    concurrent_tasks = 1
    primary_pool = ""
    secondary_pool = ""
    group = ""
    department = ""
    limit_groups = {}
    use_gpu = False
    env_allowed_keys = []
    env_search_replace_values = {}

    def process(self, instance):
        instance.data["toBeRenderedOn"] = "deadline"
        families = instance.data["families"]

        node = instance[0]
        context = instance.context

        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            deadline_url = instance.data.get("deadlineUrl")
        assert deadline_url, "Requires Deadline Webservice URL"

        self.deadline_url = "{}/api/jobs".format(deadline_url)
        self._comment = context.data.get("comment", "")
        self._ver = re.search(r"\d+\.\d+", context.data.get("hostVersion"))
        self._deadline_user = context.data.get(
            "deadlineUser", getpass.getuser())
        self._frame_start = int(instance.data["frameStartHandle"])
        self._frame_end = int(instance.data["frameEndHandle"])

        # get output path
        render_path = instance.data['path']
        script_path = context.data["currentFile"]

        for item in context:
            if "workfile" in item.data["families"]:
                msg = "Workfile (scene) must be published along"
                assert item.data["publish"] is True, msg

                template_data = item.data.get("anatomyData")
                rep = item.data.get("representations")[0].get("name")
                template_data["representation"] = rep
                template_data["ext"] = rep
                template_data["comment"] = None
                anatomy_filled = context.data["anatomy"].format(template_data)
                template_filled = anatomy_filled["publish"]["path"]
                script_path = os.path.normpath(template_filled)

                self.log.info(
                    "Using published scene for render {}".format(script_path)
                )

        # exception for slate workflow
        if "slate" in instance.data["families"]:
            self._frame_start -= 1

        response = self.payload_submit(instance,
                                       script_path,
                                       render_path,
                                       node.name()
                                       )
        # Store output dir for unified publisher (filesequence)
        instance.data["deadlineSubmissionJob"] = response.json()
        instance.data["outputDir"] = os.path.dirname(
            render_path).replace("\\", "/")
        instance.data["publishJobState"] = "Suspended"

        if instance.data.get("bakingNukeScripts"):
            for baking_script in instance.data["bakingNukeScripts"]:
                render_path = baking_script["bakeRenderPath"]
                script_path = baking_script["bakeScriptPath"]
                exe_node_name = baking_script["bakeWriteNodeName"]

                # exception for slate workflow
                if "slate" in instance.data["families"]:
                    self._frame_start += 1

                resp = self.payload_submit(
                    instance,
                    script_path,
                    render_path,
                    exe_node_name,
                    response.json()
                )

                # Store output dir for unified publisher (filesequence)
                instance.data["deadlineSubmissionJob"] = resp.json()
                instance.data["publishJobState"] = "Suspended"

        # redefinition of families
        if "render.farm" in families:
            instance.data['family'] = 'write'
            families.insert(0, "render2d")
        elif "prerender.farm" in families:
            instance.data['family'] = 'write'
            families.insert(0, "prerender")
        instance.data["families"] = families

    def payload_submit(self,
                       instance,
                       script_path,
                       render_path,
                       exe_node_name,
                       responce_data=None
                       ):
        render_dir = os.path.normpath(os.path.dirname(render_path))
        script_name = os.path.basename(script_path)
        jobname = "%s - %s" % (script_name, instance.name)

        output_filename_0 = self.preview_fname(render_path)

        if not responce_data:
            responce_data = {}

        try:
            # Ensure render folder exists
            os.makedirs(render_dir)
        except OSError:
            pass

        # define chunk and priority
        chunk_size = instance.data["deadlineChunkSize"]
        if chunk_size == 0 and self.chunk_size:
            chunk_size = self.chunk_size

        # define chunk and priority
        concurrent_tasks = instance.data["deadlineConcurrentTasks"]
        if concurrent_tasks == 0 and self.concurrent_tasks:
            concurrent_tasks = self.concurrent_tasks

        priority = instance.data["deadlinePriority"]
        if not priority:
            priority = self.priority

        # resolve any limit groups
        limit_groups = self.get_limit_groups()
        self.log.info("Limit groups: `{}`".format(limit_groups))

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": script_name,

                # Asset dependency to wait for at least the scene file to sync.
                # "AssetDependency0": script_path,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": self._deadline_user,

                "Priority": priority,
                "ChunkSize": chunk_size,
                "ConcurrentTasks": concurrent_tasks,

                "Department": self.department,

                "Pool": self.primary_pool,
                "SecondaryPool": self.secondary_pool,
                "Group": self.group,

                "Plugin": "Nuke",
                "Frames": "{start}-{end}".format(
                    start=self._frame_start,
                    end=self._frame_end
                ),
                "Comment": self._comment,

                # Optional, enable double-click to preview rendered
                # frames from Deadline Monitor
                "OutputFilename0": output_filename_0.replace("\\", "/"),

                # limiting groups
                "LimitGroups": ",".join(limit_groups)

            },
            "PluginInfo": {
                # Input
                "SceneFile": script_path,

                # Output directory and filename
                "OutputFilePath": render_dir.replace("\\", "/"),
                # "OutputFilePrefix": render_variables["filename_prefix"],

                # Mandatory for Deadline
                "Version": self._ver.group(),

                # Resolve relative references
                "ProjectPath": script_path,
                "AWSAssetFile0": render_path,

                # using GPU by default
                "UseGpu": self.use_gpu,

                # Only the specific write node is rendered.
                "WriteNode": exe_node_name
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        if responce_data.get("_id"):
            payload["JobInfo"].update({
                "JobType": "Normal",
                "BatchName": responce_data["Props"]["Batch"],
                "JobDependency0": responce_data["_id"],
                "ChunkSize": 99999999
            })

        # Include critical environment variables with submission
        keys = [
            "PYTHONPATH",
            "PATH",
            "AVALON_SCHEMA",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "PYBLISHPLUGINPATH",
            "NUKE_PATH",
            "TOOL_ENV",
            "FOUNDRY_LICENSE"
        ]
        # Add mongo url if it's enabled
        if instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        # add allowed keys from preset if any
        if self.env_allowed_keys:
            keys += self.env_allowed_keys

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)

        for _path in os.environ:
            if _path.lower().startswith('openpype_'):
                environment[_path] = os.environ[_path]

        # to recognize job from PYPE for turning Event On/Off
        environment["OPENPYPE_RENDER_JOB"] = "1"

        # finally search replace in values of any key
        if self.env_search_replace_values:
            for key, value in environment.items():
                for _k, _v in self.env_search_replace_values.items():
                    environment[key] = value.replace(_k, _v)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("using render plugin : {}".format(plugin))

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        # adding expectied files to instance.data
        self.expected_files(instance, render_path)
        self.log.debug("__ expectedFiles: `{}`".format(
            instance.data["expectedFiles"]))
        response = requests.post(self.deadline_url, json=payload, timeout=10)

        if not response.ok:
            raise Exception(response.text)

        return response

    def preflight_check(self, instance):
        """Ensure the startFrame, endFrame and byFrameStep are integers"""

        for key in ("frameStart", "frameEnd"):
            value = instance.data[key]

            if int(value) == value:
                continue

            self.log.warning(
                "%f=%d was rounded off to nearest integer"
                % (value, int(value))
            )

    def preview_fname(self, path):
        """Return output file path with #### for padding.

        Deadline requires the path to be formatted with # in place of numbers.
        For example `/path/to/render.####.png`

        Args:
            path (str): path to rendered images

        Returns:
            str

        """
        self.log.debug("_ path: `{}`".format(path))
        if "%" in path:
            search_results = re.search(r"(%0)(\d)(d.)", path).groups()
            self.log.debug("_ search_results: `{}`".format(search_results))
            return int(search_results[1])
        if "#" in path:
            self.log.debug("_ path: `{}`".format(path))
        return path

    def expected_files(self,
                       instance,
                       path):
        """ Create expected files in instance data
        """
        if not instance.data.get("expectedFiles"):
            instance.data["expectedFiles"] = []

        dir = os.path.dirname(path)
        file = os.path.basename(path)

        if "#" in file:
            pparts = file.split("#")
            padding = "%0{}d".format(len(pparts) - 1)
            file = pparts[0] + padding + pparts[-1]

        if "%" not in file:
            instance.data["expectedFiles"].append(path)
            return

        for i in range(self._frame_start, (self._frame_end + 1)):
            instance.data["expectedFiles"].append(
                os.path.join(dir, (file % i)).replace("\\", "/"))

    def get_limit_groups(self):
        """Search for limit group nodes and return group name.
        Limit groups will be defined as pairs in Nuke deadline submitter
        presents where the key will be name of limit group and value will be
        a list of plugin's node class names. Thus, when a plugin uses more
        than one node, these will be captured and the triggered process
        will add the appropriate limit group to the payload jobinfo attributes.
        Returning:
            list: captured groups list
        """
        captured_groups = []
        for lg_name, list_node_class in self.limit_groups.items():
            for node_class in list_node_class:
                for node in nuke.allNodes(recurseGroups=True):
                    # ignore all nodes not member of defined class
                    if node.Class() not in node_class:
                        continue
                    # ignore all disabled nodes
                    if node["disable"].value():
                        continue
                    # add group name if not already added
                    if lg_name not in captured_groups:
                        captured_groups.append(lg_name)
        return captured_groups
