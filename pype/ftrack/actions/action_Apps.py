import os
import logging
import toml
import ftrack_api
from ftrack_action_handler.appaction import AppAction
from avalon import io, lib


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
    icon = None

    for project in projects:
        os.environ['AVALON_PROJECT'] = project['name']
        for app in project['config']['apps']:
            if app not in apps:
                apps.append(app)

    for app in apps:
        if 'nuke' in app['name']:
            icon = "https://mbtskoudsalg.com/images/nuke-icon-png-2.png"
        elif 'maya' in app['name']:
            icon = "http://icons.iconarchive.com/icons/froyoshark/enkel/256/Maya-icon.png"
        else:
            icon = None

        AppAction(session, app['label'], app['name'], icon).register()

    session.event_hub.wait()

register(s)
