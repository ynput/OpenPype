# api.py
import os
import sys
import tempfile

import pico
from pico import PicoApp
from pico.decorators import request_args, set_cookie, delete_cookie, stream
from pico.decorators import header, cookie

from werkzeug.exceptions import Unauthorized, ImATeapot, BadRequest

from avalon import api as avalon
from avalon import io

import pyblish.api as pyblish

from pypeapp import execute
from pype import api as pype


log = pype.Logger().get_logger(__name__, "aport")


SESSION = avalon.session
if not SESSION:
    io.install()


@pico.expose()
def publish(json_data_path, staging_dir=None):
    """
    Runs standalone pyblish and adds link to
    data in external json file

    It is necessary to run `register_plugin_path` if particular
    host is needed

    Args:
        json_data_path (string): path to temp json file with
                                context data
        staging_dir (strign, optional): path to temp directory

    Returns:
        dict: return_json_path

    Raises:
        Exception: description

    """
    cwd = os.getenv('AVALON_WORKDIR').replace("\\", "/")
    os.chdir(cwd)
    log.info(os.getcwd())
    staging_dir = tempfile.mkdtemp(prefix="pype_aport_").replace("\\", "/")
    log.info("staging_dir: {}".format(staging_dir))
    return_json_path = os.path.join(staging_dir, "return_data.json")

    log.info("avalon.session is: \n{}".format(SESSION))
    pype_start = os.path.join(os.getenv('PYPE_ROOT'),
                              "app", "pype-start.py")

    args = [pype_start, "--publish",
            "-pp", os.environ["PUBLISH_PATH"],
            "-d", "rqst_json_data_path", json_data_path,
            "-d", "post_json_data_path", return_json_path
            ]

    log.debug(args)

    # start standalone pyblish qml
    execute([
        sys.executable, "-u"
    ] + args,
        cwd=cwd
    )

    return {"return_json_path": return_json_path}


@pico.expose()
def context(project, asset, task, app):
    # http://localhost:4242/pipeline/context?project=this&asset=shot01&task=comp

    os.environ["AVALON_PROJECT"] = project
    SESSION["AVALON_PROJECT"] = project

    avalon.update_current_task(task, asset, app)

    project_code = pype.get_project()["data"].get("code", '')

    os.environ["AVALON_PROJECTCODE"] = project_code
    SESSION["AVALON_PROJECTCODE"] = project_code

    hierarchy = pype.get_hierarchy()
    pype.set_hierarchy(hierarchy)
    fix_paths = {k: v.replace("\\", "/") for k, v in SESSION.items()
                 if isinstance(v, str)}
    SESSION.update(fix_paths)
    SESSION.update({"AVALON_HIERARCHY": hierarchy,
                    "AVALON_PROJECTCODE": project_code,
                    "current_dir": os.getcwd().replace("\\", "/")
                    })

    return SESSION


@pico.expose()
def deregister_plugin_path():
    if os.getenv("PUBLISH_PATH", None):
        aport_plugin_path = [p.replace("\\", "/") for p in os.environ["PUBLISH_PATH"].split(
            os.pathsep) if "aport" in p][0]
        os.environ["PUBLISH_PATH"] = aport_plugin_path
    else:
        log.warning("deregister_plugin_path(): No PUBLISH_PATH is registred")

    return "Publish path deregistered"


@pico.expose()
def register_plugin_path(publish_path):
    deregister_plugin_path()
    if os.getenv("PUBLISH_PATH", None):
        os.environ["PUBLISH_PATH"] = os.pathsep.join(
            os.environ["PUBLISH_PATH"].split(os.pathsep) +
            [publish_path.replace("\\", "/")]
        )
    else:
        os.environ["PUBLISH_PATH"] = publish_path

    log.info(os.environ["PUBLISH_PATH"].split(os.pathsep))

    return "Publish registered paths: {}".format(
        os.environ["PUBLISH_PATH"].split(os.pathsep)
    )


@pico.expose()
def nuke_test():
    import nuke
    n = nuke.createNode("Constant")
    log.info(n)


@pico.expose()
def hello(who='world'):
    return 'Hello %s' % who


@pico.expose()
def multiply(x, y):
    return x * y


@pico.expose()
def fail():
    raise Exception('fail!')


@pico.expose()
def make_coffee():
    raise ImATeapot()


@pico.expose()
def upload(upload, filename):
    if not filename.endswith('.txt'):
        raise BadRequest('Upload must be a .txt file!')
    return upload.read().decode()


@pico.expose()
@request_args(ip='remote_addr')
def my_ip(ip):
    return ip


@pico.expose()
@request_args(ip=lambda req: req.remote_addr)
def my_ip3(ip):
    return ip


@pico.prehandle()
def set_user(request, kwargs):
    if request.authorization:
        if request.authorization.password != 'secret':
            raise Unauthorized('Incorrect username or password')
        request.user = request.authorization.username
    else:
        request.user = None


@pico.expose()
@request_args(username='user')
def current_user(username):
    return username


@pico.expose()
@request_args(session=cookie('session_id'))
def session_id(session):
    return session


@pico.expose()
@set_cookie()
def start_session():
    return {'session_id': '42'}


@pico.expose()
@delete_cookie('session_id')
def end_session():
    return True


@pico.expose()
@request_args(session=header('x-session-id'))
def session_id2(session):
    return session


@pico.expose()
@stream()
def countdown(n=10):
    for i in reversed(range(n)):
        yield '%i' % i
        time.sleep(0.5)


@pico.expose()
def user_description(user):
    return '{name} is a {occupation} aged {age}'.format(**user)


@pico.expose()
def show_source():
    return open(__file__.replace('.pyc', '.py')).read()


app = PicoApp()
app.register_module(__name__)

# remove all Handlers created by pico
for name, handler in [(handler.get_name(), handler)
                      for handler in Logger().logging.root.handlers[:]]:
    if "pype" not in str(name).lower():
        print(name)
        print(handler)
        Logger().logging.root.removeHandler(handler)
