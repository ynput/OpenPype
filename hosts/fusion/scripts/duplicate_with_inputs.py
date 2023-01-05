from openpype.hosts.fusion.api import (
    comp_lock_and_undo_chunk,
    get_current_comp
)


def is_connected(input):
    """Return whether an input has incoming connection"""
    return input.GetAttrs()["INPB_Connected"]


def duplicate_with_input_connections():
    """Duplicate selected tools with incoming connections."""

    comp = get_current_comp()
    original_tools = comp.GetToolList(True).values()
    if not original_tools:
        return  # nothing selected

    with comp_lock_and_undo_chunk(
            comp, "Duplicate With Input Connections"):

        # Generate duplicates
        comp.Copy()
        comp.SetActiveTool()
        comp.Paste()
        duplicate_tools = comp.GetToolList(True).values()

        # Copy connections
        for original, new in zip(original_tools, duplicate_tools):

            original_inputs = original.GetInputList().values()
            new_inputs = new.GetInputList().values()
            assert len(original_inputs) == len(new_inputs)

            for original_input, new_input in zip(original_inputs, new_inputs):

                if is_connected(original_input):

                    if is_connected(new_input):
                        # Already connected if it is between the copied tools
                        continue

                    new_input.ConnectTo(original_input.GetConnectedOutput())
                    assert is_connected(new_input), "Must be connected now"
