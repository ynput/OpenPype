import os
import shutil

from openpype.settings import get_current_project_settings

def load_workspace_mel(workdir):
    dst_filepath = os.path.join(workdir, "workspace.mel")
    if os.path.exists(dst_filepath):
        return

    if not os.path.exists(workdir):
        os.makedirs(workdir)

    with open(dst_filepath, "w") as mel_file:
        setting = get_current_project_settings()
        mel_script = setting["maya"]["mel-workspace"]["definition"]
        for mel in mel_script:
            mel_file.write(mel)
            mel_file.write("\n")
