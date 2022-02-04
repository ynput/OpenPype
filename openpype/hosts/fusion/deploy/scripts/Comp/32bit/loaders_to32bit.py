from avalon.fusion import comp_lock_and_undo_chunk
from avalon import fusion
comp = fusion.get_current_comp()


def main():
    """Set all loaders to 32 bit"""
    with comp_lock_and_undo_chunk(comp, 'Loaders to 32bit'):
        tools = comp.GetToolList(False, "Loader").values()
        for tool in tools:
            tool.Depth = 5


main()
