import os
import toml
import time
from pype.modules.ftrack.lib import AppAction
from avalon import lib
from pype.api import Logger
from pype.lib import get_all_avalon_projects

log = Logger().get_logger(__name__)


def registerApp(app, session, plugins_presets):
    name = app['name']
    variant = ""
    try:
        variant = app['name'].split("_")[1]
    except Exception:
        pass

    abspath = lib.which_app(app['name'])
    if abspath is None:
        log.error(
            "'{0}' - App don't have config toml file".format(app['name'])
        )
        return

    apptoml = toml.load(abspath)

    ''' REQUIRED '''
    executable = apptoml['executable']

    ''' OPTIONAL '''
    label = apptoml.get('ftrack_label', app.get('label', name))
    icon = apptoml.get('ftrack_icon', None)
    description = apptoml.get('description', None)
    preactions = apptoml.get('preactions', [])

    if icon:
        icon = icon.format(os.environ.get('PYPE_STATICS_SERVER', ''))

    # register action
    AppAction(
        session, label, name, executable, variant,
        icon, description, preactions, plugins_presets
    ).register()

    if not variant:
        log.info('- Variant is not set')


def register(session, plugins_presets={}):
    # WARNING getting projects only helps to check connection to mongo
    # - without will `discover` of ftrack apps actions take ages
    result = get_all_avalon_projects()

    apps = []

    launchers_path = os.path.join(os.environ["PYPE_CONFIG"], "launchers")
    for file in os.listdir(launchers_path):
        filename, ext = os.path.splitext(file)
        if ext.lower() != ".toml":
            continue
        loaded_data = toml.load(os.path.join(launchers_path, file))
        app_data = {
            "name": filename,
            "label": loaded_data.get("label", filename)
        }
        apps.append(app_data)

    apps = sorted(apps, key=lambda x: x['name'])
    app_counter = 0
    for app in apps:
        try:
            registerApp(app, session, plugins_presets)
            if app_counter % 5 == 0:
                time.sleep(0.1)
            app_counter += 1
        except Exception as exc:
            log.exception(
                "\"{}\" - not a proper App ({})".format(app['name'], str(exc)),
                exc_info=True
            )
