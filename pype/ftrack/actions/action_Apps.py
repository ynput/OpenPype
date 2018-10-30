import os
import logging
import toml
import ftrack_api
from ftrack_action_handler import AppAction
from avalon import io, lib


def register(session):

    os.environ['AVALON_PROJECTS'] = 'tmp'
    io.install()
    projects = sorted(io.projects(), key=lambda x: x['name'])
    io.uninstall()

    apps=[]
    actions = []

    for project in projects:
        os.environ['AVALON_PROJECT'] = project['name']
        for app in project['config']['apps']:
            if app not in apps:
                apps.append(app)

    # TODO get right icons
    for app in apps:
        name = app['name'].split("_")[0]
        variant = app['name'].split("_")[1]
        label = app['label']
        executable = toml.load(lib.which_app(app['name']))['executable']
        icon = None

        if 'nuke' in app['name']:
            icon = "https://mbtskoudsalg.com/images/nuke-icon-png-2.png"
            label = "Nuke"
        elif 'maya' in app['name']:
            icon = "http://icons.iconarchive.com/icons/froyoshark/enkel/256/Maya-icon.png"
            label = "Autodesk Maya"

        AppAction(session, label, name, executable, variant, icon).register()
