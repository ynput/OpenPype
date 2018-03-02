import logging
import argparse

import avalon.io as io
import avalon.api as api
import avalon.fusion


log = logging.getLogger("UpdateSlapComp")


def switch(shot):
    """Update comp loaders through the containers

    Args:
        data (dict): collection if {asset: [subset, subset]}
    """

    host = api.registered_host()
    containers = list(host.ls())

    targets = [c["name"] for c in containers]

    representations = {}

    asset = io.find_one({"type": "asset", "name": shot})
    assert asset, ("Could not find asset in the database with the name "
                   "'%s'" % shot)

    subsets = io.find({"type": "subset",
                       "name": {"$in": targets},
                       "parent": asset["_id"]})

    if len(subsets) != len(targets):
        log.warning("Could not find the same amount of subsets in '%s'" % shot)

    for subset in subsets:
        version = io.find_one({"type": "version",
                               "parent": subset["_id"]},
                              sort=[('name', -1)])

        if not version:
            log.error("Could not find a verison for {}.{}".format(
                asset["name"], subset["name"]
            ))
            continue

        representation = io.find_one({"type": "representation",
                                      "parent": version["_id"]})

        representations[subset["name"]] = representation

    count = 0
    for i, container in enumerate(containers):
        subsetname = container["name"]
        if subsetname not in representations:
            log.error("Subset '%s' not found in comp, skipping" % subsetname)
            continue

        representation = representations[container["name"]]
        api.switch(container, representation)
        count += 1

    log.info("Updated %i items" % count)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("--shot",
                        help="Shotname to update the current comp to")

    parser.add_argument("--targets",
                        optional=True,
                        help="A list of target to update with given data")

    args = parser.parse_known_args()
    if not args.shot:
        raise RuntimeError("No data given, cannot update slap comp")

    if not isinstance(args.shot, dict):
        raise ValueError("Expecting data in the form of a dict, got "
                         "%s" % type(args.shot))

    api.install(avalon.fusion)
    switch(shot=args.shot)
