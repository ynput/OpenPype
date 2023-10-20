import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidateTyFlowData(pyblish.api.InstancePlugin):
    """Validate TyFlow plugins or relevant operators are set correctly."""

    order = pyblish.api.ValidatorOrder
    families = ["pointcloud", "tycache"]
    hosts = ["max"]
    label = "TyFlow Data"

    def process(self, instance):
        """
        Notes:
            1. Validate the container only include tyFlow objects
            2. Validate if tyFlow operator Export Particle exists

        """

        invalid_object = self.get_tyflow_object(instance)
        if invalid_object:
            self.log.error(f"Non tyFlow object found: {invalid_object}")

        invalid_operator = self.get_tyflow_operator(instance)
        if invalid_operator:
            self.log.error(
                "Operator 'Export Particles' not found in tyFlow editor.")
        if invalid_object or invalid_operator:
            raise PublishValidationError(
                "issues occurred",
                description="Container should only include tyFlow object "
                "and tyflow operator 'Export Particle' should be in "
                "the tyFlow editor.")

    def get_tyflow_object(self, instance):
        """Get the nodes which are not tyFlow object(s)
        and editable mesh(es)

        Args:
            instance (pyblish.api.Instance): instance

        Returns:
            list: invalid nodes which are not tyFlow
                object(s) and editable mesh(es).
        """
        container = instance.data["instance_node"]
        self.log.debug(f"Validating tyFlow container for {container}")

        allowed_classes = [rt.tyFlow, rt.Editable_Mesh]
        return [
            member for member in instance.data["members"]
            if rt.ClassOf(member) not in allowed_classes
        ]

    def get_tyflow_operator(self, instance):
        """Check if the Export Particle Operators in the node
        connections.

        Args:
            instance (str): instance node

        Returns:
            invalid(list): list of invalid nodes which do
            not consist of Export Particle Operators as parts
            of the node connections
        """
        invalid = []
        members = instance.data["members"]
        for member in members:
            obj = member.baseobject

            # There must be at least one animation with export
            # particles enabled
            has_export_particles = False
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                # get name of the related tyFlow node
                sub_anim = rt.GetSubAnim(obj, anim_name)
                # check if there is export particle operator
                if rt.IsProperty(sub_anim, "Export_Particles"):
                    has_export_particles = True
                    break

            if not has_export_particles:
                invalid.append(member)
        return invalid
