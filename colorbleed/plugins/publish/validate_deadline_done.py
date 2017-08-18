import pyblish.api


class ValidateMindbenderDeadlineDone(pyblish.api.InstancePlugin):
    """Ensure render is finished before publishing the resulting images"""

    label = "Rendered Successfully"
    order = pyblish.api.ValidatorOrder
    hosts = ["shell"]
    families = ["mindbender.imagesequence"]
    optional = True

    def process(self, instance):
        from avalon import api
        from avalon.vendor import requests

        # From Deadline documentation
        # https://docs.thinkboxsoftware.com/products/deadline/8.0/
        # 1_User%20Manual/manual/rest-jobs.html#job-property-values
        states = {
            0: "Unknown",
            1: "Active",
            2: "Suspended",
            3: "Completed",
            4: "Failed",
            6: "Pending",
        }

        assert "AVALON_DEADLINE" in api.Session, ("Environment variable "
                                                  "missing: 'AVALON_DEADLINE'")
        avalon_deadline = api.Session["AVALON_DEADLINE"]
        url = "{}/api/jobs?JobID=%s".format(avalon_deadline)

        for job in instance.data["metadata"]["jobs"]:
            response = requests.get(url % job["_id"])

            if response.ok:
                data = response.json()
                assert data, ValueError("Can't find information about "
                                        "this Deadline job: "
                                        "{}".format(job["_id"]))

                state = states.get(data[0]["Stat"])
                if state in (None, "Unknown"):
                    raise Exception("State of this render is unknown")

                elif state == "Active":
                    raise Exception("This render is still currently active")

                elif state == "Suspended":
                    raise Exception("This render is suspended")

                elif state == "Failed":
                    raise Exception("This render was not successful")

                elif state == "Pending":
                    raise Exception("This render is pending")
                else:
                    self.log.info("%s was rendered successfully" % instance)

            else:
                raise Exception("Could not determine the current status "
                                " of this render")
