import maya.cmds as cmds


def create_placeholder():

    place_holder_name = cmds.spaceLocator(name="_TEMPLATE_PLACEHOLDER_")[0]

    cmds.addAttr(
        place_holder_name,
        enumName="context_asset=1:linked_asset=2",
        longName="builder_type",
        attributeType='enum')

    cmds.addAttr(place_holder_name, longName="family", dataType='string')
    cmds.setAttr(place_holder_name + ".family",
                 'ex: model, look ...', type='string')
    cmds.addAttr(place_holder_name,
                 longName="representation", dataType='string')
    cmds.setAttr(place_holder_name + ".representation",
                 'ex: ma, abc ...', type='string')
    cmds.addAttr(place_holder_name, longName="loader", dataType='string')
    cmds.setAttr(place_holder_name + ".loader",
                 'ex: ReferenceLoader, LightLoader ...', type='string')
    cmds.addAttr(place_holder_name, longName="order",
                 niceName="Loader order", attributeType='short')
    cmds.setAttr(place_holder_name + ".order", 1)

    cmds.addAttr(place_holder_name, longName='optional_settings',
                 numberOfChildren=3, attributeType='compound')
    cmds.addAttr(place_holder_name, longName="asset",
                 dataType='string', parent='optional_settings')
    cmds.addAttr(place_holder_name, longName="subset",
                 dataType='string', parent='optional_settings')
    cmds.addAttr(place_holder_name, longName="hierarchy",
                 dataType='string', parent='optional_settings')
    cmds.setAttr(place_holder_name +
                 ".optional_settings.asset", '*', type='string')
    cmds.setAttr(place_holder_name +
                 ".optional_settings.subset", '*', type='string')
    cmds.setAttr(place_holder_name +
                 ".optional_settings.hierarchy", '*', type='string')

    cmds.addAttr(place_holder_name, longName="parent",
                 hidden=True, dataType='string')

    return place_holder_name
