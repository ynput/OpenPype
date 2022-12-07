# -*- coding: utf-8 -*-
from openpype.hosts.max.api import MaxHost
from openpype.pipeline import install_host

host = MaxHost()
install_host(host)
