import os
import json
import requests

import pyblish.api

from openpype.lib.abstract_submit_deadline import requests_get
from openpype.lib.delivery import collect_frames


class ValidateExpectedFiles(pyblish.api.InstancePlugin):
    """Compare rendered and expected files"""

    label = "Validate rendered files from Deadline"
    order = pyblish.api.ValidatorOrder
    families = ["render"]
    targets = ["deadline"]

    # check if actual frame range on render job wasn't different
    # case when artists wants to render only subset of frames
    allow_user_override = True

    def process(self, instance):
        self.instance = instance
        frame_list = self._get_frame_list(instance.data["render_job_id"])

        for repre in instance.data["representations"]:
            expected_files = self._get_expected_files(repre)

            staging_dir = repre["stagingDir"]
            existing_files = self._get_existing_files(staging_dir)

            expected_non_existent = expected_files.difference(
                existing_files)
            if len(expected_non_existent) != 0:
                self.log.info("Some expected files missing {}".format(
                    expected_non_existent))

                if self.allow_user_override:
                    file_name_template, frame_placeholder = \
                        self._get_file_name_template_and_placeholder(
                            expected_files)

                    if not file_name_template:
                        return

                    real_expected_rendered = self._get_real_render_expected(
                        file_name_template,
                        frame_placeholder,
                        frame_list)

                    real_expected_non_existent = \
                        real_expected_rendered.difference(existing_files)
                    if len(real_expected_non_existent) != 0:
                        raise RuntimeError("Still missing some files {}".
                                           format(real_expected_non_existent))
                    self.log.info("Update range from actual job range")
                    repre["files"] = sorted(list(real_expected_rendered))
                else:
                    raise RuntimeError("Some expected files missing {}".format(
                        expected_non_existent))

    def _get_frame_list(self, original_job_id):
        """
            Returns list of frame ranges from all render job.

            Render job might be requeried so job_id in metadata.json is invalid
            GlobalJobPreload injects current ids to RENDER_JOB_IDS.

            Args:
                original_job_id (str)
            Returns:
                (list)
        """
        all_frame_lists = []
        render_job_ids = os.environ.get("RENDER_JOB_IDS")
        if render_job_ids:
            render_job_ids = render_job_ids.split(',')
        else:  # fallback
            render_job_ids = [original_job_id]

        for job_id in render_job_ids:
            job_info = self._get_job_info(job_id)
            frame_list = job_info["Props"]["Frames"]
            if frame_list:
                all_frame_lists.extend(frame_list.split(','))

        return all_frame_lists

    def _get_real_render_expected(self, file_name_template, frame_placeholder,
                                  frame_list):
        """
            Calculates list of names of expected rendered files.

            Might be different from job expected files if user explicitly and
            manually change frame list on Deadline job.
        """
        real_expected_rendered = set()
        src_padding_exp = "%0{}d".format(len(frame_placeholder))
        for frames in frame_list:
            if '-' not in frames:  # single frame
                frames = "{}-{}".format(frames, frames)

            start, end = frames.split('-')
            for frame in range(int(start), int(end) + 1):
                ren_name = file_name_template.replace(
                    frame_placeholder, src_padding_exp % frame)
                real_expected_rendered.add(ren_name)

        return real_expected_rendered

    def _get_file_name_template_and_placeholder(self, files):
        """Returns file name with frame replaced with # and this placeholder"""
        sources_and_frames = collect_frames(files)

        file_name_template = frame_placeholder = None
        for file_name, frame in sources_and_frames.items():
            frame_placeholder = "#" * len(frame)
            file_name_template = os.path.basename(
                file_name.replace(frame, frame_placeholder))
            break

        return file_name_template, frame_placeholder

    def _get_job_info(self, job_id):
        """
            Calls DL for actual job info for 'job_id'

            Might be different than job info saved in metadata.json if user
            manually changes job pre/during rendering.
        """
        # get default deadline webservice url from deadline module
        deadline_url = self.instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if self.instance.data.get("deadlineUrl"):
            deadline_url = self.instance.data.get("deadlineUrl")
        assert deadline_url, "Requires Deadline Webservice URL"

        url = "{}/api/jobs?JobID={}".format(deadline_url, job_id)
        try:
            response = requests_get(url)
        except requests.exceptions.ConnectionError:
            print("Deadline is not accessible at {}".format(deadline_url))
            # self.log("Deadline is not accessible at {}".format(deadline_url))
            return {}

        if not response.ok:
            self.log.error("Submission failed!")
            self.log.error(response.status_code)
            self.log.error(response.content)
            raise RuntimeError(response.text)

        json_content = response.json()
        if json_content:
            return json_content.pop()
        return {}

    def _parse_metadata_json(self, json_path):
        if not os.path.exists(json_path):
            msg = "Metadata file {} doesn't exist".format(json_path)
            raise RuntimeError(msg)

        with open(json_path) as fp:
            try:
                return json.load(fp)
            except Exception as exc:
                self.log.error(
                    "Error loading json: "
                    "{} - Exception: {}".format(json_path, exc)
                )

    def _get_existing_files(self, out_dir):
        """Returns set of existing file names from 'out_dir'"""
        existing_files = set()
        for file_name in os.listdir(out_dir):
            existing_files.add(file_name)
        return existing_files

    def _get_expected_files(self, repre):
        """Returns set of file names from metadata.json"""
        expected_files = set()

        files = repre["files"]
        if not isinstance(files, list):
            files = [files]

        for file_name in files:
            expected_files.add(file_name)
        return expected_files
