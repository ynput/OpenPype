import os
import json
import pprint
import re
import requests
import pyblish.api


class SubmitDependentImageSequenceJobDeadline(pyblish.api.InstancePlugin):
    """Submit image sequence publish jobs to Deadline.

    These jobs are dependent on a deadline job submission prior to this
    plug-in.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable DEADLINE_REST_URL

    Options in instance.data:
        - deadlineSubmission (dict, Required): The returned .json
            data from the job submission to deadline.

        - outputDir (str, Required): The output directory where the metadata
            file should be generated. It's assumed that this will also be
            final folder containing the output files.

        - ext (str, Optional): The extension (including `.`) that is required
            in the output filename to be picked up for image sequence
            publishing.

        - publishJobState (str, Optional): "Active" or "Suspended"
            This defaults to "Suspended"

    This requires a "startFrame" and "endFrame" to be present in instance.data
    or in context.data.

    """

    label = "Submit image sequence jobs to Deadline"
    order = pyblish.api.IntegratorOrder + 0.2

    hosts = ["celaction"]

    families = [
        "render",
        "deadline"
    ]

    def process(self, instance):

        # DEADLINE_REST_URL = os.environ.get("DEADLINE_REST_URL",
        #                                    "http://localhost:8082")
        # assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        # Get a submission job

        job = instance.data.get("deadlineSubmissionJob")
        if not job:
            raise RuntimeError("Can't continue without valid deadline "
                               "submission prior to this plug-in.")
        ################
        ft_data = instance.context.data["ftrackData"]
        project = ft_data['Project']['name']
        project_code = ft_data['Project']['code']
        projects_path = os.path.dirname(ft_data['Project']['root'])

        data = instance.data.copy()
        asset = instance.context.data["ftrackData"]['Shot']['name']
        subset = 'render' + \
            instance.context.data["ftrackData"]['Task']['name'].capitalize()

        state = data.get("publishJobState", "Suspended")
        # job_name = "{batch} - {subset} [publish image sequence]".format(
        #     batch=job["Props"]["Name"],
        #     subset=subset
        # )
        job_name = "{asset} [publish image sequence]".format(
            asset=asset
        )

        # Get start/end frame from instance, if not available get from context
        context = instance.context

        start = int(instance.data['start'])
        end = int(instance.data['end'])

        try:
            source = data['source']
        except KeyError:
            source = context.data["currentFile"]

        # Write metadata for publish job
        render_job = data.pop("deadlineSubmissionJob")
        metadata = {
            "asset": asset,
            "regex": r"^.*\.png",
            "subset": subset,
            "startFrame": start,
            "endFrame": end,
            "fps": context.data.get("fps", None),
            "families": ["render"],
            "source": source,
            "user": context.data["user"],
            "version": context.data.get('version'),
            "audio": context.data["audio"]['filename'],
            # Optional metadata (for debugging)
            "metadata": {
                "instance": data,
                "job": job,
                "session": fake_avalon_session(project, projects_path)
            }
        }

        # Ensure output dir exists
        output_dir = instance.data["outputDir"]

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        for k, v in metadata.items():
            self.log.info(k)
            self.log.info(v)

        metadata_filename = "{}_metadata.json".format(subset)
        metadata_path = os.path.join(output_dir, metadata_filename)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": "Python",
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "JobType": "Normal",
                "Group": "celaction",
                "JobDependency0": job["_id"],
                "UserName": os.environ['USERNAME'],
                "Comment": instance.context.data.get("comment", ""),
                "InitialStatus": "Active"
            },
            "PluginInfo": {
                "Version": "3.6",
                "ScriptFile": r"\\pype\Core\dev\pype-setup\repos\pype-config\pype\scripts\publish_filesequence.py",
                "Arguments": '--path "{}"'.format(metadata_path),
                "SingleFrameOnly": "True"
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Transfer the environment from the original job to this dependent
        # job so they use the same environment
        environment = fake_env()
        environment["AVALON_ASSET"] = asset
        environment["AVALON_TASK"] = instance.context.data["ftrackData"]['Task']['name']
        environment["AVALON_PROJECT"] = project
        environment["AVALON_PROJECTS"] = projects_path
        environment["PYPE_STUDIO_PROJECTS_PUBLISH"] = ft_data['Project']['root']
        environment["PYPE_STUDIO_PROJECTS_RENDER"] = ft_data['Project']['root']
        environment["PYPE_STUDIO_PROJECTS_RESOURCES"] = ft_data['Project']['root']
        environment["PYPE_STUDIO_PROJECTS_WORK"] = ft_data['Project']['root']

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        # Avoid copied pools and remove secondary pool
        payload["JobInfo"]["Pool"] = "animation_2d"
        payload["JobInfo"].pop("SecondaryPool", None)

        self.log.info("Submitting..")
        # self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        ################
        ######################
        fake_instance = instance.context.create_instance(
            name=(str(instance) + "1"))

        for k, v in data.items():
            self.log.info(k)
            fake_instance.data[k] = v

        # fake_instance.data['deadlineData'] = payload
        # 'http://192.168.146.8:8082'
        url = "{}/api/jobs".format('http://192.168.146.8:8082')
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)
        ######################
        #######################


