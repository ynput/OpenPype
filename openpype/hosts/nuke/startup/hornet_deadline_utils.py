import json
import os
from openpype.modules.deadline.deadline_module import DeadlineModule
from openpype.modules import ModulesManager
import getpass

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
        output = json.loads(CallDeadlineCommand([ "-prettyJSON", "-GetSubmissionInfo", "Pools", "Groups", "MaxPriority", "UserHomeDir", "RepoDir:submission/Nuke/Main", "RepoDir:submission/Integration/Main", ])) # type: Dict
    except Exception as e:
        print("Failed to get submitter info: {}".format(e))


def getNodeSubmissionInfo():
    nde = nuke.thisNode()
    relevant_knobs = ['file','deadlinePool','deadlineGroup','deadlinePriority','first','last']
    submission_info = { knob: nde.knob(kname).value() for kname in relevant_knobs }

def deadlineNetworkSubmit(dev=False):
    modules = ModulesManager()
    deadline_module = modules.modules_by_name["deadline"]
    deadline_server = deadline_module.deadline_urls["default"] if not dev else deadline_module.deadline_urls["dev"]
    deadline_url = "{}/api/jobs".format(deadline_server)

    deadline_user = getpass.getuser()

def build_request(knobValues):
    payload = {
                "JobInfo": {
                    # Top-level group name
                    # Job name, as seen in Monitor
                    "Name": nuke.scriptName(),
                    # Arbitrary username, for visualisation in Monitor
                    "UserName": knobValues['deadline_user'],
                    # "InitialStatus":suspended, # NOTE hornet update on use existing frames on farm
                    "Priority": knobValues['deadlinePriority'],

                    "Pool": instance.data.get("primaryPool") or "local",
                    "SecondaryPool": "",
                    "Group": knobValues['deadlineGroup'],
                    "Plugin": 'Nuke',
                    "Frames": "{start}-{end}".format(
                        start=knobValues['first'],
                        end=knobValues['last']
                    ),
                    # Optional, enable double-click to preview rendered
                    # frames from Deadline Monitor
                    "OutputFilename0": str(output_filename_0).replace("\\", "/"),
                    # limiting groups
                    "LimitGroups": ",".join(limit_groups)
                },
                "PluginInfo": {
                    # Input
                    "SceneFile": nuke.scriptName().replace("\\", "/"),
                    # Output directory and filename
                    "OutputFilePath": render_dir.replace("\\", "/"),
                    # "OutputFilePrefix": render_variables["filename_prefix"],
                    # Mandatory for Deadline
                    "Version": nuke.NUKE_VERSION_STRING,
                    # Resolve relative references
                    "ProjectPath": script_path,
                    # using GPU by default
                    # Only the specific write node is rendered.
                    "WriteNode": nuke.thisNode().name(),
                },
                # Mandatory for Deadline, may be empty
                "AuxFiles": []
            }
