import os
import toml
import time
from pype.modules.ftrack.lib import AppAction
from avalon import lib
from pype.api import Logger, config

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
    app_usages = (
        config.get_presets()
        .get("global", {})
        .get("applications")
    ) or {}

    apps = []
    missing_app_names = []
    launchers_path = os.path.join(os.environ["PYPE_CONFIG"], "launchers")
    for file in os.listdir(launchers_path):
        filename, ext = os.path.splitext(file)
        if ext.lower() != ".toml":
            continue

        app_usage = app_usages.get(filename)
        if not app_usage:
            if app_usage is None:
                missing_app_names.append(filename)
            continue

        loaded_data = toml.load(os.path.join(launchers_path, file))
        app_data = {
            "name": filename,
            "label": loaded_data.get("label", filename)
        }
        apps.append(app_data)

    if missing_app_names:
        log.debug(
            "Apps not defined in applications usage. ({})".format(
                ", ".join((
                    "\"{}\"".format(app_name)
                    for app_name in missing_app_names
                ))
            )
        )

    apps = sorted(apps, key=lambda app: app["name"])
    app_counter = 0
    for app in apps:
        try:
            registerApp(app, session, plugins_presets)
            if app_counter % 5 == 0:
                time.sleep(0.1)
            app_counter += 1
        except Exception as exc:
            log.warning(
                "\"{}\" - not a proper App ({})".format(app['name'], str(exc)),
                exc_info=True
            )
