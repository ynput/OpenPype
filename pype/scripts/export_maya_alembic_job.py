import os

from pyblish import util


def check_results(context):
    for result in context.data["results"]:
        if not result["success"]:
            raise ValueError(result)


def main():
    context = util.collect()
    for instance in context:
        if instance.name == os.environ["PYPE_INSTANCE_NAME"]:
            instance.data["publish"] = True
            instance.data["farm"] = False
            instance.data["families"].remove("deadline")
        else:
            instance.data["publish"] = False

    check_results(context)

    stages = [util.extract, util.integrate]
    for stage in stages:
        stage(context)
        check_results(context)


if __name__ == '__main__':
    main()
