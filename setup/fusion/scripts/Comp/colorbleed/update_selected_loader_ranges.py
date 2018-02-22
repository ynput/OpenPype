"""Forces Fusion to 'retrigger' the Loader to update.

Warning:
    This might change settings like 'Reverse', 'Loop', trims and other
    settings of the Loader. So use this at your own risk.

"""

from avalon.fusion import comp_lock_and_undo_chunk


with comp_lock_and_undo_chunk(comp, "Reload clip time ranges"):
    tools = comp.GetToolList(True, "Loader").values()
    for tool in tools:

        # Get tool attributes
        tool_a = tool.GetAttrs()
        clipTable = tool_a['TOOLST_Clip_Name']
        altclipTable = tool_a['TOOLST_AltClip_Name']
        startTime = tool_a['TOOLNT_Clip_Start']
        old_global_in = tool.GlobalIn[comp.CurrentTime]

        # Reapply
        for index, _ in clipTable.items():
            time = startTime[index]
            tool.Clip[time] = tool.Clip[time]

        for index, _ in altclipTable.items():
            time = startTime[index]
            tool.ProxyFilename[time] = tool.ProxyFilename[time]

        tool.GlobalIn[comp.CurrentTime] = old_global_in
