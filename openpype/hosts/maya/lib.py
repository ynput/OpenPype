import os
from openpype.settings import get_project_settings
from openpype.lib import Logger


def create_workspace_mel(workdir, project_name, project_settings=None):
    dst_filepath = os.path.join(workdir, "workspace.mel")
    if os.path.exists(dst_filepath):
        return

    if not os.path.exists(workdir):
        os.makedirs(workdir)

    if not project_settings:
        project_settings = get_project_settings(project_name)
    mel_script = project_settings["maya"].get("mel_workspace")

    # Skip if mel script in settings is empty
    if not mel_script:
        log = Logger.get_logger("create_workspace_mel")
        log.debug("File 'workspace.mel' not created. Settings value is empty.")
        return

    with open(dst_filepath, "w") as mel_file:
        mel_file.write(mel_script)
