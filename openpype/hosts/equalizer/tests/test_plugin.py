"""
3DEqualizer plugin tests

These test need to be run in 3DEqualizer.

"""
import json
import re
import unittest

from attr import asdict
import attr
from attr.exceptions import NotAnAttrsClassError

AVALON_CONTAINER_ID = "test.container"

CONTEXT_REGEX = re.compile(
    r"AYON_CONTEXT::(?P<context>.*?)::AYON_CONTEXT_END",
    re.DOTALL)


@attr.s
class Container(object):
    name = attr.ib(default=None)
    id = attr.ib(init=False, default=AVALON_CONTAINER_ID)
    namespace = attr.ib(default="")
    loader = attr.ib(default=None)
    representation = attr.ib(default=None)


class Tde4Mock:
    """Simple class to mock few 3dequalizer functions.

    Just to run the test outside the host itself.
    """

    _notes = ""

    def isProjectUpToDate(self):
        return True

    def setProjectNotes(self, notes):
        self._notes = notes

    def getProjectNotes(self):
        return self._notes


tde4 = Tde4Mock()


def get_context_data():
    m = re.search(CONTEXT_REGEX, tde4.getProjectNotes())
    return json.loads(m.groupdict()["context"]) if m else {}


def update_context_data(data, changes):
    m = re.search(CONTEXT_REGEX, tde4.getProjectNotes())
    if not m:
        tde4.setProjectNotes("AYON_CONTEXT::::AYON_CONTEXT_END")
    update = json.dumps(data, indent=4)
    tde4.setProjectNotes(
        re.sub(
            CONTEXT_REGEX,
            "AYON_CONTEXT::%s::AYON_CONTEXT_END"%update,
            tde4.getProjectNotes()
        )
    )


def get_containers():
    return get_context_data().get("containers", [])


def add_container(container):
    context_data = get_context_data()
    containers = get_containers()

    for _container in containers:
        if _container["name"] == container.name and _container["namespace"] == container.namespace:  # noqa: E501
            containers.remove(_container)
            break

    try:
        containers.append(asdict(container))
    except NotAnAttrsClassError:
        print("not an attrs class")
        containers.append(container)

    context_data["containers"] = containers
    update_context_data(context_data, changes={})


class TestEqualizer(unittest.TestCase):
    def test_context_data(self):
        # ensure empty project notest

        data = get_context_data()
        print("data here", data)
        self.assertEqual({}, data, "context data are not empty")

        # add container
        add_container(
            Container(name="test", representation="test_A")
        )


        self.assertEqual(
            1, len(get_containers()), "container not added")
        self.assertEqual(
            get_containers()[0]["name"],
            "test", "container name is not correct")

        # add another container
        add_container(
            Container(name="test2", representation="test_B")
        )

        self.assertEqual(
            2, len(get_containers()), "container not added")
        self.assertEqual(
            get_containers()[1]["name"],
            "test2", "container name is not correct")

        # update container
        add_container(
            Container(name="test2", representation="test_C")
        )
        self.assertEqual(
            2, len(get_containers()), "container not updated")
        self.assertEqual(
            get_containers()[1]["representation"],
            "test_C", "container name is not correct")

        Containers = get_containers()
        print("Containers here", Containers)
        notes = tde4.getProjectNotes().split("\n")
        print("\n  \n \nproject notes:-")
        for note in notes:
            print(note)


if __name__ == "__main__":
    unittest.main()
