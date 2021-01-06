import os
from urllib.parse import urlparse
import json
import getpass
import shutil
import tempfile

import opentimelineio as otio
import pyblish.api
import avalon
from avalon.vendor import requests

import pype
import pyblish
import pypeapp
import acre

import pype.api
import pype.lib
from pype.scripts import transcode


class SubmitTranscodeDeadline(pyblish.api.InstancePlugin):
    """Submit transcode to Deadline."""

    order = pyblish.api.IntegratorOrder - 0.1
    label = "Submit to Deadline"
    hosts = ["standalonepublisher"]
    families = ["transcode"]

    clips_start_frame = None

    def get_published_path(self, representation, instance):
        anatomy = instance.context.data["anatomy"]
        template_data = instance.data.get("anatomyData")
        template_data["representation"] = representation["name"]
        template_data["ext"] = representation["ext"]
        template_data["comment"] = None
        anatomy_filled = anatomy.format(template_data)
        template_filled = anatomy_filled["publish"]["path"]
        published_path = os.path.normpath(template_filled)

        # Ensure extension is correct. Anatomy is confusing name with ext.
        path, ext = os.path.splitext(published_path)
        published_path = "{}{}".format(path, representation["ext"])

        return published_path

    def process(self, instance):
        # Get asset dependencies.
        asset_dependencies = {}
        count = 0
        audio_published_path = None
        for representation in instance.data["representations"]:
            published_path = self.get_published_path(representation, instance)

            asset_dependencies["AssetDependency{}".format(count)] = (
                published_path
            )
            count += 1

            if representation["name"] == "audio":
                audio_published_path = published_path

        # Requried environment.
        PYTHONPATH = ""
        for module in [pype, pyblish, avalon, pypeapp, acre]:
            PYTHONPATH += os.path.dirname(os.path.dirname(module.__file__))
            PYTHONPATH += os.pathsep

        PATH = ""
        for tool in ["oiiotool", "ffmpeg"]:
            PATH += os.path.dirname(shutil.which(tool))
            PATH += os.pathsep

        editorial_path = instance.context.data["currentFile"]

        # get editorial sequence file into otio timeline object
        extension = os.path.splitext(editorial_path)[1]
        framerate = pype.lib.get_asset()["data"]["fps"]
        kwargs = {}
        if extension == ".edl":
            # EDL has no frame rate embedded so needs explicit
            # frame rate else 24 is asssumed.
            kwargs["rate"] = framerate

        timeline = otio.adapters.read_from_file(editorial_path, **kwargs)
        tracks = timeline.each_child(
            descended_from_type=otio.schema.track.Track
        )
        jobs = []
        for track in tracks:
            for clip in track.each_child():
                if clip.name is None:
                    continue

                # Skip all generators like black empty.
                if isinstance(clip.media_reference,
                              otio.schema.GeneratorReference):
                    continue

                # Transitions are ignored, because Clips have the full frame
                # range.
                if isinstance(clip, otio.schema.transition.Transition):
                    continue

                # Get start of clips.
                clip_range = clip.range_in_parent()
                if self.clips_start_frame is None:
                    self.clips_start_frame = clip_range.start_time.value

                # Get media path.
                url = urlparse(clip.media_reference.target_url)
                path = os.path.join(url.netloc, url.path)
                if path.startswith("/"):
                    path = path[1:]
                path = os.path.abspath(path)

                # HARDCODED frame pattern for exr files.
                # Also hardcoded is the start frame, which is assumed to 1.
                if path.endswith(".exr"):
                    basename = os.path.basename(path)
                    directory = os.path.dirname(path)
                    path = "{}.%04d.exr [{}-{}]".format(
                        os.path.join(directory, basename.split(".")[0]),
                        1,
                        clip.duration().value
                    )

                start_frame = (
                    clip_range.start_time.value - self.clips_start_frame
                )
                jobs.append({
                    "input_path": path.replace("\\", "/"),
                    "preset": instance.data,
                    "name": clip.name,
                    "output_path": os.path.dirname(
                        instance.context.data["currentFile"]
                    ).replace("\\", "/"),
                    "start": int(start_frame)
                })

        module_path = transcode.__file__
        if module_path.endswith(".pyc"):
            module_path = module_path[: -len(".pyc")] + ".py"

        # Generate the payloads for Deadline submission
        payloads = []
        for job in jobs:
            args_string = (
                "-input \"{}\" -preset {} -name {} -output {}"
            )
            args = args_string.format(
                job["input_path"],
                instance.data["family"],
                job["name"],
                job["output_path"]
            )
            payload = {
                "JobInfo": {
                    "Plugin": "Python",
                    "BatchName": instance.data["name"],
                    "Name": job["name"],
                    "UserName": getpass.getuser(),
                    "OutputDirectory0": job["output_path"],
                    "EnvironmentKeyValue0": "PYTHONPATH={}".format(PYTHONPATH),
                    "EnvironmentKeyValue1": "PATH={}".format(PATH)
                },
                "PluginInfo": {
                    "Version": "3.7",
                    "ScriptFile": module_path.replace("\\", "/"),
                    "Arguments": args,
                    "SingleFrameOnly": "True",
                },
                # Mandatory for Deadline, may be empty
                "AuxFiles": [],
            }

            # Add asset dependencies.
            payload["JobInfo"].update(asset_dependencies)

            payloads.append(payload)

        dependency_ids = []
        for payload in payloads:
            self.log.info("Submitting Deadline job...")
            self.log.info(json.dumps(payload, indent=4, sort_keys=True))

            url = "{}/api/jobs".format(
                os.environ.get("DEADLINE_REST_URL", "http://localhost:8082")
            )
            response = requests.post(url, json=payload, timeout=10)
            if not response.ok:
                raise Exception(response.text)

            dependency_ids.append(json.loads(response.text)["_id"])

        # Generate concatenate job.
        extension = transcode.preset_templates["concat"]["extension"]
        data = ""
        for job in jobs:
            path = os.path.join(
                job["output_path"],
                "{}{}".format(job["name"], extension)
            ).replace("\\", "/")
            data += f"file '{path}'\n"

        dirpath = tempfile.mkdtemp()
        path = os.path.join(dirpath, instance.data["name"] + ".txt")
        with open(path, "w") as f:
            f.write(data)

        representation = {
            "name": "text",
            "ext": ".txt",
            "files": os.path.basename(path),
            "stagingDir": os.path.dirname(path),
        }
        instance.data["representations"].append(representation)

        published_path = self.get_published_path(representation, instance)

        output_path = os.path.dirname(
            instance.context.data["currentFile"]
        ).replace("\\", "/")
        input_path = published_path.replace("\\", "/")
        name = instance.data["name"]
        args = (
            f"-input {input_path} -name {name} -preset concat "
            f"-output {output_path} -audio {audio_published_path} "
            f"-start 0 -framerate {framerate}"
        )
        payload = {
            "JobInfo": {
                "Plugin": "Python",
                "BatchName": instance.data["name"],
                "Name": instance.data["name"],
                "UserName": getpass.getuser(),
                "OutputDirectory0": output_path,
                "EnvironmentKeyValue0": "PYTHONPATH={}".format(PYTHONPATH),
                "EnvironmentKeyValue1": "PATH={}".format(PATH),
                "AssetDependency0": published_path
            },
            "PluginInfo": {
                "Version": "3.7",
                "ScriptFile": module_path.replace("\\", "/"),
                "Arguments": args,
                "SingleFrameOnly": "True",
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
        }

        job_index = 0
        for id in dependency_ids:
            payload["JobInfo"]["JobDependency{}".format(job_index)] = id
            job_index += 1

        self.log.info("Submitting Deadline job...")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        url = "{}/api/jobs".format(
            os.environ.get("DEADLINE_REST_URL", "http://localhost:8082")
        )
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)
