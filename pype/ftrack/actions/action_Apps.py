import os
import logging
import toml
import ftrack_api
from ftrack_action_handler import AppAction
from avalon import io, lib
from app.api import Logger

log = Logger.getLogger(__name__)

def registerApp(app, session):
    name = app['name'].split("_")[0]
    variant = ""
    try:
        variant = app['name'].split("_")[1]
    except Exception as e:
        log.warning("'{0}' - App 'name' and 'variant' is not separated by '_' (variant is set to '')".format(app['name']))
        return

    abspath = lib.which_app(app['name'])
    if abspath == None:
        log.error("'{0}' - App don't have config toml file".format(app['name']))
        return

    apptoml = toml.load(abspath)
    executable = apptoml['executable']

    label = app['label']
    icon = None
    # TODO get right icons
    if 'nuke' in app['name']:
        icon = "https://mbtskoudsalg.com/images/nuke-icon-png-2.png"
        label = "Nuke"
    elif 'maya' in app['name']:
        icon = "http://icons.iconarchive.com/icons/froyoshark/enkel/256/Maya-icon.png"
        label = "Autodesk Maya"

    # register action
    AppAction(session, label, name, executable, variant, icon).register()


def register(session):
    # TODO AVALON_PROJECT, AVALON_ASSET, AVALON_SILO need to be set or debug from avalon

    # Get all projects from Avalon DB
    try:
        io.install()
        projects = sorted(io.projects(), key=lambda x: x['name'])
        io.uninstall()
    except Exception as e:
        log.error(e)

    apps = []
    appNames = []
    # Get all application from all projects
    for project in projects:
        os.environ['AVALON_PROJECT'] = project['name']
        for app in project['config']['apps']:
            if app['name'] not in appNames:
                appNames.append(app['name'])
                apps.append(app)

    for app in apps:
        try:
            registerApp(app, session)
        except Exception as e:
            log.warning("'{0}' - not proper App ({1})".format(app['name'], e))
