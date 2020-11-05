# -*- coding: utf-8 -*-
"""Abstract class for submitting jobs to Deadline."""
import os
from abc import ABCMeta, abstractmethod

import six
import attr
import requests

import pyblish.api


@attr.s
class DeadlineJobInfo:
    BatchName = attr.ib()


@attr.s
class DeadlinePluginInfo:
    SceneFile = attr.ib()


@six.add_metaclass(ABCMeta)
class AbstractSubmitDeadline(pyblish.api.InstancePlugin):

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    use_published = True
    asset_dependencies = False

    def submit(self, payload):
        url = "{}/api/jobs".format(self._deadline_url)
        response = self._requests_post(url, json=payload)
        if not response.ok:
            self.log.error("Submition failed!")
            self.log.error(response.status_code)
            self.log.error(response.content)
            self.log.debug(payload)
            raise RuntimeError(response.text)

        dependency = response.json()
        return dependency["_id"]

    def _requests_post(self, *args, **kwargs):
        """Wrap request post method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        # add 10sec timeout before bailing out
        kwargs['timeout'] = 10
        return requests.post(*args, **kwargs)

    def _requests_get(self, *args, **kwargs):
        """Wrap request get method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        # add 10sec timeout before bailing out
        kwargs['timeout'] = 10
        return requests.get(*args, **kwargs)
