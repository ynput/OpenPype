import os
import sys
from urllib.parse import urlparse
import json
import getpass
import tempfile
import opentimelineio as otio
import pyblish.api
import requests

import openpype
import pyblish
import openpype.api
import openpype.lib
from openpype.scripts import transcode
from openpype.settings import get_project_settings

from shutil import copyfile


class SubmitTranscodeDeadline(pyblish.api.InstancePlugin):
    """Submit transcode to Deadline."""

    order = pyblish.api.IntegratorOrder - 0.1
    label = "Submit to Deadline"
    hosts = ["traypublisher"]
    families = ["transcode"]

    def get_published_path(self, representation_name, representation_ext,
                           instance):
        anatomy = instance.context.data["anatomy"]
        template_data = instance.data.get("anatomyData")
        template_data["representation"] = representation_name
        template_data["ext"] = representation_ext
        template_data["comment"] = None
        anatomy_filled = anatomy.format(template_data)
        template_filled = anatomy_filled["publish"]["path"]
        published_path = os.path.normpath(template_filled)

        # Ensure extension is correct. Anatomy is confusing name with ext.
        path, ext = os.path.splitext(published_path)
        published_path = "{}{}".format(path, representation_ext)

        return published_path

    def process(self, instance):
        if instance.context.data.get("defaultDeadline"):
            deadline_url = instance.context.data.get("defaultDeadline")
        assert deadline_url, "Requires Deadline Webservice URL"
        deadline_url = "{}/api/jobs".format(deadline_url)

        editorial_path = instance.context.data["currentFile"]

        # get editorial sequence file into otio timeline object
        extension = os.path.splitext(editorial_path)[1]
        asset_name = instance.data["asset"]
        framerate = openpype.lib.get_asset(asset_name)["data"]["fps"]
        kwargs = {}
        if extension == ".edl":
            # EDL has no frame rate embedded so needs explicit
            # frame rate else 24 is asssumed.
            kwargs["rate"] = framerate

        published_path = self.get_published_path("text",
                                                 ".txt",
                                                 instance)
        published_path = os.path.dirname(published_path)

        timeline = otio.adapters.read_from_file(editorial_path, **kwargs)
        tracks = timeline.each_child(
            descended_from_type=otio.schema.Track
        )
        jobs = []
        clip_names = []
        for track in tracks:
            self.log.info("!!! track:: {}".format(track))
            for clip in track.each_child():
                self.log.info("!!! clip:: {}".format(clip))
                if clip.name is None:
                    continue

                # Skip all generators like black empty.
                if isinstance(clip.media_reference,
                              otio.schema.GeneratorReference):
                    continue

                # Transitions are ignored, because Clips have the full frame
                # range.
                if isinstance(clip, otio.schema.Transition):
                    continue

                # Get start of clips.
                start_frame = int(clip.source_range.start_time.value)
                end_frame = int(start_frame + clip.duration().value)

                # Get media path.
                url = urlparse(clip.media_reference.target_url)
                path = os.path.join(url.netloc, url.path)
                if path.startswith("/"):
                    path = "{}:{}".format(url.scheme, path)
                path = os.path.abspath(path)
                self.log.info("!!! url:: {}".format(url))
                # Ignore "wav" media.
                if path.endswith(".wav"):
                    continue

                # HARDCODED frame pattern for exr files. This should be
                # extended to all image sequences.
                if path.endswith(".exr"):
                    # Bug with xml files where image sequences always start at
                    # 0.
                    if extension == ".xml" and start_frame == 0:
                        start_frame = 1

                    end_frame = start_frame + clip.duration().value - 1

                    basename = os.path.basename(path)
                    directory = os.path.dirname(path)
                    path = "{}.%04d.exr [{}-{}]".format(
                        os.path.join(directory, basename.split(".")[0]),
                        start_frame,
                        end_frame
                    )

                # Need unique names to prevent overwriting.
                name = clip.name
                if name in clip_names:
                    name_occurance = clip_names.count(clip.name)
                    name = "{}_{}".format(clip.name, name_occurance)
                clip_names.append(clip.name)

                dest = os.path.join(published_path,
                                    "transcode_resources")
                if not os.path.isdir(dest):
                    os.makedirs(dest)
                self.log.info(
                    "copyfile:: {} >> {}".format(path, dest))
                copyfile(path.replace("\\", "/"), dest)

                jobs.append({
                    "input_path": dest,
                    "preset": instance.data,
                    "name": name,
                    "output_path": os.path.dirname(published_path),
                    "start": int(start_frame),
                    "end": end_frame
                })

        module_path = transcode.__file__
        if module_path.endswith(".pyc"):
            module_path = module_path[: -len(".pyc")] + ".py"

        # Generate the payloads for Deadline submission
        payloads = []
        args_template = (
            "-input \"{}\"" +
            " -preset {}" +
            " -name {}" +
            " -output {}" +
            " -framerate {}" +
            " -start {}" +
            " -end {}"
        )
        for job in jobs:
            args = args_template.format(
                job["input_path"],
                instance.data["family"],
                job["name"],
                job["output_path"],
                framerate,
                job["start"],
                job["end"]
            )
            payload = self._prepare_base_payload(instance.data["name"],
                                                 job["name"],
                                                 job["output_path"],
                                                 job["input_path"],
                                                 module_path, args)

            # HARDCODED asset dependency format for exr files.
            if "%04d.exr" in job["input_path"]:
                path = job["input_path"].split("exr")[0]
                path = path.replace("%04d", "####") + "exr"
                payload["JobInfo"]["AssetDependency0"] = path

                payload["JobInfo"]["FrameDependencyOffsetEnd"] = job["end"]
                payload["JobInfo"]["FrameDependencyOffsetStart"] = job["start"]
                payload["JobInfo"]["IsFrameDependent"] = True

            payloads.append(payload)

        dependency_ids = []
        for payload in payloads:
            self.log.info("Submitting Deadline job...")
            self.log.info(json.dumps(payload, indent=4, sort_keys=True))

            response = requests.post(deadline_url, json=payload, timeout=10)
            if not response.ok:
                raise Exception(response.text)

            dependency_ids.append(json.loads(response.text)["_id"])

        # Generate concatenate job.
        path = self._write_concat_metadata(instance, jobs)

        representation = {
            "name": "text",
            "ext": ".txt",
            "files": os.path.basename(path),
            "stagingDir": os.path.dirname(path),
        }
        instance.data["representations"].append(representation)

        published_path = self.get_published_path(representation["name"],
                                                 representation["ext"],
                                                 instance)

        # Get audio asset dependency.
        audio_published_path = None
        for representation in instance.data["representations"]:
            if representation["name"] != "audio":
                continue

            audio_published_path = self.get_published_path(
                representation["name"], representation["ext"], instance)

        # Get arguments.
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

        # Generate payload.
        payload = self._prepare_base_payload(instance.data["name"],
                                             instance.data["name"],
                                             output_path, audio_published_path,
                                             module_path, args)

        job_index = 0
        for id in dependency_ids:
            payload["JobInfo"]["JobDependency{}".format(job_index)] = id
            job_index += 1

        self.log.info("Submitting Deadline job...")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        response = requests.post(deadline_url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)

    def _prepare_base_payload(self, batch_name, job_name,
                              output_path, dependency_path,
                              module_path, args):
        payload = {
            "JobInfo": {
                "Plugin": "Python",
                "BatchName": batch_name,
                "Name": job_name,
                "UserName": getpass.getuser(),
                "OutputDirectory0": output_path,
                "AssetDependency0": dependency_path
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

        return payload

    def _write_concat_metadata(self, instance, jobs):
        # Generate concatenate job.
        project_name = instance.context.data["projectEntity"]["name"]
        project_settings = get_project_settings(project_name)
        preset_templates = (project_settings["traypublisher"]
                                            ["TranscodeCreator"]
                                            ["preset_templates"])
        extension = preset_templates["concat"]["output_extension"]
        data = ""
        for job in jobs:
            path = os.path.join(
                job["output_path"],
                "{}{}".format(job["name"], extension)
            ).replace("\\", "/")
            data += f"file '{path}'\n"

        dirpath = tempfile.mkdtemp()
        path = os.path.join(dirpath, instance.data["name"] + ".txt")
        self.log.info("!!!path:: {}".format(path))
        with open(path, "w") as f:
            f.write(data)

        return path
