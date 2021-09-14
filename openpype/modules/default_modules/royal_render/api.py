# -*- coding: utf-8 -*-
"""Wrapper around Royal Render API."""
from .rr_job import RRJob, SubmitFile


class Api:

    def create_submission(self, jobs, submitter_attributes, file_name=None):
        # type: (list, list, str) -> SubmitFile
        """Create jobs submission file.

        Args:
            jobs (list): List of :class:`RRJob`
            submitter_attributes (list): List of submitter attributes
                :class:`SubmitterParameter` for whole submission batch.
            file_name (str), optional): File path to write data to.

        Returns:
            str: XML data of job submission files.

        """
        raise NotImplementedError

    def send_job_file(self, submit_file):
        # type: (str) -> None
        ...
