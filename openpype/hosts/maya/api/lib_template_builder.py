import maya.cmds as cmds


def create_linked_asset_place_holder(place_holder_name="linked_asset_builder"):

    return create_place_holder(place_holder_name, "linked_asset_builder")

def create_context_place_holder(place_holder_name="context_place_holder"):

    return create_place_holder(place_holder_name, "linked_asset_builder")

def create_place_holder(place_holder_name, attribute_name):

    place_holder_name = cmds.spaceLocator(name=place_holder_name)

    cmds.addAttr(place_holder_name, longName=attribute_name, attributeType='bool')
    cmds.addAttr(place_holder_name, longName="representation", dataType="string")
    cmds.addAttr(place_holder_name, longName="families", dataType='string')
    cmds.addAttr(place_holder_name, longName="repre_name", dataType='string')
    cmds.addAttr(place_holder_name, longName="asset", dataType='string')
    cmds.addAttr(place_holder_name, longName="hierarchy", dataType='string')
    cmds.addAttr(place_holder_name, longName="loader", dataType='string')
    cmds.addAttr(place_holder_name, longName="order", dataType='string')

    attr_name = "{}.{}".format(place_holder_name, attribute_name)
    cmds.setAttr(attr_name, True)

    return place_holder_name