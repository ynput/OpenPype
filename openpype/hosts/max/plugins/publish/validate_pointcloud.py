import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidatePointCloud(pyblish.api.InstancePlugin):
    """Validate that workfile was saved."""

    order = pyblish.api.ValidatorOrder
    families = ["pointcloud"]
    hosts = ["max"]
    label = "Validate Point Cloud"

    def process(self, instance):
        """
        Notes:

            1. Validate the container only include tyFlow objects
            2. Validate if tyFlow operator Export Particle exists
            3. Validate if the export mode of Export Particle is at PRT format
            4. Validate the partition count and range set as default value
                Partition Count : 100
                Partition Range : 1 to 1
            5. Validate if the custom attribute(s) exist as parameter(s)
                of export_particle operator

        """
        invalid = self.get_tyFlow_object(instance)
        if invalid:
            raise PublishValidationError("Non tyFlow object "
                                         "found: {}".format(invalid))
        invalid = self.get_tyFlow_operator(instance)
        if invalid:
            raise PublishValidationError("tyFlow ExportParticle operator "
                                         "not found: {}".format(invalid))

        invalid = self.validate_export_mode(instance)
        if invalid:
            raise PublishValidationError("The export mode is not at PRT")

        invalid = self.validate_partition_value(instance)
        if invalid:
            raise PublishValidationError("tyFlow Partition setting is "
                                         "not at the default value")
        invalid = self.validate_custom_attribute(instance)
        if invalid:
            raise PublishValidationError("Custom Attribute not found "
                                         ":{}".format(invalid))

    def get_tyFlow_object(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info("Validating tyFlow container "
                      "for {}".format(container))

        con = rt.getNodeByName(container)
        selection_list = list(con.Children)
        for sel in selection_list:
            sel_tmp = str(sel)
            if rt.classOf(sel) in [rt.tyFlow,
                                   rt.Editable_Mesh]:
                if "tyFlow" not in sel_tmp:
                    invalid.append(sel)
            else:
                invalid.append(sel)

        return invalid

    def get_tyFlow_operator(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info("Validating tyFlow object "
                      "for {}".format(container))

        con = rt.getNodeByName(container)
        selection_list = list(con.Children)
        bool_list = []
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.getsubanimnames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.getsubanim(obj, anim_name)
                # check if there is export particle operator
                boolean = rt.isProperty(sub_anim, "Export_Particles")
                bool_list.append(str(boolean))
            # if the export_particles property is not there
            # it means there is not a "Export Particle" operator
            if "True" not in bool_list:
                self.log.error("Operator 'Export Particles' not found!")
                invalid.append(sel)

        return invalid

    def validate_custom_attribute(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info("Validating tyFlow custom "
                      "attributes for {}".format(container))

        project_setting = instance.context.data["project_settings"]
        point_cloud_settings = project_setting["max"]["PointCloud"]

        con = rt.getNodeByName(container)
        selection_list = list(con.Children)
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.getsubanimnames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.getsubanim(obj, anim_name)
                # check if there is export particle operator
                boolean = rt.isProperty(sub_anim, "Export_Particles")
                event_name = sub_anim.name
                if boolean:
                    opt = "${0}.{1}.export_particles".format(sel.name,
                                                             event_name)
                    attributes = point_cloud_settings["attribute"]
                    for key, value in attributes.items():
                        custom_attr = "{0}.PRTChannels_{1}".format(opt,
                                                                   value)
                        try:
                            rt.execute(custom_attr)
                        except RuntimeError:
                            invalid.add(key)

        return invalid

    def validate_partition_value(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info("Validating tyFlow partition "
                      "value for {}".format(container))

        con = rt.getNodeByName(container)
        selection_list = list(con.Children)
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.getsubanimnames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.getsubanim(obj, anim_name)
                # check if there is export particle operator
                boolean = rt.isProperty(sub_anim, "Export_Particles")
                event_name = sub_anim.name
                if boolean:
                    opt = "${0}.{1}.export_particles".format(sel.name,
                                                             event_name)
                    count = rt.execute(f'{opt}.PRTPartitionsCount')
                    if count != 100:
                        invalid.append(count)
                    start = rt.execute(f'{opt}.PRTPartitionsFrom')
                    if start != 1:
                        invalid.append(start)
                    end = rt.execute(f'{opt}.PRTPartitionsTo')
                    if end != 1:
                        invalid.append(end)

        return invalid

    def validate_export_mode(self, instance):
        invalid = []
        container = instance.data["instance_node"]
        self.log.info("Validating tyFlow export "
                      "mode for {}".format(container))

        con = rt.getNodeByName(container)
        selection_list = list(con.Children)
        for sel in selection_list:
            obj = sel.baseobject
            anim_names = rt.getsubanimnames(obj)
            for anim_name in anim_names:
                # get all the names of the related tyFlow nodes
                sub_anim = rt.getsubanim(obj, anim_name)
                # check if there is export particle operator
                boolean = rt.isProperty(sub_anim, "Export_Particles")
                event_name = sub_anim.name
                if boolean:
                    opt = "${0}.{1}.export_particles".format(sel.name,
                                                             event_name)
                    export_mode = rt.execute(f'{opt}.exportMode')
                    if export_mode != 1:
                        invalid.append(export_mode)

        return invalid
