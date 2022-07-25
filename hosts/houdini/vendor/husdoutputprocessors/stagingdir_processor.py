import hou
import husdoutputprocessors.base as base
import os


class StagingDirOutputProcessor(base.OutputProcessorBase):
    """Output all USD Rop file nodes into the Staging Directory

    Ignore any folders and paths set in the Configured Layers
    and USD Rop node, just take the filename and save into a
    single directory.

    """
    theParameters = None
    parameter_prefix = "stagingdiroutputprocessor_"
    stagingdir_parm_name = parameter_prefix + "stagingDir"

    def __init__(self):
        self.staging_dir = None

    def displayName(self):
        return 'StagingDir Output Processor'

    def parameters(self):
        if not self.theParameters:
            parameters = hou.ParmTemplateGroup()
            rootdirparm = hou.StringParmTemplate(
                self.stagingdir_parm_name,
                'Staging Directory', 1,
                string_type=hou.stringParmType.FileReference,
                file_type=hou.fileType.Directory
            )
            parameters.append(rootdirparm)
            self.theParameters = parameters.asDialogScript()
        return self.theParameters

    def beginSave(self, config_node, t):

        # Use the Root Directory parameter if it is set.
        root_dir_parm = config_node.parm(self.stagingdir_parm_name)
        if root_dir_parm:
            self.staging_dir = root_dir_parm.evalAtTime(t)

        if not self.staging_dir:
            out_file_parm = config_node.parm('lopoutput')
            if out_file_parm:
                self.staging_dir = out_file_parm.evalAtTime(t)
            if self.staging_dir:
                (self.staging_dir, filename) = os.path.split(self.staging_dir)

    def endSave(self):
        self.staging_dir = None

    def processAsset(self, asset_path,
            asset_path_for_save,
            referencing_layer_path,
            asset_is_layer,
            for_save):
        """
        Args:
            asset_path (str): The incoming file path you want to alter or not.
            asset_path_for_save (bool): Whether the current path is a
                referenced path in the USD file. When True, return the path
                you want inside USD file.
            referencing_layer_path (str): ???
            asset_is_layer (bool): Whether this asset is a USD layer file.
                If this is False, the asset is something else (for example,
                a texture or volume file).
            for_save (bool): Whether the asset path is for a file to be saved
                out. If so, then return actual written filepath.

        Returns:
            The refactored asset path.

        """

        # Treat save paths as being relative to the output path.
        if for_save and self.staging_dir:
            # Whenever we're processing a Save Path make sure to
            # resolve it to the Staging Directory
            filename = os.path.basename(asset_path)
            return os.path.join(self.staging_dir, filename)

        return asset_path


output_processor = StagingDirOutputProcessor()
def usdOutputProcessor():
    return output_processor

