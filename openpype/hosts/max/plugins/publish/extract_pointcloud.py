import os
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection
)


class ExtractPointCloud(publish.Extractor):
    """
    Extract PRT format with tyFlow operators

    Notes:
        Currently only works for the default partition setting

    Args:
        export_particle(): sets up all job arguments for attributes
        to be exported in MAXscript

        get_operators(): get the export_particle operator

        get_custom_attr(): get all custom channel attributes from Openpype
        setting and sets it as job arguments before exporting

        get_files(): get the files with tyFlow naming convention
        before publishing

        partition_output_name(): get the naming with partition settings.
        get_partition(): get partition value

    """

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract Point Cloud"
    hosts = ["max"]
    families = ["pointcloud"]

    def process(self, instance):
        start = int(instance.context.data.get("frameStart"))
        end = int(instance.context.data.get("frameEnd"))
        project_setting = instance.context.data["project_settings"]
        point_cloud_settings = project_setting["max"]["PointCloud"]
        container = instance.data["instance_node"]
        self.log.info("Extracting PRT...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.prt".format(**instance.data)
        path = os.path.join(stagingdir, filename)

        with maintained_selection():
            job_args = self.export_particle(container,
                                            start,
                                            end,
                                            path,
                                            point_cloud_settings)
            for job in job_args:
                rt.execute(job)

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        self.log.info("Writing PRT with TyFlow Plugin...")
        filenames = self.get_files(container, path, start, end)
        self.log.debug("filenames: {0}".format(filenames))

        partition = self.partition_output_name(container)

        representation = {
            'name': 'prt',
            'ext': 'prt',
            'files': filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": stagingdir,
            "outputName": partition         # partition value
        }
        instance.data["representations"].append(representation)
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          path))

    def export_particle(self,
                        container,
                        start,
                        end,
                        filepath,
                        point_cloud_settings):
        job_args = []
        opt_list = self.get_operators(container)
        for operator in opt_list:
            start_frame = "{0}.frameStart={1}".format(operator,
                                                      start)
            job_args.append(start_frame)
            end_frame = "{0}.frameEnd={1}".format(operator,
                                                  end)
            job_args.append(end_frame)
            filepath = filepath.replace("\\", "/")
            prt_filename = '{0}.PRTFilename="{1}"'.format(operator,
                                                          filepath)

            job_args.append(prt_filename)
            # Partition
            mode = "{0}.PRTPartitionsMode=2".format(operator)
            job_args.append(mode)

            additional_args = self.get_custom_attr(
                operator, point_cloud_settings)
            for args in additional_args:
                job_args.append(args)

            prt_export = "{0}.exportPRT()".format(operator)
            job_args.append(prt_export)

        return job_args

    def get_operators(self, container):
        """Get Export Particles Operator"""

        opt_list = []
        node = rt.getNodebyName(container)
        selection_list = list(node.Children)
        for sel in selection_list:
            obj = sel.baseobject
            # TODO: to see if it can be used maxscript instead
            anim_names = rt.getsubanimnames(obj)
            for anim_name in anim_names:
                sub_anim = rt.getsubanim(obj, anim_name)
                boolean = rt.isProperty(sub_anim, "Export_Particles")
                event_name = sub_anim.name
                if boolean:
                    opt = "${0}.{1}.export_particles".format(sel.name,
                                                             event_name)
                    opt_list.append(opt)

        return opt_list

    def get_custom_attr(self, operator, point_cloud_settings):
        """Get Custom Attributes"""

        custom_attr_list = []
        attr_settings = point_cloud_settings["attribute"]
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
        """
        Note:
            Set the filenames accordingly to the tyFlow file
            naming extension for the publishing purpose

            Actual File Output from tyFlow:
            <SceneFile>__part<PartitionStart>of<PartitionCount>.<frame>.prt
            e.g. tyFlow_cloth_CCCS_blobbyFill_001__part1of1_00004.prt
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
        """
        Notes:
            Partition output name set for mapping
            the published file output

        todo:
            Customizes the setting for the output
        """
        partition_count, partition_start = self.get_partition(container)
        partition = "_part{:03}of{}".format(partition_start,
                                            partition_count)

        return partition

    def get_partition(self, container):
        """
        Get Partition Value
        """
        opt_list = self.get_operators(container)
        for operator in opt_list:
            count = rt.execute(f'{operator}.PRTPartitionsCount')
            start = rt.execute(f'{operator}.PRTPartitionsFrom')

            return count, start
