import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.pipeline import publish


class ExtractPointCloud(publish.Extractor):
    """
    Extract PRT format with tyFlow operators.

    Notes:
        Currently only works for the default partition setting

    Args:
        self.export_particle(): sets up all job arguments for attributes
            to be exported in MAXscript

        self.get_operators(): get the export_particle operator

        self.get_custom_attr(): get all custom channel attributes from Openpype
            setting and sets it as job arguments before exporting

        self.get_files(): get the files with tyFlow naming convention
            before publishing

        self.partition_output_name(): get the naming with partition settings.

        self.get_partition(): get partition value

    """

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract Point Cloud"
    hosts = ["max"]
    families = ["pointcloud"]
    settings = []

    def process(self, instance):
        self.settings = self.get_setting(instance)
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]
        self.log.info("Extracting PRT...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.prt".format(**instance.data)
        path = os.path.join(stagingdir, filename)

        with maintained_selection():
            job_args = self.export_particle(instance.data["members"],
                                            start,
                                            end,
                                            path)

            for job in job_args:
                rt.Execute(job)

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        self.log.info("Writing PRT with TyFlow Plugin...")
        filenames = self.get_files(
            instance.data["members"], path, start, end)
        self.log.debug(f"filenames: {filenames}")

        partition = self.partition_output_name(
            instance.data["members"])

        representation = {
            'name': 'prt',
            'ext': 'prt',
            'files': filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": stagingdir,
            "outputName": partition         # partition value
        }
        instance.data["representations"].append(representation)
        self.log.info(f"Extracted instance '{instance.name}' to: {path}")

    def export_particle(self,
                        members,
                        start,
                        end,
                        filepath):
        """Sets up all job arguments for attributes.

        Those attributes are to be exported in MAX Script.

        Args:
            members (list): Member nodes of the instance.
            start (int): Start frame.
            end (int): End frame.
            filepath (str): Path to PRT file.

        Returns:
            list of arguments for MAX Script.

        """
        job_args = []
        opt_list = self.get_operators(members)
        for operator in opt_list:
            start_frame = f"{operator}.frameStart={start}"
            job_args.append(start_frame)
            end_frame = f"{operator}.frameEnd={end}"
            job_args.append(end_frame)
            filepath = filepath.replace("\\", "/")
            prt_filename = f'{operator}.PRTFilename="{filepath}"'
            job_args.append(prt_filename)
            # Partition
            mode = f"{operator}.PRTPartitionsMode=2"
            job_args.append(mode)

            additional_args = self.get_custom_attr(operator)
            job_args.extend(iter(additional_args))
            prt_export = f"{operator}.exportPRT()"
            job_args.append(prt_export)

        return job_args

    @staticmethod
    def get_operators(members):
        """Get Export Particles Operator.

        Args:
            members (list): Instance members.

        Returns:
            list of particle operators

        """
        opt_list = []
        for member in members:
            obj = member.baseobject
        # TODO: to see if it can be used maxscript instead
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                sub_anim = rt.GetSubAnim(obj, anim_name)
                boolean = rt.IsProperty(sub_anim, "Export_Particles")
                if boolean:
                        event_name = sub_anim.Name
                        opt = f"${member.Name}.{event_name}.export_particles"
                        opt_list.append(opt)

        return opt_list

    @staticmethod
    def get_setting(instance):
        project_setting = instance.context.data["project_settings"]
        return project_setting["max"]["PointCloud"]

    def get_custom_attr(self, operator):
        """Get Custom Attributes"""

        custom_attr_list = []
        attr_settings = self.settings["attribute"]
        for key, value in attr_settings.items():
            custom_attr = "{0}.PRTChannels_{1}=True".format(operator,
                                                            value)
            self.log.debug(
                "{0} will be added as custom attribute".format(key)
            )
            custom_attr_list.append(custom_attr)

        return custom_attr_list

    def get_files(self,
                  container,
                  path,
                  start_frame,
                  end_frame):
        """Get file names for tyFlow.

        Set the filenames accordingly to the tyFlow file
        naming extension for the publishing purpose

        Actual File Output from tyFlow::
            <SceneFile>__part<PartitionStart>of<PartitionCount>.<frame>.prt

            e.g. tyFlow_cloth_CCCS_blobbyFill_001__part1of1_00004.prt

        Args:
            container: Instance node.
            path (str): Output directory.
            start_frame (int): Start frame.
            end_frame (int): End frame.

        Returns:
            list of filenames

        """
        filenames = []
        filename = os.path.basename(path)
        orig_name, ext = os.path.splitext(filename)
        partition_count, partition_start = self.get_partition(container)
        for frame in range(int(start_frame), int(end_frame) + 1):
            actual_name = "{}__part{:03}of{}_{:05}".format(orig_name,
                                                           partition_start,
                                                           partition_count,
                                                           frame)
            actual_filename = path.replace(orig_name, actual_name)
            filenames.append(os.path.basename(actual_filename))

        return filenames

    def partition_output_name(self, container):
        """Get partition output name.

        Partition output name set for mapping
        the published file output.

        Todo:
            Customizes the setting for the output.

        Args:
            container: Instance node.

        Returns:
            str: Partition name.

        """
        partition_count, partition_start = self.get_partition(container)
        return f"_part{partition_start:03}of{partition_count}"

    def get_partition(self, container):
        """Get Partition value.

        Args:
            container: Instance node.

        """
        opt_list = self.get_operators(container)
        # TODO: This looks strange? Iterating over
        #   the opt_list but returning from inside?
        for operator in opt_list:
            count = rt.Execute(f'{operator}.PRTPartitionsCount')
            start = rt.Execute(f'{operator}.PRTPartitionsFrom')

            return count, start
