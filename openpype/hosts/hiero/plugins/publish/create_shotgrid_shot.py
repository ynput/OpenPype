import pyblish.api
from openpype.lib.mongo import OpenPypeMongoConnection

class CollectShotgridShots(pyblish.api.InstancePlugin):
    """Collect shotgrid entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.4999
    label = "Create Shotgrid Shots"

    def process(self, instance):
        context = instance.context

        anatomy = instance.data.get("anatomyData", {})

        # Don't run shotgrid create and don't override entity if family is workfile
        if anatomy['family'] == 'workfile':
            self.log.info('Skipping Create Shotgrid Shot. This is a workfile')
            return

        sg = context.data.get("shotgridSession")
        sg_shot = _get_shotgrid_shot(sg, anatomy, context)

        if sg_shot:
            context.data["shotgridEntity"] = sg_shot
            self.log.info(
                # "Created Corresponding Shot for clip: {}".format(sg_shot)
                "Overriding entity with corresponding shot for clip: {}".format(sg_shot)
            )

def _get_shotgrid_collection(project):
    client = OpenPypeMongoConnection.get_mongo_client()
    return client.get_database("shotgrid_openpype").get_collection(project)


def _get_shotgrid_project(context):
    shotgrid_project_id = None
    shotgrid_data = context.data["project_settings"].get(
        "shotgrid")
    if shotgrid_data:
        shotgrid_project_id = shotgrid_data.get(
            "shotgrid_project_id")

    if shotgrid_project_id:
        return {"type": "Project", "id": shotgrid_project_id}
    return {}


def _get_shotgrid_shot(sg, anatomy, context):
    shot_name = anatomy['asset']

    # This will be substituted for the tag data when implemented into hiero as shot creator
    # but for now need to parse it from name of shot
    # Look for episode and create if need be
    sg_project = _get_shotgrid_project(context)
    if len(shot_name.split('_')) > 2:
        epi_name = shot_name.split('_')[-3]
        filters = [
            ["project.Project.sg_code", "is", anatomy['project']['name']],
            ['code', 'is', epi_name],
        ]
        sg_epi = sg.find_one('Episode', filters)
        if not sg_epi:
            epi_data = {
                "project": sg_project,
                # "sg_sequence": sg_seq,
                # Define sequence on shot
                "code": epi_name,
            }
            sg_epi = sg.create("Episode", epi_data)
    else:
        sg_epi = None

    # Look for sequence and create if need be
    if len(shot_name.split('_')) > 1:
        seq_name = shot_name.split('_')[-2]
        filters = [
            ["project.Project.sg_code", "is", anatomy['project']['name']],
            ['code', 'is', seq_name],
        ]
        if sg_epi:
            filters.append(['episode', 'is', sg_epi])
        sg_seq = sg.find_one("Sequence", filters)

        if not sg_seq:
            seq_data = {
                "project": sg_project,
                # "sg_sequence": sg_seq,
                # Define sequence on shot
                "code": seq_name,
            }
            if sg_epi:
                seq_data['episode'] = sg_epi
            sg_seq = sg.create("Sequence", seq_data)

    # Create shot if need be
    filters = [
        ["project.Project.sg_code", "is", anatomy['project']['name']],
        ['code', 'is', shot_name],
    ]
    unlinked_sg_shot = sg.find_one('Shot', filters)
    if sg_seq:
        filters.append(['sg_sequence', 'is', sg_seq])
        sg_shot = sg.find_one('Shot', filters)

        if unlinked_sg_shot and not sg_shot and sg_seq:
            sg.update('Shot', unlinked_sg_shot['id'], {'sg_sequence': sg_seq})

            return unlinked_sg_shot
    else:
        sg_shot = unlinked_sg_shot

    if not sg_shot:
        shot_data = {
            "project": sg_project,
            "code": shot_name,
        }
        if sg_seq:
            shot_data["sg_sequence"] = sg_seq

        sg_shot = sg.create("Shot", shot_data)
        # Based on hiero/publish handle.. create sg shot

    return sg_shot
