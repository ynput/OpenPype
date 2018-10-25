import os
import logging
import ftrack_api
from ftrack_action_handler.appaction import AppAction
from avalon import io


os.environ['AVALON_PROJECTS'] = 'tmp'
io.install()
projects = sorted(io.projects(), key=lambda x: x['name'])
io.uninstall()

# Temporary
s = ftrack_api.Session(
    server_url="https://pype.ftrackapp.com",
    api_key="4e01eda0-24b3-4451-8e01-70edc03286be",
    api_user="jakub.trllo"
)

def register(session):
    apps=[]
    actions = []
    for project in projects:
        os.environ['AVALON_PROJECT'] = project['name']
        for app in project['config']['apps']:
            if app not in apps:
                apps.append(app)

    for app in apps:
        AppAction(session, app['label'], app['name']).register()


    session.event_hub.wait()

register(s)
