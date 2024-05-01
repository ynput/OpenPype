import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.pipeline import publish


class ExtractTyCache(publish.Extractor):
    """Extract tycache format with tyFlow operators.
    Notes:
        - TyCache only works for TyFlow Pro Plugin.

    Methods:
        self._extract_tyflow_particles: sets the necessary
            attributes and export tyCache with the export
            particle operator(s)

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
        material_cache = instance.data.get("material_cache", True)
        operator = instance.data["operator"]
        representations = instance.data.setdefault("representations", [])
        start_frame = instance.data["frameStartHandle"]
        end_frame = instance.data["frameEndHandle"]
        name = instance.data.get("productName")
        tyc_fnames = []
        tyc_mesh_fnames = []
        with maintained_selection():
            filename = f"{instance.name}_{name}.tyc"
            path = os.path.join(stagingdir, filename)
            filenames = self.get_files(
                instance, name, start_frame, end_frame)
            self._extract_tyflow_particles(
                operator, path, export_mode, material_cache)
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
        # Get the material filename of which assigned in
        # tyCache for extraction
        material_filename = f"{instance.name}__tyMtl.mat"
        full_material_name = os.path.join(stagingdir, material_filename)
        full_material_name = full_material_name.replace("\\", "/")
        if material_cache and os.path.exists(full_material_name):
            mateiral_repres = {
                "name": 'tyMtl',
                "ext": 'mat',
                'files': material_filename,
                'stagingDir': stagingdir,
                "outputName": '__tyMtl'
            }
            representations.append(mateiral_repres)
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

    def _extract_tyflow_particles(self, operator, filepath,
                                  export_mode, material_cache):
        """Exports tyCache particle with the necessary export settings

        Args:
            operators (list): List of Export Particle operator
            start (int): Start frame.
            end (int): End frame.
            filepath (str): Output path of the TyCache file.
            export_mode (int): Export Mode for the TyCache Output.
            material_cache (bool): Whether tycache should publish
                along with material

        """
        if rt.getProperty(operator, "exportMode") != export_mode:
            return
        export_settings = {
            "tycacheCreateObject": False,
            "tycacheCreateObjectIfNotCreated": False,
            "tycacheChanMaterials": True if material_cache else False,
            "tyCacheFilename": filepath.replace("\\", "/"),
        }

        for key, value in export_settings.items():
            rt.setProperty(operator, key, value)
        # export tyCache
        operator.ExportTyCache()
