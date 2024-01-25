import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.hosts.max.api.lib import get_tyflow_export_particle_operators
from openpype.pipeline import publish


class ExtractTyCache(publish.Extractor):
    """Extract tycache format with tyFlow operators.
    Notes:
        - TyCache only works for TyFlow Pro Plugin.

    Methods:
        self._extract_tyflow_particles: sets the necessary
            attributes and export tyCache with the export
            particle operator(s)

        self.get_tyflow_export_particle_operators(): get the
            export_particle operator(s)

        self.get_files(): get the files with tyFlow naming convention
            before publishing
    """

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract TyCache"
    hosts = ["max"]
    families = ["tycache", "tyspline"]

    def process(self, instance):
        # TODO: let user decide the param
        self.log.debug("Extracting Tycache...")

        stagingdir = self.staging_dir(instance)

        export_mode = instance.data.get("exportMode", 2)
        members = instance.data["members"]
        representations = instance.data.setdefault("representations", [])
        tyc_fnames = []
        tyc_mesh_fnames = []
        with maintained_selection():
            self.log.debug(get_tyflow_export_particle_operators(members))
            for operators in get_tyflow_export_particle_operators(members):
                operator, start_frame, end_frame, name = operators
                filename = f"{instance.name}_{name}.tyc"
                path = os.path.join(stagingdir, filename)
                filenames = self.get_files(
                    instance, name, start_frame, end_frame)
                self._extract_tyflow_particles(operator, path, export_mode)
                mesh_filename = f"{instance.name}_{name}__tyMesh.tyc"
                tyc_fnames.extend(filenames)
                tyc_mesh_fnames.append(mesh_filename)
        representation = {
            "name": "tyc",
            "ext": "tyc",
            "files": (
                tyc_fnames if len(tyc_fnames) > 1
                else tyc_fnames[0]),
            "stagingDir": stagingdir
        }
        representations.append(representation)
        mesh_repres = {
            'name': 'tyMesh',
            'ext': 'tyc',
            'files': (
                tyc_mesh_fnames if len(tyc_mesh_fnames) > 1
                else tyc_mesh_fnames[0]),
            "stagingDir": stagingdir
        }
        representations.append(mesh_repres)
        self.log.debug(
            f"Extracted instance '{instance.name}' to: {stagingdir}")

    def get_files(self, instance, operator, start_frame, end_frame):
        """Get file names for tyFlow in tyCache format.

        Set the filenames accordingly to the tyCache file
        naming extension(.tyc) for the publishing purpose

        Actual File Output from tyFlow in tyCache format:
        <InstanceName>_<operator>__tyPart_<frame>.tyc

        e.g. tycacheMain__tyPart_00000.tyc

        Args:
            instance (pyblish.api.Instance): instance.

        Returns:
            filenames(list): list of filenames

        """
        filenames = []
        for frame in range(int(start_frame), int(end_frame) + 1):
            filename = f"{instance.name}_{operator}__tyPart_{frame:05}.tyc"
            filenames.append(filename)
        return filenames

    def _extract_tyflow_particles(self, operator, filepath, export_mode):
        """Exports tyCache particle with the necessary export settings

        Args:
            operators (list): List of Export Particle operator
            start (int): Start frame.
            end (int): End frame.
            filepath (str): Output path of the TyCache file.
            export_mode (int): Export Mode for the TyCache Output.

        """
        if rt.getProperty(operator, "exportMode") != export_mode:
            return
        export_settings = {
            "tycacheCreateObject": False,
            "tycacheCreateObjectIfNotCreated": False,
            "tyCacheFilename": filepath.replace("\\", "/"),
        }

        for key, value in export_settings.items():
            rt.setProperty(operator, key, value)
        # export tyCache
        operator.ExportTyCache()
