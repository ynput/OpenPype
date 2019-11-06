# api.py
import os
import sys

import pico
from pico import PicoApp
from app.api import forward, Logger

import pipeline as ppl

log = Logger.getLogger(__name__, "aport")


@pico.expose()
def get_session():
    ppl.AVALON_PROJECT = os.getenv("AVALON_PROJECT", None)
    ppl.AVALON_ASSET = os.getenv("AVALON_ASSET", None)
    ppl.AVALON_TASK = os.getenv("AVALON_TASK", None)
    ppl.AVALON_SILO = os.getenv("AVALON_SILO", None)
    return ppl.get_session()


@pico.expose()
def load_representations(project, representations):
    '''Querry data from mongo db for defined representations.

    Args:
        project (str): name of the project
        representations (list): representations which are required

    Returns:
        data (dict): representations in last versions

    # testing url:
    http://localhost:4242/api/load_representations?project=jakub_projectx&representations=[{%22asset%22:%22e09s031_0040%22,%22subset%22:%22referenceDefault%22,%22representation%22:%22mp4%22},%20{%22asset%22:%22e09s031_0030%22,%22subset%22:%22referenceDefault%22,%22representation%22:%22mp4%22}]

    # returning:
    {"e09s031_0040_referenceDefault":{"_id":"5c6dabaa2af61756b02f7f32","schema":"pype:representation-2.0","type":"representation","parent":"5c6dabaa2af61756b02f7f31","name":"mp4","data":{"path":"C:\\Users\\hubert\\_PYPE_testing\\projects\\jakub_projectx\\thisFolder\\e09\\s031\\e09s031_0040\\publish\\clip\\referenceDefault\\v019\\jkprx_e09s031_0040_referenceDefault_v019.mp4","template":"{publish.root}/{publish.folder}/{version.main}/{publish.file}"},"dependencies":[],"context":{"root":"C:\\Users\\hubert\\_PYPE_testing\\projects","project":{"name":"jakub_projectx","code":"jkprx"},"task":"edit","silo":"thisFolder","asset":"e09s031_0040","family":"clip","subset":"referenceDefault","VERSION":19,"hierarchy":"thisFolder\\e09\\s031","representation":"mp4"}}}
    '''
    data = {}
    # log.info("___project: {}".format(project))
    # ppl.io.activate_project(project)
    #
    # from_mongo = ppl.io.find({"name": repr['representation'],
    #                           "type": "representation"})[:]

    for repr in representations:
        log.info("asset: {}".format(repr['asset']))
        # set context for each asset individually
        context(project, repr['asset'], '')

        # query data from mongo db for the asset's subset representation
        related_repr = [r for r in ppl.io.find({"name": repr['representation'],
                                                "type": "representation",
                                                "context.asset": repr['asset']})[:]]

        versions_dict = {r['context']['version']: i
                         for i, r in enumerate(related_repr)}
        versions_list = [v for v in versions_dict.keys()]
        sorted(versions_list)

        version_index_last = versions_dict[max(versions_list)]

        log.info("version_index_last: {}".format(version_index_last))
        # create name which will be used on timeline clip
        name = '_'.join([repr['asset'], repr['subset']])

        # log.info("___related_repr: {}".format(related_repr))
        # assign data for the clip representation
        version = ppl.io.find_one(
            {'_id': related_repr[version_index_last]['parent']})
        log.info("version: {}".format(version))

        # fixing path workarround
        if '.#####.mxf' in related_repr[version_index_last]['data']['path']:
            related_repr[version_index_last]['data']['path'] = related_repr[version_index_last]['data']['path'].replace(
                '.#####.mxf', '.mxf')

        related_repr[version_index_last]['version'] = version
        related_repr[version_index_last]['parentClip'] = repr['parentClip']
        data[name] = related_repr[version_index_last]

    return data