def fake_avalon_session(project=None, projects_path=None):
    return {
        "AVALON_APP": "premiere",
        "AVALON_APP_VERSION": "2019",
        "AVALON_ASSET": "editorial",
        "AVALON_CONFIG": "pype",
        "AVALON_CONTAINER_ID": "avalon.container",
        "AVALON_DB": "Pype",
        "AVALON_DEADLINE": "http://192.168.146.8:8082",
        "AVALON_DEBUG": "1",
        "AVALON_EARLY_ADOPTER": "1",
        "AVALON_INSTANCE_ID": "avalon.instance",
        "AVALON_LABEL": "Avalon",
        "AVALON_LOCATION": "http://127.0.0.1",
        "AVALON_MONGO": "mongodb://PypeAdmin:X34vkuwL4wbK9A7X@192.168.146.24:27072/Pype",
        "AVALON_PASSWORD": "secret",
        "AVALON_PROJECT": project or "LBB2_dev",
        "AVALON_PROJECTS": projects_path or "L:/PYPE_test",
        "AVALON_SILO": "editorial",
        "AVALON_TASK": "conform",
        "AVALON_TIMEOUT": "1000",
        "AVALON_USERNAME": "avalon",
        "AVALON_WORKDIR": "L:/PYPE_test/episodes/editorial/work/conform",
        "schema": "avalon-core:session-1.0"
    }


