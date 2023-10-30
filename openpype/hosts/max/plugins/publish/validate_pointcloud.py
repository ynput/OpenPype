import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidatePointCloud(pyblish.api.InstancePlugin):
    """Validate that work file was saved."""

    order = pyblish.api.ValidatorOrder
    families = ["pointcloud"]
    hosts = ["max"]
    label = "Validate Point Cloud"

    def process(self, instance):
        """
        Notes:
            1. Validate if the export mode of Export Particle is at PRT format
            2. Validate the partition count and range set as default value
                Partition Count : 100
                Partition Range : 1 to 1
            3. Validate if the custom attribute(s) exist as parameter(s)
                of export_particle operator

        """
        report = []

        if self.validate_export_mode(instance):
            report.append("The export mode is not at PRT")

        if self.validate_partition_value(instance):
            report.append(("tyFlow Partition setting is "
                           "not at the default value"))

        invalid_attribute = self.validate_custom_attribute(instance)
        if invalid_attribute:
            report.append(("Custom Attribute not found "
                           f":{invalid_attribute}"))

        if report:
            raise PublishValidationError(f"{report}")

    def validate_custom_attribute(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info(
            f"Validating tyFlow custom attributes for {container}")

        selection_list = instance.data["members"]

        project_settings = instance.context.data["project_settings"]
        attr_settings = project_settings["max"]["PointCloud"]["attribute"]
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.GetSubAnim(obj, anim_name)
                if rt.IsProperty(sub_anim, "Export_Particles"):
                    event_name = sub_anim.name
                    opt = "${0}.{1}.export_particles".format(sel.name,
                                                             event_name)
                    for key, value in attr_settings.items():
                        custom_attr = "{0}.PRTChannels_{1}".format(opt,
                                                                   value)
                        try:
                            rt.Execute(custom_attr)
                        except RuntimeError:
                            invalid.append(key)

        return invalid

    def validate_partition_value(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info(
            f"Validating tyFlow partition value for {container}")

        selection_list = instance.data["members"]
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.GetSubAnim(obj, anim_name)
                if rt.IsProperty(sub_anim, "Export_Particles"):
                    event_name = sub_anim.name
                    opt = "${0}.{1}.export_particles".format(sel.name,
                                                             event_name)
                    count = rt.Execute(f'{opt}.PRTPartitionsCount')
                    if count != 100:
                        invalid.append(count)
                    start = rt.Execute(f'{opt}.PRTPartitionsFrom')
                    if start != 1:
                        invalid.append(start)
                    end = rt.Execute(f'{opt}.PRTPartitionsTo')
                    if end != 1:
                        invalid.append(end)

        return invalid

    def validate_export_mode(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info(
            f"Validating tyFlow export mode for {container}")

        con = rt.GetNodeByName(container)
        selection_list = list(con.Children)
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.GetSubAnim(obj, anim_name)
                # check if there is export particle operator
                boolean = rt.IsProperty(sub_anim, "Export_Particles")
                event_name = sub_anim.name
                if boolean:
                    opt = f"${sel.name}.{event_name}.export_particles"
                    export_mode = rt.Execute(f'{opt}.exportMode')
                    if export_mode != 1:
                        invalid.append(export_mode)

        return invalid
