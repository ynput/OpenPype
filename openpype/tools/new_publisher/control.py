import logging
import avalon.api


class PublisherController:
    def __init__(self):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()
