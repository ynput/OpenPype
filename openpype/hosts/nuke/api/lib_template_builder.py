from collections import OrderedDict

from openpype.vendor.python.common import qargparse
from openpype.tools.utils.widgets import OptionDialog
from openpype.hosts.nuke.api.lib import imprint
import nuke


# To change as enum
build_types = ["context_asset", "linked_asset", "all_assets"]


def get_placeholder_attributes(node, enumerate=False):
    list_atts = ['builder_type', 'family', 'representation', 'loader',
                 'loader_args', 'order', 'asset', 'subset',
                 'hierarchy', 'siblings', 'last_loaded']
    attributes = {}
    for attr in node.knobs().keys():
        if attr in list_atts:
            if enumerate:
                try:
                    attributes[attr] = node.knob(attr).values()
                except AttributeError:
                    attributes[attr] = node.knob(attr).getValue()
            else:
                attributes[attr] = node.knob(attr).getValue()

    return attributes


def delete_placeholder_attributes(node):
    '''
    function to delete all extra placeholder attributes
    '''
    extra_attributes = get_placeholder_attributes(node)
    for attribute in extra_attributes.keys():
        try:
            node.removeKnob(node.knob(attribute))
        except ValueError:
            continue


def hide_placeholder_attributes(node):
    '''
    function to hide all extra placeholder attributes
    '''
    extra_attributes = get_placeholder_attributes(node)
    for attribute in extra_attributes.keys():
        try:
            node.knob(attribute).setVisible(False)
        except ValueError:
            continue


def create_placeholder():

    args = placeholder_window()

    if not args:
        return  # operation canceled, no locator created

    placeholder = nuke.nodes.NoOp()
    placeholder.setName('PLACEHOLDER')
    placeholder.knob('tile_color').setValue(4278190335)

    # custom arg parse to force empty data query
    # and still imprint them on placeholder
    # and getting items when arg is of type Enumerator
    options = OrderedDict()
    for arg in args:
        if not type(arg) == qargparse.Separator:
            options[str(arg)] = arg._data.get("items") or arg.read()
    imprint(placeholder, options)
    imprint(placeholder, {'is_placeholder': True})


def update_placeholder():
    placeholder = nuke.selectedNodes()
    if not placeholder:
        raise ValueError("No node selected")
    if len(placeholder) > 1:
        raise ValueError("Too many selected nodes")
    placeholder = placeholder[0]

    args = placeholder_window(get_placeholder_attributes(placeholder))
    # delete placeholder attributes
    delete_placeholder_attributes(placeholder)
    if not args:
        return  # operation canceled

    options = OrderedDict()
    for arg in args:
        if not type(arg) == qargparse.Separator:
            options[str(arg)] = arg._data.get("items") or arg.read()
    imprint(placeholder, options)
    # imprint_enum(placeholder, args)


def imprint_enum(placeholder, args):
    """
    Imprint method doesn't act properly with enums.
    Replacing the functionnality with this for now
    """
    enum_values = {str(arg): arg.read()
                   for arg in args if arg._data.get("items")}
    string_to_value_enum_table = {
        build: i for i, build
        in enumerate(build_types)}
    attrs = {}
    for key, value in enum_values.items():
        attrs[key] = string_to_value_enum_table[value]
    # try :
    #     nuke.setPreset(nuke.getNodeClassName(placeholder),"attributes",attrs)
    # except Exception:

        # setattr(
        #     placeholder , key,
        #     string_to_value_enum_table[value])
        # raise Exception (getattr(
        #     placeholder , key))


def placeholder_window(options=None):
    from openpype.hosts.nuke.api.pipeline import get_main_window
    options = options or dict()
    dialog = OptionDialog(parent=get_main_window())
    dialog.setWindowTitle("Create Placeholder")

    args = [
        qargparse.Separator("Main attributes"),
        qargparse.Enum(
            "builder_type",
            label="Asset Builder Type",
            default=options.get("builder_type", 0),
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
            default=options.get("family", ""),
            label="OpenPype Family",
            placeholder="ex: model, look ..."),
        qargparse.String(
            "representation",
            default=options.get("representation", ""),
            label="OpenPype Representation",
            placeholder="ex: ma, abc ..."),
        qargparse.String(
            "loader",
            default=options.get("loader", ""),
            label="Loader",
            placeholder="ex: ReferenceLoader, LightLoader ...",
            help="""Loader

Defines what openpype loader will be used to load assets.
Useable loader depends on current host's loader list.
Field is case sensitive.
"""),
        qargparse.String(
            "loader_args",
            default=options.get("loader_args", ""),
            label="Loader Arguments",
            placeholder='ex: {"camera":"persp", "lights":True}',
            help="""Loader

Defines a dictionnary of arguments used to load assets.
Useable arguments depend on current placeholder Loader.
Field should be a valid python dict. Anything else will be ignored.
"""),
        qargparse.Integer(
            "order",
            default=options.get("order", 0),
            min=0,
            max=999,
            label="Order",
            placeholder="ex: 0, 100 ... (smallest order loaded first)",
            help="""Order

Order defines asset loading priority (0 to 999)
Priority rule is : "lowest is first to load"."""),
        qargparse.Separator(
            "Optional attributes "),
        qargparse.String(
            "asset",
            default=options.get("asset", ""),
            label="Asset filter",
            placeholder="regex filtering by asset name",
            help="Filtering assets by matching field regex to asset's name"),
        qargparse.String(
            "subset",
            default=options.get("subset", ""),
            label="Subset filter",
            placeholder="regex filtering by subset name",
            help="Filtering assets by matching field regex to subset's name"),
        qargparse.String(
            "hierarchy",
            default=options.get("hierarchy", ""),
            label="Hierarchy filter",
            placeholder="regex filtering by asset's hierarchy",
            help="Filtering assets by matching field asset's hierarchy")
    ]
    dialog.create(args)
    if not dialog.exec_():
        return None

    return args
