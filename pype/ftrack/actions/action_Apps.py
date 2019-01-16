import os
import toml
from ftrack_action_handler import AppAction
from avalon import io, lib
from app.api import Logger

log = Logger.getLogger(__name__)


def registerApp(app, session):
    name = app['name']
    variant = ""
    try:
        variant = app['name'].split("_")[1]
    except Exception:
        log.warning((
            '"{0}" - App "name" and "variant" is not separated by "_"'
            ' (variant is not set)'
        ).format(app['name']))
        return

    abspath = lib.which_app(app['name'])
    if abspath is None:
        log.error(
            "'{0}' - App don't have config toml file".format(app['name'])
        )
        return

    apptoml = toml.load(abspath)

    executable = apptoml['executable']
    label = apptoml.get('ftrack_label', app['label'])
    icon = apptoml.get('ftrack_icon', None)
    description = apptoml.get('description', None)

    # register action
    AppAction(
        session, label, name, executable, variant, icon, description
    ).register()


def register(session):
    # set avalon environ - they just must exist
    os.environ['AVALON_PROJECT'] = ''
    os.environ['AVALON_ASSET'] = ''
    os.environ['AVALON_SILO'] = ''
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
