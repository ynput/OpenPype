# Module Arrow,clique need to be installed!!!!!!!!!
import ftrack_api

# TO DO load config with column name that need to be imported/exported


import os

from avalon import api as avalon
from pyblish import api as pyblish
from avalon import io


#project = Avalonsession.find({"type": "project"})

# Action - On create/change/delete event chekc if data are send data to avalon

session = ftrack_api.Session(
    server_url="https://pype.ftrackapp.com",
    api_key="4e01eda0-24b3-4451-8e01-70edc03286be",
    api_user="jakub.trllo"
)
