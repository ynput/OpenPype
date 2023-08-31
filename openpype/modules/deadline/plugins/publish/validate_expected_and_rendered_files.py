import os
import requests

import pyblish.api

from openpype.lib import collect_frames
from openpype_modules.deadline.abstract_submit_deadline import requests_get


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
        """Process all the nodes in the instance"""

        # get dependency jobs ids for retrieving frame list
        dependent_job_ids = self._get_dependent_job_ids(instance)

        if not dependent_job_ids:
            self.log.warning("No dependent jobs found for instance: {}"
                             "".format(instance))
            return

        # get list of frames from dependent jobs
        frame_list = self._get_dependent_jobs_frames(
            instance, dependent_job_ids)

        for repre in instance.data["representations"]:
            expected_files = self._get_expected_files(repre)

            staging_dir = repre["stagingDir"]
            existing_files = self._get_existing_files(staging_dir)

            if self.allow_user_override:
                # We always check for user override because the user might have
                # also overridden the Job frame list to be longer than the
                # originally submitted frame range
                # todo: We should first check if Job frame range was overridden
                #       at all so we don't unnecessarily override anything
                file_name_template, frame_placeholder = \
                    self._get_file_name_template_and_placeholder(
                        expected_files)

                if not file_name_template:
                    raise RuntimeError("Unable to retrieve file_name template"
                                       "from files: {}".format(expected_files))

                job_expected_files = self._get_job_expected_files(
                    file_name_template,
                    frame_placeholder,
                    frame_list)

                job_files_diff = job_expected_files.difference(expected_files)
                if job_files_diff:
                    self.log.debug(
                        "Detected difference in expected output files from "
                        "Deadline job. Assuming an updated frame list by the "
                        "user. Difference: {}".format(sorted(job_files_diff))
                    )

                    # Update the representation expected files
                    self.log.info("Update range from actual job range "
                                  "to frame list: {}".format(frame_list))
                    repre["files"] = sorted(job_expected_files)

                    # Update the expected files
                    expected_files = job_expected_files

            # We don't use set.difference because we do allow other existing
            # files to be in the folder that we might not want to use.
            missing = expected_files - existing_files
            if missing:
                raise RuntimeError(
                    "Missing expected files: {}\n"
                    "Expected files: {}\n"
                    "Existing files: {}".format(
                        sorted(missing),
                        sorted(expected_files),
                        sorted(existing_files)
                    )
                )

    def _get_dependent_job_ids(self, instance):
        """Returns list of dependent job ids from instance metadata.json

        Args:
            instance (pyblish.api.Instance): pyblish instance

        Returns:
            (list): list of dependent job ids

        """
        dependent_job_ids = []

        # job_id collected from metadata.json
        original_job_id = instance.data["render_job_id"]

        dependent_job_ids_env = os.environ.get("RENDER_JOB_IDS")
        if dependent_job_ids_env:
            dependent_job_ids = dependent_job_ids_env.split(',')
        elif original_job_id:
            dependent_job_ids = [original_job_id]

        return dependent_job_ids

    def _get_dependent_jobs_frames(self, instance, dependent_job_ids):
        """Returns list of frame ranges from all render job.

        Render job might be re-submitted so job_id in metadata.json could be
        invalid. GlobalJobPreload injects current job id to RENDER_JOB_IDS.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            dependent_job_ids (list): list of dependent job ids
        Returns:
            (list)
        """
        all_frame_lists = []

        for job_id in dependent_job_ids:
            job_info = self._get_job_info(instance, job_id)
            frame_list = job_info["Props"].get("Frames")
            if frame_list:
                all_frame_lists.extend(frame_list.split(','))

        return all_frame_lists

    def _get_job_expected_files(self,
                                file_name_template,
                                frame_placeholder,
                                frame_list):
        """Calculates list of names of expected rendered files.

        Might be different from expected files from submission if user
        explicitly and manually changed the frame list on the Deadline job.

        """
        # no frames in file name at all, eg 'renderCompositingMain.withLut.mov'
        if not frame_placeholder:
            return set([file_name_template])

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

            # There might be cases where clique was unable to collect
            # collections in `collect_frames` - thus we capture that case
            if frame is not None:
                frame_placeholder = "#" * len(frame)

                file_name_template = os.path.basename(
                    file_name.replace(frame, frame_placeholder))
            else:
                file_name_template = file_name
            break

        return file_name_template, frame_placeholder

    def _get_job_info(self, instance, job_id):
        """Calls DL for actual job info for 'job_id'

        Might be different than job info saved in metadata.json if user
        manually changes job pre/during rendering.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            job_id (str): Deadline job id

        Returns:
            (dict): Job info from Deadline

        """
        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            deadline_url = instance.data.get("deadlineUrl")
        assert deadline_url, "Requires Deadline Webservice URL"

        url = "{}/api/jobs?JobID={}".format(deadline_url, job_id)
        try:
            response = requests_get(url)
        except requests.exceptions.ConnectionError:
            self.log.error("Deadline is not accessible at "
                           "{}".format(deadline_url))
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

    def _get_existing_files(self, staging_dir):
        """Returns set of existing file names from 'staging_dir'"""
        existing_files = set()
        for file_name in os.listdir(staging_dir):
            existing_files.add(file_name)
        return existing_files

    def _get_expected_files(self, repre):
        """Returns set of file names in representation['files']

        The representations are collected from `CollectRenderedFiles` using
        the metadata.json file submitted along with the render job.

        Args:
            repre (dict): The representation containing 'files'

        Returns:
            set: Set of expected file_names in the staging directory.

        """
        expected_files = set()

        files = repre["files"]
        if not isinstance(files, list):
            files = [files]

        for file_name in files:
            expected_files.add(file_name)
        return expected_files
