from avalon.fusion import comp_lock_and_undo_chunk

from avalon import fusion
comp = fusion.get_current_comp()


def main():
    """Set all selected backgrounds to 32 bit"""
    with comp_lock_and_undo_chunk(comp, 'Selected Backgrounds to 32bit'):
        tools = comp.GetToolList(True, "Background").values()
        for tool in tools:
            tool.Depth = 5


main()
