import pyblish.api
import maya.cmds as mc

@pyblish.api.log
class removeVaccineNodes(pyblish.api.Validator):
    """Removes all vaccine nodes"""

    label = 'Remove Vaccine Nodes'
    order = pyblish.api.Validator.order
    optional = True
    hosts = ['maya']
    families = ['*']

    def process(self, context):

        # remove vaccine acript jobs
        for script in mc.ls(type='script'):
            if ("breed_gene" in script or "vaccine_gene" in script):
                mc.delete(script)
        for sj in mc.scriptJob(listJobs=True):
            if "leukocyte" in sj:
                job_num = int(sj.split(':', 1)[0])
                mc.scriptJob(kill=job_num, force=True)
