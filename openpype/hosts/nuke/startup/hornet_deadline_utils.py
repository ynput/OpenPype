import json
import os
from openpype.modules.deadline.deadline_module import DeadlineModule
from openpype.modules import ModulesManager
import getpass
import nuke
import requests
from datetime import datetime
tempRenderTemplate = "{work}/renders/nuke/{subset}"
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
    relevant_knobs = ['File output','deadlinePool','deadlineGroup','deadlinePriority','first','last']
    all_knobs = nde.allKnobs()
    return { knb.name(): knb.value() for knb in all_knobs if knb.name() in relevant_knobs }

def deadlineNetworkSubmit(dev=False):
    tempRenderPath = tempRenderTemplate.format(work=os.environ["AVALON_WORKDIR"], subset=nuke.thisNode().name())
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nuke.scriptSaveToTemp("{path}/{name}_{time}.nk".format(path=tempRenderPath,
                                                           name=os.path.splitext(os.path.basename(nuke.root().name()))[0],
                                                           time=timestamp))
    modules = ModulesManager()
    deadline_module = modules.modules_by_name["deadline"]
    deadline_server = deadline_module.deadline_urls["default"] if not dev else deadline_module.deadline_urls["dev"]
    deadline_url = "{}/api/jobs".format(deadline_server)
    body = build_request(getNodeSubmissionInfo(),timestamp)
    response = requests.post(deadline_url, json=body, timeout=10)
    if not response.ok:
        raise Exception(response.text)
    print(response)


def build_request(knobValues,timestamp):
    # Include critical environment variables with submission
    return {
                "JobInfo": {
                    # Job name, as seen in Monitor
                    "Name": os.environ['AVALON_PROJECT'].split("_")[0] + "_" + os.environ['AVALON_ASSET'] + '_' + nuke.thisNode().name(),
                    # pass submitter user
                    "UserName": getpass.getuser(),
                    "Priority": knobValues.get('deadlinePriority') or 50,
                    "Pool": knobValues.get("deadlinePool") or "local",
                    "SecondaryPool": "",
                    "Group": knobValues.get('deadlineGroup') or 'nuke',
                    "Plugin": 'Nuke',
                    "Frames": "{start}-{end}".format(
                        start=knobValues['first'] or 1001,
                        end=knobValues['last'] or 1001
                    ),
                    # Optional, enable double-click to preview rendered
                    # frames from Deadline Monitor
                    #"OutputFilename0": str(output_filename_0).replace("\\", "/"),
                    # limiting groups
                    "LimitGroups": ''
                },
                "PluginInfo": {
                    # Input
                    "SceneFile": (nuke.script_directory() + "{}_{}.nk".format(nuke.root().name(), timestamp)).replace("\\", "/"),
                    # Output directory and filename
                    "OutputFilePath": knobValues['File output'].replace("\\", "/"),
                    # "OutputFilePrefix": render_variables["filename_prefix"],
                    # Mandatory for Deadline
                    "Version": nuke.NUKE_VERSION_STRING,
                    # Resolve relative references
                    "ProjectPath": nuke.script_directory().replace("\\", "/"),
                    # using GPU by default
                    # Only the specific write node is rendered.
                    "WriteNode": nuke.thisNode().name(),
                },
                # Mandatory for Deadline, may be empty
                "AuxFiles": []
            }