def fake_env():
    return {
        "AVALON_CONFIG": "pype",
        "AVALON_CONTAINER_ID": "avalon.container",
        "AVALON_CORE": "\\\\pype\\Core\\dev\\pype-setup\\repos\\avalon-core",
        "AVALON_DB": "Pype",
        "AVALON_DB_DATA": "\\\\pype\\Core\\dev\\mongo_db_data",
        "AVALON_DEADLINE": "http://192.168.146.8:8082",
        "AVALON_DEBUG": "1",
        "AVALON_EARLY_ADOPTER": "1",
        "AVALON_ENV_NAME": "pype_env",
        "AVALON_HIERARCHY": "",
        "AVALON_INSTANCE_ID": "avalon.instance",
        "AVALON_LABEL": "Avalon",
        "AVALON_LAUNCHER": "\\\\pype\\Core\\dev\\pype-setup\\repos\\avalon-launcher",
        "AVALON_LOCATION": "http://127.0.0.1",
        "AVALON_MONGO": "mongodb://PypeAdmin:X34vkuwL4wbK9A7X@192.168.146.24:27072/Pype",
        "AVALON_MONGO_PORT": "27072",
        "AVALON_PASSWORD": "secret",
        "AVALON_SCHEMA": "\\\\pype\\Core\\dev\\pype-setup\\repos\\clothcat-templates\\schema",
        "AVALON_SILO": "",
        "AVALON_TIMEOUT": "1000",
        "AVALON_USERNAME": "avalon",
        "AVALON_WORKDIR": "default",
        "DEADLINE_PATH": "C:\\Program Files\\Thinkbox\\Deadline10\\bin",
        "DEADLINE_REST_URL": "http://192.168.146.8:8082",
        "FTRACK_API_KEY": "NGI0ZGU3ZjMtNzNiZC00NGVlLWEwY2EtMzA1OWJlZGM0MjAyOjozZWZmMThjZi04MjkwLTQxMzQtODUwMC03NTZhMGJiZTM2MTA",
        "FTRACK_API_USER": "license@clothcatanimation.com",
        "FTRACK_SERVER": "https://clothcat2.ftrackapp.com",
        "MONGO_DB_ENTRYDB": "Pype",
        "MONGO_DB_PASS": "X34vkuwL4wbK9A7X",
        "MONGO_DB_USER": "PypeAdmin",
        "PATH": "\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\lib\\site-packages\\PyQt5\\Qt\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\Scripts;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\Library\\bin;\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env\\python3\\Library;;\\\\pype\\Core\\dev\\pype-setup\\repos\\clothcat-templates\\bin;\\\\pype\\Core\\dev\\pype-setup\\repos\\clothcat-templates\\bin\\windows;\\\\pype\\Core\\dev\\pype-setup\\app;\\\\pype\\core\\software\\ffmpeg\\bin;\\\\pype\\Core\\dev\\Applications\\djv\\bin",
        "PYBLISHPLUGINPATH": "\\\\pype\\Core\\dev\\pype-setup\\repos\\pype-config\\pype\\plugins\\ftrack\\publish;",
        "PYBLISH_BASE": "\\\\pype\\Core\\dev\\pype-setup\\repos\\pyblish-base",
        "PYBLISH_HOSTS": "shell",
        "PYBLISH_LITE": "\\\\pype\\Core\\dev\\pype-setup\\repos\\pyblish-lite",
        "PYBLISH_QML": "\\\\pype\\Core\\dev\\pype-setup\\repos\\pyblish-qml",
        "PYPE_APP_ROOT": "\\\\pype\\Core\\dev\\pype-setup\\app",
        "PYPE_DEBUG": "3",
        "PYPE_DEBUG_STDOUT": "0",
        "PYPE_SETUP_ROOT": "\\\\pype\\Core\\dev\\pype-setup",
        "PYPE_STUDIO_CODE": "CC",
        "PYPE_STUDIO_CONFIG": "\\\\pype\\Core\\dev\\pype-setup\\repos\\pype-config",
        "PYPE_STUDIO_CORE": "\\\\pype\\Core\\dev",
        "PYPE_STUDIO_CORE_MOUNT": "\\\\pype\\Core\\dev",
        "PYPE_STUDIO_NAME": "Cloth Cat",
        "PYPE_STUDIO_SOFTWARE": "\\\\pype\\Core\\dev\\Applications",
        "PYPE_STUDIO_TEMPLATES": "\\\\pype\\Core\\dev\\pype-setup\\repos\\clothcat-templates",
        "PYPE_STUDIO_TOOLS": "\\\\pype\\Core\\dev\\production\\tools",
        "PYTHONPATH": "\\\\pype\\Core\\dev\\pype-setup;\\\\pype\\Core\\dev\\pype-setup\\app\\vendor;\\\\pype\\Core\\dev\\pype-setup\\repos\\avalon-core;\\\\pype\\Core\\dev\\pype-setup\\repos\\avalon-launcher;\\\\pype\\Core\\dev\\pype-setup\\repos\\pyblish-base;\\\\pype\\Core\\dev\\pype-setup\\repos\\pyblish-qml;\\\\pype\\Core\\dev\\pype-setup\\repos\\pyblish-lite;\\\\pype\\Core\\dev\\pype-setup\\repos\\ftrack-event-server;\\\\pype\\Core\\dev\\pype-setup\\repos\\pype-config;\\\\pype\\Core\\dev\\pype-setup\\app\\vendor;\\\\pype\\Core\\dev\\pype-setup\\repos\\pype-config\\pype\\vendor;\\\\pype\\Core\\dev\\pype-setup\\repos\\ftrack-event-server",
        "PYTHONVERBOSE": "True",
        "PYTHON_ENV": "C:\\Users\\Public\\pype_env",
        "REMOTE_ENV_DIR": "\\\\pype\\Core\\dev\\pype-setup\\bin\\python\\pype_env",
        "REMOTE_ENV_ON": "0",
        "SCHEMA": "avalon-core:session-1.0",
        "STUDIO_SOFT": "\\\\evo2\\core\\Applications",
        "TOOL_ENV": "\\\\pype\\Core\\dev\\pype-setup\\repos\\clothcat-templates\\environments",
        "USERNAME": "pype"
    }
