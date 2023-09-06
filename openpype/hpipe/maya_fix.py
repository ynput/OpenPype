import os
from openpype.settings import get_project_settings
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def fix_workspace():
    """
     Hornet fix for openpype to load the workspace.mel from the project settings.
    """
    project_settings = get_project_settings(os.environ['AVALON_PROJECT'])
    if project_settings.get('maya'):
        log.info("Hornet hotfix for workspace...")
        from maya import mel
        from maya import cmds
        mel_workspace = project_settings.get('maya')['mel_workspace']
        mel.eval(mel_workspace)
        cmds.workspace( s=True )
