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

        """
        invalid = self.get_tyFlow_object(instance)
        if invalid:
            raise PublishValidationError("Non tyFlow object "
                                         "found: {}".format(invalid))
        invalid = self.get_tyFlow_operator(instance)
        if invalid:
            raise PublishValidationError("tyFlow ExportParticle operator "
                                         "not found: {}".format(invalid))

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
