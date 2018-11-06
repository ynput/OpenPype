import ftrack_utils

import ftrack_api


session = ftrack_api.Session()

objTypes = set()

# TODO get all entity types ---- NOT TASK,MILESTONE,LIBRARY --> should be editable!!!
allObjTypes = session.query('ObjectType').all()
for object in range(len(allObjTypes)):
    index = len(allObjTypes)-object-1

    if (str(allObjTypes[index]['name']) in ['Task','Milestone','Library']):
        allObjTypes.pop(index)

for k in allObjTypes:
    print(k['name'])

# Name & Label for export Avalon-mongo ID to Ftrack
# allCustAttr = session.query('CustomAttributeConfiguration').all()
# curCustAttr = []
# for ca in allCustAttr:
#     curCustAttr.append(ca['key'])
#
# custAttrName = 'avalon_mongo_id'
# custAttrLabel = 'Avalon/Mongo Id'
# custAttrType = session.query('CustomAttributeType where name is "text"').one()
# # TODO WHICH SECURITY ROLE IS RIGHT
# custAttrSecuRole = session.query('SecurityRole').all()

# for custAttrObjType in objTypes:
#     # Create Custom attribute if not exists
#     if custAttrName not in curCustAttr:
#         session.create('CustomAttributeConfiguration', {
#             'entity_type': 'task',
#             'object_type_id': custAttrObjType['id'],
#             'type': custAttrType,
#             'label': custAttrLabel,
#             'key': custAttrName,
#             'default': '',
#             'write_security_roles': custAttrSecuRole,
#             'read_security_roles': custAttrSecuRole,
#             'config': json.dumps({'markdown': False}),
#         })
#         session.commit()