@pico.expose()
def publish(send_json_path, get_json_path, gui):
    """
    Runs standalone pyblish and adds link to
    data in external json file

    It is necessary to run `register_plugin_path` if particular
    host is needed

    Args:
        send_json_path (string): path to temp json file with
                                sending context data
        get_json_path (strign): path to temp json file with
                                returning context data

    Returns:
        dict: get_json_path

    Raises:
        Exception: description

    """

    log.info("avalon.session is: \n{}".format(ppl.SESSION))
    log.info("PUBLISH_PATH: \n{}".format(os.environ["PUBLISH_PATH"]))

    pype_start = os.path.join(os.getenv('PYPE_SETUP_ROOT'),
                              "app", "pype-start.py")

    args = [pype_start,
            "--root", os.environ['AVALON_PROJECTS'], "--publish-gui",
            "-pp", os.environ["PUBLISH_PATH"],
            "-d", "rqst_json_data_path", send_json_path,
            "-d", "post_json_data_path", get_json_path
            ]

    log.debug(args)
    log.info("_aport.api Variable `AVALON_PROJECTS` had changed to `{0}`.".format(
        os.environ['AVALON_PROJECTS']))
    forward([
        sys.executable, "-u"
    ] + args,
        # cwd=cwd
    )

    return {"get_json_path": get_json_path}


@pico.expose()
def context(project, asset, task, app='aport'):
    os.environ["AVALON_PROJECT"] = ppl.AVALON_PROJECT = project
    os.environ["AVALON_ASSET"] = ppl.AVALON_ASSET = asset
    os.environ["AVALON_TASK"] = ppl.AVALON_TASK = task
    os.environ["AVALON_SILO"] = ppl.AVALON_SILO = ''

    ppl.get_session()
    # log.info('ppl.SESSION: {}'.format(ppl.SESSION))

    # http://localhost:4242/pipeline/context?project=this&asset=shot01&task=comp

    ppl.update_current_task(task, asset, app)

    project_code = ppl.io.find_one({"type": "project"})["data"].get("code", '')

    os.environ["AVALON_PROJECTCODE"] = \
        ppl.SESSION["AVALON_PROJECTCODE"] = project_code

    parents = ppl.io.find_one({"type": 'asset',
                               "name": ppl.AVALON_ASSET})['data']['parents']

    if parents and len(parents) > 0:
        # hierarchy = os.path.sep.join(hierarchy)
        hierarchy = os.path.join(*parents).replace("\\", "/")

    os.environ["AVALON_HIERARCHY"] = \
        ppl.SESSION["AVALON_HIERARCHY"] = hierarchy

    fix_paths = {k: v.replace("\\", "/") for k, v in ppl.SESSION.items()
                 if isinstance(v, str)}

    ppl.SESSION.update(fix_paths)
    ppl.SESSION.update({"AVALON_HIERARCHY": hierarchy,
                        "AVALON_PROJECTCODE": project_code,
                        "current_dir": os.getcwd().replace("\\", "/")
                        })

    return ppl.SESSION


@pico.expose()
def anatomy_fill(data):
    from pype import api as pype
    pype.load_data_from_templates()
    anatomy = pype.Anatomy
    return anatomy.format(data)


@pico.expose()
def deregister_plugin_path():
    if os.getenv("PUBLISH_PATH", None):
        aport_plugin_path = os.pathsep.join(
            [p.replace("\\", "/")
             for p in os.environ["PUBLISH_PATH"].split(os.pathsep)
             if "aport" in p or
             "ftrack" in p])
        os.environ["PUBLISH_PATH"] = aport_plugin_path
    else:
        log.warning("deregister_plugin_path(): No PUBLISH_PATH is registred")

    return "Publish path deregistered"


@pico.expose()
def register_plugin_path(publish_path):
    deregister_plugin_path()
    if os.getenv("PUBLISH_PATH", None):
        os.environ["PUBLISH_PATH"] = os.pathsep.join(
            os.environ["PUBLISH_PATH"].split(os.pathsep)
            + [publish_path.replace("\\", "/")]
        )
    else:
        os.environ["PUBLISH_PATH"] = publish_path

    log.info(os.environ["PUBLISH_PATH"].split(os.pathsep))

    return "Publish registered paths: {}".format(
        os.environ["PUBLISH_PATH"].split(os.pathsep)
    )


app = PicoApp()
app.register_module(__name__)

# remove all Handlers created by pico
for name, handler in [(handler.get_name(), handler)
                      for handler in Logger.logging.root.handlers[:]]:
    if "pype" not in str(name).lower():
        Logger.logging.root.removeHandler(handler)

# SPLASH.hide_splash()
