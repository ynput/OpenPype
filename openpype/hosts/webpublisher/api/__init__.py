import os
import logging

import pyblish.api

from openpype.host import HostBase
from openpype.hosts.webpublisher import WEBPUBLISHER_ROOT_DIR

log = logging.getLogger("openpype.hosts.webpublisher")


class WebpublisherHost(HostBase):
    name = "webpublisher"

    def install(self):
        print("Installing Pype config...")
        pyblish.api.register_host(self.name)

        publish_plugin_dir = os.path.join(
            WEBPUBLISHER_ROOT_DIR, "plugins", "publish"
        )
        pyblish.api.register_plugin_path(publish_plugin_dir)
        self.log.info(publish_plugin_dir)
