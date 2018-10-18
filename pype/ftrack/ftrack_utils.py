# fttrack help functions


# import ftrack
import os
from pprint import *


def deleteAssetsForTask(taskId):
    #taskId = os.environ['FTRACK_TASKID']
    task = ftrack.Task(taskId)

    taskAssets = task.getAssets()
    print(taskAssets)
    for a in taskAssets:
        print(a.getName())
        a.delete()
    #shot = task.getParent()
    #shotAssets = shot.getAssets()


def deleteAssetsFromShotByName(shotId, assNm=None):
    if not assNm:
        return

    shot = ftrack.Task(shotId)

    shotAssets = shot.getAssets()
    for a in shotAssets:
        nm = a.getName()
        if nm == assNm:
            a.delete()


def killRunningTasks(tm=None):
    import datetime
    import ftrack_api

    session = ftrack_api.Session()

    # Query all jobs created prior to yesterday which has not yet been completed.
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    if tm:
        yesterday = tm
    print(yesterday)
    jobs = session.query(
        'select id, status from Job '
        'where status in ("queued", "running") and created_at > {0}'.format(yesterday)
    )

    # Update all the queried jobs, setting the status to failed.
    for job in jobs:
        print(job['created_at'])
        print('Changing Job ({}) status: {} -> failed'.format(job['id'], job['status']))
        job['status'] = 'failed'

    session.commit()

    print('Complete')


def createCustomAttr():

    import ftrack_api

    session = ftrack_api.Session()
    objTypes = set()  # for custom attribute creation

    # TODO get all entity types ---- NOT TASK
    # objTypes.add(session.query('ObjectType where name is ' + entity.entity_type).one())

    # Name & Label for export Avalon-mongo ID to Ftrack
    allCustAttr = session.query('CustomAttributeConfiguration').all()
    curCustAttr = []
    for ca in allCustAttr:
        curCustAttr.append(ca['key'])

    custAttrName = 'avalon_mongo_id'
    custAttrLabel = 'Avalon/Mongo Id'
    custAttrType = session.query('CustomAttributeType where name is "text"').one()
    # TODO WHICH SECURITY ROLE IS RIGHT
    custAttrSecuRole = session.query('SecurityRole').all()

    for custAttrObjType in objTypes:
        # custAttrObjType = session.query('ObjectType where name is ' + entity.entity_type).one()
        # Create Custom attribute if not exists
        if custAttrName not in curCustAttr:
            session.create('CustomAttributeConfiguration', {
                'entity_type': 'task',
                'object_type_id': custAttrObjType['id'],
                'type': custAttrType,
                'label': custAttrLabel,
                'key': custAttrName,
                'default': '',
                'write_security_roles': custAttrSecuRole,
                'read_security_roles': custAttrSecuRole,
                'config': json.dumps({'markdown': False}),
            })
    session.commit()


def checkRegex():
    # _handle_result -> would be solution?
    # """ TODO Check if name of entities match REGEX"""
    for entity in importable:
        for e in entity['link']:
            item = {
                "silo": "silo",
                "parent": "parent",
                "type": "asset",
                "schema": "avalon-core:asset-2.0",
                "name": e['name'],
                "data": dict(),
            }
            try:
                schema.validate(item)
            except Exception as e:
                print(e)
    print(e['name'])
    ftrack.EVENT_HUB.publishReply(
        event,
        data={
            'success': False,
            'message': 'Entity name contains invalid character!'
        }
    )
