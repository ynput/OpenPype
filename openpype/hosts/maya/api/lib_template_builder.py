import maya.cmds as cmds


def create_place_holder():

    place_holder_name = cmds.spaceLocator(name="place_holder")

    cmds.addAttr(
        place_holder_name,
        enumName="context_asset=1:linked_asset=2",
        longName="builder_type",
        attributeType='enum')
    cmds.addAttr(
        place_holder_name, longName="representation", dataType="string"
    )
    cmds.addAttr(place_holder_name, longName="families", dataType='string')
    cmds.addAttr(place_holder_name, longName="repre_name", dataType='string')
    cmds.addAttr(place_holder_name, longName="asset", dataType='string')
    cmds.addAttr(place_holder_name, longName="hierarchy", dataType='string')
    cmds.addAttr(place_holder_name, longName="loader", dataType='string')
    cmds.addAttr(place_holder_name, longName="order", dataType='string')

    return place_holder_name
