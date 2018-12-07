import os
import logging
import toml
import ftrack_api
from ftrack_action_handler import AppAction
from avalon import io, lib
from app.api import Logger

log = Logger.getLogger(__name__)

def registerApp(app, session):
    name = app['name']
    variant = ""
    try:
        variant = app['name'].split("_")[1]
    except Exception as e:
        log.warning("'{0}' - App 'name' and 'variant' is not separated by '_' (variant is not set)".format(app['name']))
        return

    log.warning("app name {}".format(name))
    abspath = lib.which_app(app['name'])
    if abspath == None:
        log.error("'{0}' - App don't have config toml file".format(app['name']))
        return

    apptoml = toml.load(abspath)

    executable = apptoml['executable']

    label = app['label']
    if 'ftrack_label' in apptoml:
        label = apptoml['ftrack_label']

    icon = None
    if 'icon' in apptoml:
        icon = apptoml['icon']

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

    apps = sorted(apps, key=lambda x: x['name'])
    for app in apps:
        try:
            registerApp(app, session)
        except Exception as e:
            log.warning("'{0}' - not proper App ({1})".format(app['name'], e))
