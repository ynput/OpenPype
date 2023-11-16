import json
import os
from openpype.modules.deadline.deadline_module import DeadlineModule
from openpype.modules import ModulesManager
import getpass
import nuke
import requests
from datetime import datetime
## copied from submit_nuke_to_deadline.py
def GetDeadlineCommand():
    # type: () -> str
    deadlineBin = "" # type: str
    try:
        deadlineBin = os.environ['DEADLINE_PATH']
    except KeyError:
        #if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
        pass

    # On OSX, we look for the DEADLINE_PATH file if the environment variable does not exist.
    if deadlineBin == "" and  os.path.exists("/Users/Shared/Thinkbox/DEADLINE_PATH"):
        with open("/Users/Shared/Thinkbox/DEADLINE_PATH") as f:
            deadlineBin = f.read().strip()

    deadlineCommand = os.path.join(deadlineBin, "deadlinecommand") # type: str

    return deadlineCommand

def CallDeadlineCommand(arguments, hideWindow=True):
    # type: (List[str], bool) -> str
    deadlineCommand = GetDeadlineCommand() # type: str

    startupinfo = None # type: ignore # this is only a windows option
    if hideWindow and os.name == 'nt':
        # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
        if hasattr(subprocess, '_subprocess') and hasattr(subprocess._subprocess, 'STARTF_USESHOWWINDOW'): # type: ignore # this is only a windows option
            startupinfo = subprocess.STARTUPINFO() # type: ignore # this is only a windows option
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW # type: ignore # this is only a windows option
        elif hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo = subprocess.STARTUPINFO() # type: ignore # this is only a windows option
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore # this is only a windows option

    environment = {} # type: Dict[str, str]
    for key in os.environ.keys():
        environment[key] = str(os.environ[key])

    if os.name == 'nt':
        deadlineCommandDir = os.path.dirname(deadlineCommand)
        if not deadlineCommandDir == "" :
            environment['PATH'] = deadlineCommandDir + os.pathsep + os.environ['PATH']

    arguments.insert(0, deadlineCommand)
    output = "" # type: Union[bytes, str]

    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, env=environment)
    output, errors = proc.communicate()

    if sys.version_info[0] > 2 and type(output) is bytes:
        output = output.decode()

    return output # type: ignore


## END copied from submit_nuke_to_deadline.py

def getSubmitterInfo():
    try:
        return json.loads(CallDeadlineCommand([ "-prettyJSON", "-GetSubmissionInfo", "Pools", "Groups", "MaxPriority", "UserHomeDir", "RepoDir:submission/Nuke/Main", "RepoDir:submission/Integration/Main", ])) # type: Dict
    except Exception as e:
        print("Failed to get submitter info: {}".format(e))


def getNodeSubmissionInfo():
    nde = nuke.thisNode()
    inside_write = nuke.toNode('inside_' + nde.name())
    relevant_knobs = ['File output','deadlinePool','deadlineGroup','deadlinePriority']
    relevant_inside_knobs = ['first', 'last']
    all_knobs = nde.allKnobs()
    knob_values = { knb.name(): knb.value() for knb in all_knobs if knb.name() in relevant_knobs }
    knob_values['first'] = inside_write.knob('first').value()
    knob_values['last'] = inside_write.knob('last').value()
    return knob_values

def deadlineNetworkSubmit(dev=False):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not os.path.exists(os.path.join(os.environ['AVALON_WORKDIR'], "submission")):
        os.mkdir(os.path.join(os.environ['AVALON_WORKDIR'], "submission"))
    nuke.scriptSaveToTemp("{path}/submission/{name}_{time}.nk".format(path=os.environ['AVALON_WORKDIR'],
                                                           name=os.path.splitext(os.path.basename(nuke.root().name()))[0],
                                                           time=timestamp))
    modules = ModulesManager()
    deadline_module = modules.modules_by_name["deadline"]
    deadline_server = deadline_module.deadline_urls["default"] if not dev else deadline_module.deadline_urls["dev"]
    deadline_url = "{}/api/jobs".format(deadline_server)
    body = build_request(getNodeSubmissionInfo(),timestamp)
    response = requests.post(deadline_url, json=body, timeout=10)
    if not response.ok:
        nuke.alert("Failed to submit to Deadline: {}".format(response.text))
        raise Exception(response.text)
    else:
        nuke.alert("Submitted to Deadline Sucessfully")


def build_request(knobValues,timestamp):
    # Include critical environment variables with submission
    submissionEnvVars = ['HORNET_ROOT', 'NUKE_PATH', 'OCIO', 'OPTICAL_FLARES_PATH', 'peregrinel_LICENSE', 'OFX_PLUGIN_PATH', 'RVL_SERVER', 'neatlab_LICENSE']
    environment = dict({k: os.environ[k] for k in submissionEnvVars if k in os.environ.keys()})
    body = {
                "JobInfo": {
                    # Job name, as seen in Monitor
                    "Name": os.environ['AVALON_PROJECT'].split("_")[0] + "_" + os.environ['AVALON_ASSET'] + '_' + nuke.thisNode().name(),
                    # pass submitter user
                    "UserName": getpass.getuser(),
                    "Priority": int(knobValues.get('deadlinePriority')) or 90,
                    "Pool": knobValues.get('deadlinePool') or "local",
                    "SecondaryPool": '',
                    "Group": knobValues.get('deadlineGroup') or 'nuke',
                    "Plugin": 'Nuke',
                    "Frames": "{start}-{end}".format(
                        start=int(knobValues['first']) or nuke.root().firstFrame(),
                        end=int(knobValues['last']) or nuke.root().lastFrame()
                    ),
                    # Optional, enable double-click to preview rendered
                    # frames from Deadline Monitor
                    #"OutputFilename0": str(output_filename_0).replace("\\", "/"),
                    # limiting groups
                    "ChunkSize": int(knobValues.get('deadlineChunkSize',1)) or 1,
                    "LimitGroups": ''
                },
                "PluginInfo": {
                    # Input
                    "SceneFile": (nuke.script_directory() + "/submission/{}_{}.nk".format(os.path.splitext(os.path.basename(nuke.root().name()))[0], timestamp)).replace("\\", "/"),
                    # Output directory and filename
                    "OutputFilePath": knobValues['File output'].replace("\\", "/"),
                    # "OutputFilePrefix": render_variables["filename_prefix"],
                    # Mandatory for Deadline
                    "Version": str(nuke.NUKE_VERSION_MAJOR) + "." + str(nuke.NUKE_VERSION_MINOR),
                    # Resolve relative references
                    "ProjectPath": nuke.script_directory().replace("\\", "/"),
                    # using GPU by default
                    # Only the specific write node is rendered.
                    "WriteNode": nuke.thisNode().name(),
                },
                # Mandatory for Deadline, may be empty
                "AuxFiles": []
            }
    body["JobInfo"].update({
        "EnvironmentKeyValue%d" % index: "{key}={value}".format(
        key=key,
        value=str(environment[key])
            ) for index, key in enumerate(environment)})
    return body
