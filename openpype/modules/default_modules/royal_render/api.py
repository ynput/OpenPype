# -*- coding: utf-8 -*-
from .rr_job import RRJob, SubmitFile


class Api:

    def create_submission(self, jobs, submitter_attributes):
        """"""
        raise NotImplementedError

    def add_job(self, job):
        ...