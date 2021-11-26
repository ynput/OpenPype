import maya.cmds as cmds
from avalon.maya.lib import imprint
from avalon.vendor import qargparse
from avalon.tools.widgets import OptionDialog
from avalon.maya.pipeline import get_main_window

def create_placeholder():
    dialog = OptionDialog(parent=get_main_window())
    dialog.setWindowTitle("Create Placeholder")

    build_types = ["context_asset", "linked_asset"]
    args = [
        qargparse.Separator("Main attributes"),
        qargparse.Enum(
            "builder_type",
            label="Asset Builder Type",
            default=0,
            items=build_types,
            help="""Asset Builder Type
Builder type describe what template loader will look for.

context_asset : Template loader will look for subsets of
current context asset (Asset bob will find asset)

linked_asset : Template loader will look for assets linked
to current context asset.
Linked asset are looked in avalon database under field "inputLinks"
"""
        ),
        qargparse.String(
            "family",
            default="",
            label="OpenPype Family",
            placeholder="ex: model, look ..."),
        qargparse.String(
            "representation",
            default="",
            label="OpenPype Representation",
            placeholder="ex: ma, abc ..."),
        qargparse.String(
            "loader",
            default="",
            label="Loader",
            placeholder="ex: ReferenceLoader, LightLoader ...",
            help="""Loader

Defines what openpype loader will be used to load assets.
Useable loader depends on current host's loader list.
Field is case sensitive.
"""),
        qargparse.Integer(
            "order",
            default=0,
            min=0,
            max=999,
            label="Order",
            placeholder="ex: 0, 100 ... (smallest order loaded first)",
            help="""Order

Order defines asset loading priority (0 to 999)
Priority rule is : "lowest is first to load"."""),
        qargparse.Separator(
            "Optional attributes"),
        qargparse.String(
            "asset",
            default="",
            label="Asset filter",
            placeholder="regex filtering by asset name",
            help="""Filtering assets by matching field regex to asset's name"""),
        qargparse.String(
            "subset",
            default="",
            label="Subset filter",
            placeholder="regex filtering by subset name",
            help="""Filtering assets by matching field regex to subset's name"""),
        qargparse.String(
            "hierarchy",
            default="",
            label="Hierarchy filter",
            placeholder="regex filtering by asset's hierarchy",
            help="""Filtering assets by matching field asset's hierarchy""")
    ]
    dialog.create(args)

    if not dialog.exec_():
        return  # operation canceled, no locator created

    #custom arg parse to force empty data query and still imprint them on placeholder
    #and getting items when arg is of type Enumerator
    options = {str(arg): arg._data.get("items") or arg.read()
               for arg in args if not type(arg) == qargparse.Separator}
    placeholder = cmds.spaceLocator(name="_TEMPLATE_PLACEHOLDER_")[0]
    imprint(placeholder, options)

    # Some tweaks because imprint force enums to to default value so we get
    # back arg read and force them to attributes
    enum_values = {str(arg): arg.read()
        for arg in args if arg._data.get("items")}
    string_to_value_enum_table = {build: i for i, build in enumerate(build_types)}
    for key, value in enum_values.items():
        cmds.setAttr(
            placeholder + "." + key,
            string_to_value_enum_table[value])

    #Add helper attributes to keep placeholder info
    cmds.addAttr(placeholder, longName="parent",
        hidden=True, dataType="string")
