import pyblish.api
import pype.api


class ValidateFtrackAttributes(pyblish.api.InstancePlugin):
    """
    This will validate attributes in ftrack against data in scene.

    Attributes to be validated are specified in:

        `$PYPE_CONFIG/presets/<host>/ftrack_attributes.json`

    This is array (list) of checks in format:
    [
        [<attribute>, <operator>, <expression>]
    ]

    Where <attribute> is name of ftrack attribute, <operator> is one of:

        "is", is_not", "greater_than", "less_than", "contains", "not_contains",
        "starts_with", "ends_with"

    <expression> is python code that is evaluated by validator. This allows
    you to fetch whatever value in scene you want, for example in Maya:

    [
        "fps", "is",
        "from maya import mel; out = mel.eval('currentTimeUnitToFPS()')"
    ]

    will test if ftrack fps attribute on current Task parent is same as fps
    info we get from maya. Store the value you need to compare in
    variable `out` in your expression.
    """

    label = "Validate Custom Ftrack Attributes"
    order = pype.api.ValidateContentsOrder
    families = ["ftrack"]
    optional = True
    # Ignore standalone host, because it does not have an Ftrack entity
    # associated.
    hosts = [
        "blender",
        "fusion",
        "harmony",
        "houdini",
        "maya",
        "nuke",
        "nukestudio",
        "photoshop",
        "premiere",
        "resolve",
        "unreal"
    ]

    def process(self, instance):
        context = instance.context
        task = context.data.get('ftrackTask', False)
        if not task:
            self._raise(AttributeError,
                        "Missing FTrack Task entity in context")

        host = pyblish.api.current_host()
        to_check = context.data["presets"].get(
            host, {}).get("ftrack_custom_attributes")
        if not to_check:
            self.log.warning("ftrack_attributes preset not found")
            return

        self.log.info("getting attributes from ftrack ...")
        # get parent of task
        custom_attributes = {}
        try:
            parent = task["parent"]
            custom_attributes = parent["custom_attributes"].items()
        except KeyError:
            self._raise(KeyError, "missing `parent` or `attributes`")

        custom_attributes = dict(custom_attributes)

        # get list of hierarchical attributes from ftrack
        session = context.data["ftrackSession"]

        custom_hier_attributes = self._get_custom_hier_attrs(session)
        custom_attributes = {}
        _nonhier = {}
        custom_hier_attributes = {k: None for k in custom_hier_attributes}

        for key, value in dict(parent["custom_attributes"]).items():
            if key in custom_hier_attributes:
                custom_hier_attributes[key] = value
            else:
                _nonhier[key] = value

        custom_hier_values = self._get_hierarchical_values(
            custom_hier_attributes, parent)

        custom_hier_values.update(_nonhier)

        errors = []
        attribs = custom_hier_values
        for check in to_check:
            ev = {}
            # WARNING(Ondrej Samohel): This is really not secure as we are
            # basically executing user code. But there's no other way to make
            # it flexible enough for users to get stuff from
            exec(str(check[2]), {}, ev)
            if not ev.get("out"):
                errors.append("{} code doesn't return 'out': '{}'".format(
                    check[0], check[2]))
                continue
            if check[0] in attribs:
                if check[1] == "is":
                    if attribs[check[0]] != ev["out"]:
                        errors.append("{}: {} is not {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "is_not":
                    if attribs[check[0]] == ev["out"]:
                        errors.append("{}: {} is {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "less_than":
                    if attribs[check[0]] < ev["out"]:
                        errors.append("{}: {} is greater {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "greater_than":
                    if attribs[check[0]] < ev["out"]:
                        errors.append("{}: {} is less {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "contains":
                    if attribs[check[0]] in ev["out"]:
                        errors.append("{}: {} does not contain {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "not_contains":
                    if attribs[check[0]] not in ev["out"]:
                        errors.append("{}: {} contains {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "starts_with":
                    if attribs[check[0]].startswith(ev["out"]):
                        errors.append("{}: {} does not starts with {}".format(
                            check[0], attribs[check[0]], ev["out"]))
                elif check[1] == "ends_with":
                    if attribs[check[0]].endswith(ev["out"]):
                        errors.append("{}: {} does not end with {}".format(
                            check[0], attribs[check[0]], ev["out"]))

        if errors:
            self.log.error('There are invalid values for attributes:')
            for e in errors:
                self.log.error(e)
            raise ValueError("ftrack attributes doesn't match")

    def _get_custom_hier_attrs(self, session):
        hier_custom_attributes = []
        cust_attrs_query = (
            "select id, entity_type, object_type_id, is_hierarchical"
            " from CustomAttributeConfiguration"
        )
        all_avalon_attr = session.query(cust_attrs_query).all()
        for cust_attr in all_avalon_attr:
            if cust_attr["is_hierarchical"]:
                hier_custom_attributes.append(cust_attr["key"])

        return hier_custom_attributes

    def _get_hierarchical_values(self, keys_dict, entity):
        # check values already set
        _set_keys = []
        for key, value in keys_dict.items():
            if value is not None:
                _set_keys.append(key)

        # pop set values from keys_dict
        set_keys = {}
        for key in _set_keys:
            set_keys[key] = keys_dict.pop(key)

        # find if entity has set values and pop them out
        keys_to_pop = []
        for key in keys_dict.keys():
            _val = entity["custom_attributes"][key]
            if _val:
                keys_to_pop.append(key)
                set_keys[key] = _val

        for key in keys_to_pop:
            keys_dict.pop(key)

        # if there are not keys to find value return found
        if not keys_dict:
            return set_keys

        # end recursion if entity is project
        if entity.entity_type.lower() == "project":
            for key, value in keys_dict.items():
                set_keys[key] = value

        else:
            result = self._get_hierarchical_values(keys_dict, entity["parent"])
            for key, value in result.items():
                set_keys[key] = value

        return set_keys

    def _raise(self, exc, msg):
        self.log.error(msg)
        raise exc(msg)
